"""
Architecture Analysis Skill - Coupling, cohesion, layering, patterns
"""
import ast
import os
from collections import defaultdict
from typing import List, Dict, Set
from advanced.skills.base import BaseSkill
from advanced.models import AgentContext, CategoryScore, AnalysisCategory, Finding, Severity, MetricResult


class ArchitectureSkill(BaseSkill):
    def __init__(self):
        super().__init__("Architecture Analysis", AnalysisCategory.ARCHITECTURE, weight=1.5)

    def analyze(self, context: AgentContext) -> CategoryScore:
        findings = []
        metrics = []

        imports_by_file = {}
        all_imports = set()
        internal_imports = defaultdict(set)
        external_imports = defaultdict(set)
        circular_deps = []

        for file_path, content in context.file_contents.items():
            if not file_path.endswith('.py'):
                continue
            try:
                tree = ast.parse(content)
                file_imports = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            file_imports.add(alias.name)
                            all_imports.add(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            file_imports.add(node.module)
                            all_imports.add(node.module)
                imports_by_file[file_path] = file_imports
            except Exception:
                pass

        repo_root = context.repository_path
        local_modules = set()
        for file_path in context.file_contents.keys():
            if file_path.endswith('.py'):
                module_path = file_path.replace('/', '.').replace('\\', '.').replace('.py', '')
                local_modules.add(module_path)
                parts = module_path.split('.')
                for i in range(1, len(parts) + 1):
                    local_modules.add('.'.join(parts[:i]))

        for file_path, imports in imports_by_file.items():
            for imp in imports:
                if any(imp.startswith(local) for local in local_modules):
                    internal_imports[file_path].add(imp)
                else:
                    external_imports[file_path].add(imp)

        circular_deps = self._find_circular_deps(internal_imports)

        for cycle in circular_deps[:5]:
            findings.append(self._create_finding(
                finding_id=f"circular_{'_'.join(cycle)}",
                severity=Severity.HIGH,
                title=f"Circular dependency detected",
                description=f"Circular import chain: {' -> '.join(cycle)}",
                evidence=f"Cycle length: {len(cycle)}",
                recommendation="Refactor to break circular dependency using dependency inversion or shared module"
            ))

        god_modules = []
        for file_path, imports in internal_imports.items():
            if len(imports) > 15:
                god_modules.append((file_path, len(imports)))

        for file_path, count in god_modules:
            findings.append(self._create_finding(
                finding_id=f"god_module_{file_path}",
                severity=Severity.MEDIUM,
                title=f"Potential god module: {file_path}",
                description=f"Module imports {count} other internal modules",
                evidence=f"Internal imports: {count}",
                recommendation="Consider splitting this module or using facade pattern"
            ))

        layered_violations = self._check_layering(internal_imports, context.file_contents.keys())
        for violation in layered_violations:
            findings.append(self._create_finding(
                finding_id=f"layer_{violation['from']}_{violation['to']}",
                severity=Severity.LOW,
                title=f"Layering violation",
                description=f"{violation['from']} imports {violation['to']} (wrong direction)",
                evidence=f"Direction: {violation['direction']}",
                recommendation="Ensure dependencies flow in correct architectural direction"
            ))

        avg_imports = sum(len(i) for i in internal_imports.values()) / len(internal_imports) if internal_imports else 0
        max_imports = max((len(i) for i in internal_imports.values()), default=0)

        metrics.extend([
            self._create_metric("total_modules", float(len(context.file_contents))),
            self._create_metric("avg_internal_imports", avg_imports, threshold=10),
            self._create_metric("max_internal_imports", max_imports, threshold=20),
            self._create_metric("circular_dependencies", float(len(circular_deps)), threshold=0),
            self._create_metric("god_modules_count", float(len(god_modules)), threshold=3),
            self._create_metric("layering_violations", float(len(layered_violations)), threshold=5),
            self._create_metric("external_dependencies", float(len(set().union(*external_imports.values()) if external_imports else set())))
        ])

        score = 100
        score -= len(circular_deps) * 15
        score -= len(god_modules) * 5
        score -= len(layered_violations) * 2
        if avg_imports > 15:
            score -= 10
        score = max(0, min(100, score))

        return CategoryScore(
            category=self.category,
            score=score,
            weight=self.weight,
            findings=findings,
            metrics=metrics
        )

    def _find_circular_deps(self, imports: Dict[str, Set[str]]) -> List[List[str]]:
        visited = set()
        rec_stack = set()
        cycles = []
        path = []

        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in imports.get(node, set()):
                if neighbor not in imports:
                    continue
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    if cycle not in cycles:
                        cycles.append(cycle)

            rec_stack.remove(node)
            path.pop()

        for node in imports:
            if node not in visited:
                dfs(node)

        return cycles

    def _check_layering(self, imports: Dict[str, Set[str]], all_files: List[str]) -> List[Dict]:
        violations = []
        layers = {
            'domain': ['domain', 'models', 'entities', 'core'],
            'application': ['application', 'services', 'use_cases', 'interactors'],
            'infrastructure': ['infrastructure', 'repositories', 'adapters', 'external'],
            'presentation': ['presentation', 'api', 'controllers', 'views', 'cli', 'web']
        }

        file_layers = {}
        for file_path in all_files:
            for layer, keywords in layers.items():
                if any(kw in file_path.lower() for kw in keywords):
                    file_layers[file_path] = layer
                    break

        layer_order = {'domain': 0, 'application': 1, 'infrastructure': 2, 'presentation': 3}

        for from_file, to_imports in imports.items():
            from_layer = file_layers.get(from_file)
            if not from_layer:
                continue
            for to_import in to_imports:
                to_file = None
                for f in all_files:
                    if to_import in f or f.endswith(to_import + '.py'):
                        to_file = f
                        break
                if to_file and to_file in file_layers:
                    to_layer = file_layers[to_file]
                    if layer_order.get(from_layer, 99) > layer_order.get(to_layer, 99):
                        violations.append({
                            'from': from_file,
                            'to': to_file,
                            'direction': f"{from_layer} -> {to_layer}"
                        })
        return violations