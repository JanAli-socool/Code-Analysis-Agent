"""
Enhanced Architecture Skill with dependency graph analysis, layering, and pattern detection.
"""
import ast
import os
from typing import List, Dict, Any, Set, Optional
from dataclasses import dataclass
from collections import defaultdict, deque
from pathlib import Path

from pro.config.loader import get_config
from pro.cache.manager import AnalysisCache


@dataclass
class ArchitectureFinding:
    id: str
    category: str
    severity: str
    title: str
    description: str
    file_path: str
    line_start: int
    line_end: int
    metric_value: float
    threshold: float
    recommendation: str


class ArchitectureSkill:
    def __init__(self, cache: AnalysisCache = None):
        self.cache = cache
        self.config = get_config().analysis.architecture

    def analyze(self, repo_path: str, file_contents: Dict[str, str]) -> Dict[str, Any]:
        config = self.config
        cache_key = "architecture_skill"

        if self.cache:
            cached = self.cache.get(repo_path, cache_key, config, file_contents)
            if cached:
                return cached

        findings = []

        # Build import graph
        import_graph = self._build_import_graph(file_contents)
        
        # Detect circular dependencies
        cycles = self._find_circular_dependencies(import_graph)
        for cycle in cycles:
            findings.append(ArchitectureFinding(
                id=f"circular_{'_'.join(cycle)}",
                category="circular_dependency",
                severity="high",
                title=f"Circular dependency detected",
                description=f"Circular import chain: {' -> '.join(cycle)} -> {cycle[0]}",
                file_path=cycle[0],
                line_start=1,
                line_end=1,
                metric_value=len(cycle),
                threshold=0,
                recommendation="Break cycle using dependency inversion or shared module"
            ))

        # Detect god modules
        god_modules = self._find_god_modules(import_graph)
        for module, fan_in, fan_out in god_modules:
            findings.append(ArchitectureFinding(
                id=f"god_module_{module}",
                category="god_module",
                severity="medium" if fan_out > 20 else "low",
                title=f"Potential god module: {module}",
                description=f"Module has {fan_out} outgoing and {fan_in} incoming dependencies",
                file_path=module,
                line_start=1,
                line_end=1,
                metric_value=fan_out + fan_in,
                threshold=15,
                recommendation="Split module; apply facade or mediator pattern"
            ))

        # Check layering violations
        layer_violations = self._check_layering(import_graph, file_contents)
        for violation in layer_violations:
            findings.append(ArchitectureFinding(
                id=f"layer_{violation['from']}_{violation['to']}",
                category="layering_violation",
                severity="low",
                title=f"Layering violation",
                description=f"{violation['from']} ({violation['from_layer']}) imports {violation['to']} ({violation['to_layer']})",
                file_path=violation['from'],
                line_start=1,
                line_end=1,
                metric_value=1,
                threshold=0,
                recommendation=f"Ensure dependencies flow: domain -> application -> infrastructure -> presentation"
            ))

        # Detect architectural patterns
        patterns = self._detect_patterns(file_contents)
        
        # Calculate metrics
        metrics = self._calculate_metrics(import_graph, cycles, god_modules, layer_violations, patterns)
        
        result = {
            "findings": [f.__dict__ for f in findings],
            "metrics": [{"name": k, "value": v} for k, v in metrics.items()],
            "score": self._calculate_score(findings, metrics)
        }

        if self.cache:
            self.cache.set(repo_path, cache_key, config, file_contents, result)

        return result

    def _build_import_graph(self, file_contents: Dict[str, str]) -> Dict[str, Set[str]]:
        """Build directed graph of internal imports."""
        py_files = {k: v for k, v in file_contents.items() if k.endswith('.py')}
        
        # Map file paths to module names
        module_map = {}
        for path in py_files:
            module = path.replace('/', '.').replace('\\', '.').replace('.py', '')
            module_map[path] = module

        # Reverse map for lookup
        module_to_file = {v: k for k, v in module_map.items()}

        graph = defaultdict(set)
        local_modules = set(module_map.values())
        
        # Add parent modules too
        for mod in list(local_modules):
            parts = mod.split('.')
            for i in range(1, len(parts) + 1):
                local_modules.add('.'.join(parts[:i]))

        for file_path, content in py_files.items():
            try:
                tree = ast.parse(content)
                from_module = module_map[file_path]
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name in local_modules:
                                graph[from_module].add(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and node.module in local_modules:
                            graph[from_module].add(node.module)
            except Exception:
                pass

        return dict(graph)

    def _find_circular_dependencies(self, graph: Dict[str, Set[str]]) -> List[List[str]]:
        """Find all circular dependencies using Tarjan's algorithm."""
        visited = set()
        rec_stack = set()
        path = []
        cycles = []

        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, set()):
                if neighbor not in graph:
                    continue
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    # Found cycle
                    idx = path.index(neighbor)
                    cycle = path[idx:] + [neighbor]
                    # Normalize cycle (start from smallest)
                    min_idx = cycle.index(min(cycle[:-1]))
                    normalized = cycle[min_idx:-1] + cycle[:min_idx] + [cycle[min_idx]]
                    if normalized not in cycles:
                        cycles.append(normalized)

            rec_stack.remove(node)
            path.pop()

        for node in graph:
            if node not in visited:
                dfs(node)

        return cycles

    def _find_god_modules(self, graph: Dict[str, Set[str]]) -> List[tuple]:
        """Find modules with high fan-in and fan-out."""
        # Calculate fan-in (reverse graph)
        reverse_graph = defaultdict(set)
        for src, targets in graph.items():
            for tgt in targets:
                reverse_graph[tgt].add(src)

        god_modules = []
        for module in graph:
            fan_out = len(graph.get(module, set()))
            fan_in = len(reverse_graph.get(module, set()))
            
            if fan_out > 15 or fan_in > 10:
                god_modules.append((module, fan_in, fan_out))

        return sorted(god_modules, key=lambda x: x[1] + x[2], reverse=True)[:10]

    def _check_layering(self, graph: Dict[str, Set[str]], file_contents: Dict[str, str]) -> List[Dict]:
        """Check for layering violations based on configured layers."""
        violations = []
        layer_rules = self.config.get('layering_rules', [])
        
        # Normalize layer rules - handle both formats:
        # Format 1: [{"name": "domain", "keywords": [...]}]
        # Format 2: [{"domain": [...]}]
        normalized_layers = []
        for layer in layer_rules:
            if 'name' in layer and 'keywords' in layer:
                normalized_layers.append(layer)
            else:
                # Format 2: single key dict
                for name, keywords in layer.items():
                    normalized_layers.append({'name': name, 'keywords': keywords})
        
        if not normalized_layers:
            return violations

        # Map files to layers
        file_layers = {}
        for file_path in file_contents:
            if not file_path.endswith('.py'):
                continue
            for layer in normalized_layers:
                for keyword in layer.get('keywords', []):
                    if keyword in file_path.lower():
                        file_layers[file_path] = layer['name']
                        break

        layer_order = {layer['name']: i for i, layer in enumerate(normalized_layers)}

        for from_file, imports in graph.items():
            from_path = None
            for fp in file_contents:
                if fp.endswith('.py') and fp.replace('/', '.').replace('\\', '.').replace('.py', '') == from_file:
                    from_path = fp
                    break
            
            if not from_path or from_path not in file_layers:
                continue
                
            from_layer = file_layers[from_path]
            from_order = layer_order.get(from_layer, 99)

            for to_module in imports:
                to_path = None
                for fp in file_contents:
                    if fp.endswith('.py') and fp.replace('/', '.').replace('\\', '.').replace('.py', '') == to_module:
                        to_path = fp
                        break
                
                if to_path and to_path in file_layers:
                    to_layer = file_layers[to_path]
                    to_order = layer_order.get(to_layer, 99)
                    
                    # Violation: higher layer imports lower layer
                    if from_order > to_order:
                        violations.append({
                            'from': from_path,
                            'to': to_path,
                            'from_layer': from_layer,
                            'to_layer': to_layer
                        })

        return violations

    def _detect_patterns(self, file_contents: Dict[str, str]) -> Dict[str, Any]:
        """Detect common architectural patterns."""
        patterns = {
            "repository_pattern": False,
            "factory_pattern": False,
            "singleton_pattern": False,
            "dependency_injection": False,
            "mvc_structure": False,
            "clean_architecture": False
        }

        for file_path, content in file_contents.items():
            if not file_path.endswith('.py'):
                continue
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    # Repository pattern: class with CRUD methods
                    if isinstance(node, ast.ClassDef):
                        methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                        crud_methods = {'get', 'create', 'update', 'delete', 'find', 'save', 'list'}
                        if len(crud_methods & set(methods)) >= 3:
                            patterns["repository_pattern"] = True

                        # Factory pattern
                        if any('factory' in n.name.lower() for n in node.body if isinstance(n, ast.FunctionDef)):
                            patterns["factory_pattern"] = True

                        # Singleton
                        if '__new__' in methods or 'get_instance' in methods:
                            patterns["singleton_pattern"] = True

                    # Dependency injection: __init__ with typed parameters
                    if isinstance(node, ast.FunctionDef) and node.name == '__init__':
                        for arg in node.args.args:
                            if arg.annotation:
                                patterns["dependency_injection"] = True

                    # MVC structure detection
                    if 'controller' in file_path.lower() or 'view' in file_path.lower():
                        patterns["mvc_structure"] = True

                # Clean architecture: distinct layer directories
                if any(layer in file_path.lower() for layer in 
                       ['domain', 'application', 'infrastructure', 'presentation']):
                    patterns["clean_architecture"] = True

            except Exception:
                pass

        return patterns

    def _calculate_metrics(self, graph: Dict, cycles: List, god_modules: List, 
                          violations: List, patterns: Dict) -> Dict:
        all_nodes = set(graph.keys())
        for targets in graph.values():
            all_nodes.update(targets)

        # Calculate coupling metrics
        total_edges = sum(len(targets) for targets in graph.values())
        avg_fan_out = total_edges / max(len(graph), 1)
        
        # Instability metric (fan_out / (fan_in + fan_out))
        instabilities = []
        reverse_graph = defaultdict(set)
        for src, targets in graph.items():
            for tgt in targets:
                reverse_graph[tgt].add(src)

        for node in all_nodes:
            fan_out = len(graph.get(node, set()))
            fan_in = len(reverse_graph.get(node, set()))
            if fan_in + fan_out > 0:
                instabilities.append(fan_out / (fan_in + fan_out))

        avg_instability = sum(instabilities) / len(instabilities) if instabilities else 0

        return {
            "total_modules": len(all_nodes),
            "total_dependencies": total_edges,
            "avg_fan_out": round(avg_fan_out, 2),
            "avg_instability": round(avg_instability, 3),
            "circular_dependencies": len(cycles),
            "god_modules": len(god_modules),
            "layering_violations": len(violations),
            "max_fan_out": max((len(v) for v in graph.values()), default=0),
            "repository_pattern": patterns.get("repository_pattern", False),
            "factory_pattern": patterns.get("factory_pattern", False),
            "dependency_injection": patterns.get("dependency_injection", False),
            "clean_architecture": patterns.get("clean_architecture", False),
            "mvc_structure": patterns.get("mvc_structure", False)
        }

    def _calculate_score(self, findings: List[ArchitectureFinding], metrics: Dict) -> float:
        score = 100.0

        # Penalize findings
        for f in findings:
            if f.severity == "high":
                score -= 15
            elif f.severity == "medium":
                score -= 8
            elif f.severity == "low":
                score -= 3

        # Bonus for good patterns
        if metrics.get("clean_architecture"):
            score += 10
        if metrics.get("dependency_injection"):
            score += 5
        if metrics.get("repository_pattern"):
            score += 5

        # Penalize based on metrics
        if metrics.get("circular_dependencies", 0) > 0:
            score -= metrics["circular_dependencies"] * 10
        if metrics.get("god_modules", 0) > 0:
            score -= metrics["god_modules"] * 5
        if metrics.get("layering_violations", 0) > 5:
            score -= 10
        elif metrics.get("layering_violations", 0) > 0:
            score -= 5

        if metrics.get("avg_instability", 0) > 0.8:
            score -= 10
        elif metrics.get("avg_instability", 0) > 0.6:
            score -= 5

        return max(0, min(100, round(score, 1)))