"""
Async skill execution with proper concurrency control, timeouts, and cancellation.
"""
import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Callable, Awaitable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from pro.config.loader import get_config


@dataclass
class SkillTask:
    name: str
    skill: Any
    weight: float
    repo_path: str
    file_contents: Dict[str, str]
    config: Any


@dataclass
class SkillResult:
    name: str
    category: str
    score: float
    weight: float
    findings: List[Dict]
    metrics: List[Dict]
    duration_ms: float
    error: Optional[str] = None


class AsyncSkillRunner:
    def __init__(self, max_concurrent: int = None, default_timeout: float = 120.0):
        self.config = get_config()
        exec_config = self.config.execution
        
        self.max_concurrent = max_concurrent or exec_config.max_workers
        self.default_timeout = default_timeout
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        self.logger = logging.getLogger("async_runner")
        
        # Thread pool for CPU-bound skills (radon, bandit subprocess, AST parsing)
        self.thread_pool = ThreadPoolExecutor(max_workers=self.max_concurrent)
        
        # Track running tasks for cancellation
        self._running_tasks: Dict[str, asyncio.Task] = {}

    async def run_skills(self, skills: List[tuple], repo_path: str, 
                        file_contents: Dict[str, str]) -> List[SkillResult]:
        """Run all skills concurrently with proper error handling."""
        
        async def run_single_skill(name: str, skill: Any, weight: float) -> SkillResult:
            async with self.semaphore:
                return await self._run_skill_with_timeout(name, skill, weight, repo_path, file_contents)

        # Create tasks
        tasks = [
            asyncio.create_task(run_single_skill(name, skill, weight))
            for name, skill, weight in skills
        ]
        self._running_tasks = {name: task for (name, _, _), task in zip(skills, tasks)}

        # Wait for all with timeout
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            await self.cancel_all()
            raise

        # Process results
        skill_results = []
        for (name, _, weight), result in zip(skills, results):
            if isinstance(result, Exception):
                self.logger.error(f"Skill {name} failed: {result}")
                skill_results.append(SkillResult(
                    name=name, category=name, score=0.0, weight=weight,
                    findings=[], metrics=[], duration_ms=0, error=str(result)
                ))
            else:
                skill_results.append(result)

        return skill_results

    async def _run_skill_with_timeout(self, name: str, skill: Any, weight: float,
                                      repo_path: str, file_contents: Dict[str, str]) -> SkillResult:
        """Run a single skill with timeout and thread pool for CPU-bound work."""
        start = time.time()
        
        try:
            # Run skill in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            skill_result = await asyncio.wait_for(
                loop.run_in_executor(
                    self.thread_pool,
                    self._run_skill_sync,
                    skill, repo_path, file_contents
                ),
                timeout=self.default_timeout
            )
            duration = (time.time() - start) * 1000
            
            return SkillResult(
                name=name, category=name,
                score=skill_result.get("score", 0.0),
                weight=weight,
                findings=skill_result.get("findings", []),
                metrics=skill_result.get("metrics", []),
                duration_ms=round(duration, 1)
            )
        except asyncio.TimeoutError:
            self.logger.error(f"Skill {name} timed out after {self.default_timeout}s")
            return SkillResult(
                name=name, category=name, score=0.0, weight=weight,
                findings=[], metrics=[], duration_ms=self.default_timeout * 1000,
                error=f"Timeout after {self.default_timeout}s"
            )
        except Exception as e:
            self.logger.error(f"Skill {name} error: {e}")
            return SkillResult(
                name=name, category=name, score=0.0, weight=weight,
                findings=[], metrics=[], duration_ms=(time.time() - start) * 1000,
                error=str(e)
            )

    def _run_skill_sync(self, skill: Any, repo_path: str, file_contents: Dict[str, str]) -> Dict:
        """Synchronous skill execution for thread pool."""
        return skill.analyze(repo_path, file_contents)

    async def cancel_all(self) -> None:
        """Cancel all running skill tasks."""
        for name, task in self._running_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    self.logger.info(f"Cancelled skill: {name}")
        self._running_tasks.clear()

    async def shutdown(self) -> None:
        """Clean shutdown of runner."""
        await self.cancel_all()
        self.thread_pool.shutdown(wait=True)

    @asynccontextmanager
    async def skill_context(self, name: str, skill: Any, weight: float,
                           repo_path: str, file_contents: Dict[str, str]):
        """Context manager for single skill execution with automatic cleanup."""
        task = asyncio.create_task(
            self._run_skill_with_timeout(name, skill, weight, repo_path, file_contents)
        )
        self._running_tasks[name] = task
        try:
            yield task
        finally:
            if name in self._running_tasks:
                del self._running_tasks[name]


class SkillPipeline:
    """Pipeline for running skills in stages with dependencies."""
    
    def __init__(self, runner: AsyncSkillRunner):
        self.runner = runner
        self.stages: List[List[tuple]] = []
    
    def add_stage(self, skills: List[tuple]) -> 'SkillPipeline':
        """Add a pipeline stage (skills run in parallel within stage, stages sequential)."""
        self.stages.append(skills)
        return self
    
    async def run(self, repo_path: str, file_contents: Dict[str, str]) -> List[SkillResult]:
        """Run pipeline stages sequentially."""
        all_results = []
        
        for stage in self.stages:
            stage_results = await self.runner.run_skills(stage, repo_path, file_contents)
            all_results.extend(stage_results)
        
        return all_results


async def run_skills_async(skills: List[tuple], repo_path: str, 
                          file_contents: Dict[str, str],
                          max_concurrent: int = None) -> List[SkillResult]:
    """Convenience function for running skills asynchronously."""
    runner = AsyncSkillRunner(max_concurrent=max_concurrent)
    try:
        return await runner.run_skills(skills, repo_path, file_contents)
    finally:
        await runner.shutdown()