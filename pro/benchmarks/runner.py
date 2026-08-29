"""
Benchmark runner for performance testing.
"""
import json
import time
import statistics
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from rich.progress import Progress

from pro.orchestrator import ProfessionalOrchestrator
from pro.config.loader import get_config, ConfigLoader
from pro.cache.manager import AnalysisCache


@dataclass
class BenchmarkResult:
    repo_name: str
    repo_path: str
    iterations: int
    times_ms: List[float]
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    std_dev_ms: float
    cache_hits: int
    cache_misses: int
    cache_hit_rate: float
    scores: List[float]
    avg_score: float


class BenchmarkRunner:
    def __init__(self, config=None):
        self.config = config or get_config()
    
    def run_benchmarks(self, repo_paths: List[str], iterations: int, 
                      progress: Progress, task_id) -> List[Dict[str, Any]]:
        """Run benchmarks on multiple repositories."""
        results = []
        
        for repo_path in repo_paths:
            repo_name = Path(repo_path).name
            progress.update(task_id, description=f"Benchmarking {repo_name}...")
            
            result = self._benchmark_repo(repo_path, iterations, progress, task_id)
            results.append(asdict(result))
            progress.advance(task_id)
        
        return results
    
    def _benchmark_repo(self, repo_path: str, iterations: int,
                       progress: Progress, task_id) -> BenchmarkResult:
        """Benchmark a single repository."""
        # Clear cache before first run
        cache_dir = self.config.execution.cache_dir
        if not Path(cache_dir).is_absolute():
            cache_dir = Path(repo_path) / cache_dir
        cache = AnalysisCache(str(cache_dir), self.config.execution.cache_ttl_hours) if self.config.execution.cache_enabled else None
        
        times_ms = []
        scores = []
        cache_hits = 0
        cache_misses = 0
        
        for i in range(iterations):
            # Create fresh orchestrator each iteration
            orchestrator = ProfessionalOrchestrator(repo_path, self.config)
            
            # Check cache stats before
            stats_before = cache.stats() if cache else {'disk_entries': 0}
            
            start = time.perf_counter()
            result = orchestrator.run_analysis()
            elapsed_ms = (time.perf_counter() - start) * 1000
            
            # Check cache stats after
            stats_after = cache.stats() if cache else {'disk_entries': 0}
            if stats_after['disk_entries'] > stats_before['disk_entries']:
                cache_hits += 1
            else:
                cache_misses += 1
            
            times_ms.append(elapsed_ms)
            scores.append(result.overall_score)
            
            progress.update(task_id, advance=1/iterations)
        
        total_cache = cache_hits + cache_misses
        hit_rate = cache_hits / total_cache if total_cache > 0 else 0.0
        
        return BenchmarkResult(
            repo_name=Path(repo_path).name,
            repo_path=repo_path,
            iterations=iterations,
            times_ms=times_ms,
            avg_time_ms=statistics.mean(times_ms),
            min_time_ms=min(times_ms),
            max_time_ms=max(times_ms),
            std_dev_ms=statistics.stdev(times_ms) if len(times_ms) > 1 else 0.0,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            cache_hit_rate=hit_rate,
            scores=scores,
            avg_score=statistics.mean(scores)
        )
    
    def save_results(self, results: List[Dict], output_path: str) -> None:
        """Save benchmark results to JSON."""
        with open(output_path, 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'results': results,
                'summary': {
                    'total_repos': len(results),
                    'total_iterations': sum(r['iterations'] for r in results),
                    'avg_time_overall': statistics.mean(r['avg_time_ms'] for r in results),
                }
            }, f, indent=2)
    
    def load_results(self, input_path: str) -> List[Dict]:
        """Load benchmark results from JSON."""
        with open(input_path) as f:
            return json.load(f)['results']
    
    def compare_runs(self, baseline_path: str, current_path: str) -> Dict[str, Any]:
        """Compare two benchmark runs."""
        baseline = self.load_results(baseline_path)
        current = self.load_results(current_path)
        
        comparison = {}
        for b, c in zip(baseline, current):
            if b['repo_name'] != c['repo_name']:
                continue
            comparison[b['repo_name']] = {
                'time_delta_pct': ((c['avg_time_ms'] - b['avg_time_ms']) / b['avg_time_ms']) * 100,
                'score_delta': c['avg_score'] - b['avg_score'],
                'baseline_time_ms': b['avg_time_ms'],
                'current_time_ms': c['avg_time_ms'],
                'baseline_score': b['avg_score'],
                'current_score': c['avg_score'],
            }
        
        return comparison