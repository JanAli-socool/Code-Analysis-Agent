"""
Incremental Analysis - Only analyze changed files using git diff.
"""
import subprocess
import os
import json
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass
from collections import defaultdict

if TYPE_CHECKING:
    from pro.orchestrator import ProfessionalOrchestrator

from pro.config.loader import get_config
from pro.cache.manager import AnalysisCache


@dataclass
class ChangeSet:
    added: List[str]
    modified: List[str]
    deleted: List[str]
    renamed: List[Tuple[str, str]]  # (old_path, new_path)


@dataclass
class IncrementalResult:
    full_analysis: bool
    changed_files: List[str]
    affected_modules: Set[str]
    analysis_time_ms: float
    cache_hits: int
    cache_misses: int


class IncrementalAnalyzer:
    def __init__(self, repo_path: str, config=None):
        self.repo_path = Path(repo_path).resolve()
        self.config = config or get_config()
        self.cache = AnalysisCache(
            self.config.execution.cache_dir,
            self.config.execution.cache_ttl_hours
        ) if self.config.execution.cache_enabled else None
        self._orchestrator_cls = None
    
    def _get_orchestrator(self):
        """Lazy import to avoid circular dependency."""
        if self._orchestrator_cls is None:
            from pro.orchestrator import ProfessionalOrchestrator
            self._orchestrator_cls = ProfessionalOrchestrator
        return self._orchestrator_cls
    
    def get_changes(self, base_ref: str = "HEAD~1", target_ref: str = "HEAD") -> ChangeSet:
        """Get changed files between two git refs."""
        try:
            # Get diff with names and status
            result = subprocess.run([
                'git', 'diff', '--name-status', '-z',
                base_ref, target_ref
            ], cwd=self.repo_path, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                # Fallback: get all tracked files
                return self._get_all_files()
            
            added, modified, deleted, renamed = [], [], [], []
            
            parts = result.stdout.split('\x00')
            i = 0
            while i < len(parts) - 1:
                status = parts[i]
                path = parts[i + 1] if i + 1 < len(parts) else ""
                i += 2
                
                if not path:
                    continue
                
                if status == 'A':
                    added.append(path)
                elif status == 'M':
                    modified.append(path)
                elif status == 'D':
                    deleted.append(path)
                elif status.startswith('R'):
                    # Rename: status is R100, path is old, next is new
                    if i < len(parts):
                        new_path = parts[i]
                        i += 1
                        renamed.append((path, new_path))
                elif status == 'C':
                    # Copy: similar to rename
                    if i < len(parts):
                        new_path = parts[i]
                        i += 1
                        renamed.append((path, new_path))
            
            return ChangeSet(added, modified, deleted, renamed)
            
        except Exception as e:
            # Fallback
            return self._get_all_files()
    
    def _get_all_files(self) -> ChangeSet:
        """Get all tracked Python files."""
        try:
            result = subprocess.run([
                'git', 'ls-files', '*.py'
            ], cwd=self.repo_path, capture_output=True, text=True, timeout=30)
            files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
            return ChangeSet(added=files, modified=[], deleted=[], renamed=[])
        except Exception:
            return ChangeSet(added=[], modified=[], deleted=[], renamed=[])
    
    def get_affected_modules(self, changes: ChangeSet, file_contents: Dict[str, str]) -> Set[str]:
        """Determine which modules are affected by changes (including dependents)."""
        # Build import graph
        py_files = {k: v for k, v in file_contents.items() if k.endswith('.py')}
        
        # Map file paths to module names
        module_map = {}
        for path in py_files:
            module = path.replace('/', '.').replace('\\', '.').replace('.py', '')
            module_map[path] = module
        
        # Build reverse dependency graph (who imports whom)
        reverse_deps = defaultdict(set)
        local_modules = set(module_map.values())
        
        # Add parent modules
        for mod in list(local_modules):
            parts = mod.split('.')
            for i in range(1, len(parts) + 1):
                local_modules.add('.'.join(parts[:i]))
        
        for file_path, content in py_files.items():
            try:
                import ast
                tree = ast.parse(content)
                from_module = module_map[file_path]
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name in local_modules:
                                reverse_deps[alias.name].add(from_module)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and node.module in local_modules:
                            reverse_deps[node.module].add(from_module)
            except Exception:
                pass
        
        # Find affected modules
        affected = set()
        changed_modules = set()
        
        for path in changes.added + changes.modified:
            if path in module_map:
                changed_modules.add(module_map[path])
        
        for old_path, new_path in changes.renamed:
            if old_path in module_map:
                changed_modules.add(module_map[old_path])
            if new_path in module_map:
                changed_modules.add(module_map[new_path])
        
        # Add changed modules and their dependents (transitive closure)
        queue = list(changed_modules)
        while queue:
            mod = queue.pop(0)
            if mod in affected:
                continue
            affected.add(mod)
            # Add dependents
            for dep in reverse_deps.get(mod, set()):
                if dep not in affected:
                    queue.append(dep)
        
        return affected
    
    def should_run_full_analysis(self, changes: ChangeSet, threshold: int = 50) -> bool:
        """Determine if full analysis is needed based on change scope."""
        total_changes = len(changes.added) + len(changes.modified) + len(changes.deleted)
        return total_changes > threshold
    
    def run_incremental(self, base_ref: str = "HEAD~1", target_ref: str = "HEAD",
                       force_full: bool = False) -> IncrementalResult:
        """Run incremental analysis."""
        import time
        start_time = time.time()
        
        # Get changes
        changes = self.get_changes(base_ref, target_ref)
        total_changes = len(changes.added) + len(changes.modified) + len(changes.deleted)
        
        # Load repository files (lazy import to avoid circular dependency)
        Orchestrator = self._get_orchestrator()
        orchestrator = Orchestrator(str(self.repo_path), self.config)
        file_contents = orchestrator.load_repository()
        
        # Check if full analysis needed
        if force_full or self.should_run_full_analysis(changes):
            result = orchestrator.run_analysis()
            return IncrementalResult(
                full_analysis=True,
                changed_files=[],
                affected_modules=set(),
                analysis_time_ms=(time.time() - start_time) * 1000,
                cache_hits=0,
                cache_misses=0
            )
        
        # Get affected modules
        affected_modules = self.get_affected_modules(changes, file_contents)
        
        # Filter file_contents to only affected modules
        affected_files = set()
        for path in file_contents:
            if path.endswith('.py'):
                module = path.replace('/', '.').replace('\\', '.').replace('.py', '')
                if module in affected_modules or any(
                    module.startswith(am + '.') or am.startswith(module + '.') 
                    for am in affected_modules
                ):
                    affected_files.add(path)
        
        # Add changed files explicitly
        for path in changes.added + changes.modified:
            if path in file_contents:
                affected_files.add(path)
        
        # Create filtered file_contents
        filtered_contents = {k: v for k, v in file_contents.items() if k in affected_files}
        
        # Temporarily replace file_contents for analysis
        original_contents = orchestrator.file_contents
        orchestrator.file_contents = filtered_contents
        
        # Run analysis on subset
        result = orchestrator.run_analysis()
        
        # Restore
        orchestrator.file_contents = original_contents
        
        # Track cache stats
        cache_stats = self.cache.stats() if self.cache else {'memory_entries': 0, 'disk_entries': 0}
        
        return IncrementalResult(
            full_analysis=False,
            changed_files=list(affected_files),
            affected_modules=affected_modules,
            analysis_time_ms=(time.time() - start_time) * 1000,
            cache_hits=cache_stats.get('memory_entries', 0),
            cache_misses=cache_stats.get('disk_entries', 0)
        )


def create_incremental_cli():
    """CLI entry point for incremental analysis."""
    import click
    
    @click.command()
    @click.argument('repo_path', type=click.Path(exists=True))
    @click.option('--base', default='HEAD~1', help='Base git ref')
    @click.option('--target', default='HEAD', help='Target git ref')
    @click.option('--force-full', is_flag=True, help='Force full analysis')
    @click.option('--output', '-o', type=click.Path(), help='Output file')
    def incremental(repo_path, base, target, force_full, output):
        analyzer = IncrementalAnalyzer(repo_path)
        result = analyzer.run_incremental(base, target, force_full)
        
        output_data = {
            "full_analysis": result.full_analysis,
            "changed_files": result.changed_files,
            "affected_modules": list(result.affected_modules),
            "analysis_time_ms": result.analysis_time_ms,
            "cache_hits": result.cache_hits,
            "cache_misses": result.cache_misses
        }
        
        if output:
            with open(output, 'w') as f:
                json.dump(output_data, f, indent=2)
        else:
            console.print_json(json.dumps(output_data, indent=2))
    
    return incremental


if __name__ == "__main__":
    import json
    from rich.console import Console
    console = Console()
    create_incremental_cli()