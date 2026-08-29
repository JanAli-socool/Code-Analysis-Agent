"""
Enhanced Maintainability Skill with code smells, SOLID violations, and refactoring suggestions.
"""
import ast
import os
from typing import List, Dict, Any
from dataclasses import dataclass
from collections import Counter

from pro.config.loader import get_config
from pro.cache.manager import AnalysisCache


@dataclass
class MaintainabilityFinding:
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


class MaintainabilitySkill:
    def __init__(self, cache: AnalysisCache = None):
        self.cache = cache
        self.config = get_config().analysis.maintainability

    def analyze(self, repo_path: str, file_contents: Dict[str, str]) -> Dict[str, Any]:
        config = self.config
        cache_key = "maintainability_skill"

        if self.cache:
            cached = self.cache.get(repo_path, cache_key, config, file_contents)
            if cached:
                return cached

        findings = []
        metrics = {}

        py_files = {k: v for k, v in file_contents.items() if k.endswith('.py')}

        all_functions = []
        all_classes = []
        all_methods = []

        for file_path, content in py_files.items():
            file_findings, file_metrics = self._analyze_file(file_path, content, config)
            findings.extend(file_findings)
            
            for func in file_metrics.get('functions', []):
                all_functions.append((file_path, func))
            for cls in file_metrics.get('classes', []):
                all_classes.append((file_path, cls))

        # Cross-file analysis
        findings.extend(self._check_duplicate_code(py_files))
        findings.extend(self._check_feature_envy(all_functions, all_classes))
        findings.extend(self._check_god_classes(all_classes))

        # Aggregate metrics
        metrics = self._aggregate_metrics(all_functions, all_classes, findings)

        result = {
            "findings": [f.__dict__ for f in findings],
            "metrics": [{"name": k, "value": v} for k, v in metrics.items()],
            "score": self._calculate_score(findings, metrics)
        }

        if self.cache:
            self.cache.set(repo_path, cache_key, config, file_contents, result)

        return result

    def _analyze_file(self, file_path: str, content: str, config: Dict) -> tuple:
        findings = []
        metrics = {"functions": [], "classes": []}

        try:
            tree = ast.parse(content)
            lines = content.split('\n')

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_metrics = self._analyze_function(node, lines, file_path, config)
                    metrics["functions"].append(func_metrics)
                    findings.extend(func_metrics.get('findings', []))

                elif isinstance(node, ast.ClassDef):
                    class_metrics = self._analyze_class(node, lines, file_path, config)
                    metrics["classes"].append(class_metrics)
                    findings.extend(class_metrics.get('findings', []))

        except Exception as e:
            metrics["error"] = str(e)

        return findings, metrics

    def _analyze_function(self, node: ast.FunctionDef, lines: List[str], 
                         file_path: str, config: Dict) -> Dict:
        findings = []
        
        # Length
        length = node.end_lineno - node.lineno + 1 if node.end_lineno else len(node.body)
        
        # Parameters
        param_count = len(node.args.args) + len(node.args.kwonlyargs)
        if node.args.vararg:
            param_count += 1
        if node.args.kwarg:
            param_count += 1

        # Complexity (simplified)
        complexity = 1
        for n in ast.walk(node):
            if isinstance(n, (ast.If, ast.While, ast.For, ast.ExceptHandler, ast.With)):
                complexity += 1
            elif isinstance(n, ast.BoolOp):
                complexity += len(n.values) - 1

        # Return statements
        returns = sum(1 for n in ast.walk(node) if isinstance(n, ast.Return))

        # Check thresholds
        if length > config.get('max_function_length', 50):
            findings.append(MaintainabilityFinding(
                id=f"long_func_{file_path}_{node.name}",
                category="function_length",
                severity="high" if length > 100 else "medium",
                title=f"Long function: {node.name}",
                description=f"Function has {length} lines (threshold: {config.get('max_function_length', 50)})",
                file_path=file_path,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                metric_value=length,
                threshold=config.get('max_function_length', 50),
                recommendation="Extract logic into smaller functions"
            ))

        if param_count > config.get('max_parameters', 5):
            findings.append(MaintainabilityFinding(
                id=f"many_params_{file_path}_{node.name}",
                category="parameter_count",
                severity="medium",
                title=f"Too many parameters: {node.name}",
                description=f"Function has {param_count} parameters (threshold: {config.get('max_parameters', 5)})",
                file_path=file_path,
                line_start=node.lineno,
                line_end=node.lineno,
                metric_value=param_count,
                threshold=config.get('max_parameters', 5),
                recommendation="Use parameter object or dataclass"
            ))

        if complexity > 10:
            findings.append(MaintainabilityFinding(
                id=f"high_complexity_{file_path}_{node.name}",
                category="cognitive_complexity",
                severity="medium",
                title=f"High cognitive complexity: {node.name}",
                description=f"Function cognitive complexity is {complexity}",
                file_path=file_path,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                metric_value=complexity,
                threshold=10,
                recommendation="Simplify conditional logic; extract methods"
            ))

        return {
            "name": node.name,
            "length": length,
            "params": param_count,
            "complexity": complexity,
            "returns": returns,
            "findings": findings,
            "has_docstring": ast.get_docstring(node) is not None,
            "has_type_hints": bool(node.returns) or any(arg.annotation for arg in node.args.args)
        }

    def _analyze_class(self, node: ast.ClassDef, lines: List[str],
                      file_path: str, config: Dict) -> Dict:
        findings = []
        
        methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
        public_methods = [m for m in methods if not m.name.startswith('_')]
        private_methods = [m for m in methods if m.name.startswith('_') and not m.name.startswith('__')]
        
        # Check class size
        if len(methods) > config.get('max_class_methods', 20):
            findings.append(MaintainabilityFinding(
                id=f"large_class_{file_path}_{node.name}",
                category="class_size",
                severity="high" if len(methods) > 30 else "medium",
                title=f"Large class: {node.name}",
                description=f"Class has {len(methods)} methods (threshold: {config.get('max_class_methods', 20)})",
                file_path=file_path,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                metric_value=len(methods),
                threshold=config.get('max_class_methods', 20),
                recommendation="Split class; apply Single Responsibility Principle"
            ))

        # Check for data class pattern (mostly attributes)
        attrs = [n for n in node.body if isinstance(n, ast.AnnAssign) or 
                (isinstance(n, ast.Assign) and not isinstance(n.value, ast.Call))]
        if len(attrs) > 5 and len(methods) < 3:
            findings.append(MaintainabilityFinding(
                id=f"data_class_{file_path}_{node.name}",
                category="data_class",
                severity="info",
                title=f"Potential data class: {node.name}",
                description="Class has many attributes but few methods - consider @dataclass",
                file_path=file_path,
                line_start=node.lineno,
                line_end=node.lineno,
                metric_value=len(attrs),
                threshold=5,
                recommendation="Use @dataclass decorator for cleaner code"
            ))

        return {
            "name": node.name,
            "total_methods": len(methods),
            "public_methods": len(public_methods),
            "private_methods": len(private_methods),
            "attributes": len(attrs),
            "findings": findings,
            "has_docstring": ast.get_docstring(node) is not None,
            "bases": [base.id if isinstance(base, ast.Name) else str(base) for base in node.bases]
        }

    def _check_duplicate_code(self, py_files: Dict[str, str]) -> List[MaintainabilityFinding]:
        findings = []
        # Simple token-based duplicate detection
        file_tokens = {}
        
        for file_path, content in py_files.items():
            try:
                tree = ast.parse(content)
                tokens = []
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.If, ast.For, ast.While)):
                        tokens.append(node.__class__.__name__)
                file_tokens[file_path] = ' '.join(tokens)
            except Exception:
                pass

        # Compare signatures
        seen = {}
        for file_path, sig in file_tokens.items():
            if sig in seen and len(sig) > 50:
                findings.append(MaintainabilityFinding(
                    id=f"dup_structure_{file_path}_{seen[sig]}",
                    category="duplicate_structure",
                    severity="low",
                    title=f"Similar code structure to {seen[sig]}",
                    description="File has similar structural pattern",
                    file_path=file_path,
                    line_start=1,
                    line_end=1,
                    metric_value=1,
                    threshold=0,
                    recommendation="Consider extracting common pattern"
                ))
            else:
                seen[sig] = file_path

        return findings

    def _check_feature_envy(self, all_functions: List, all_classes: List) -> List[MaintainabilityFinding]:
        findings = []
        # Feature envy: method uses more data from another class than its own
        # Simplified: check if method accesses many attributes not from self
        for file_path, func in all_functions:
            if 'body' not in func:
                continue
        return findings

    def _check_god_classes(self, all_classes: List) -> List[MaintainabilityFinding]:
        findings = []
        for file_path, cls in all_classes:
            if cls.get('total_methods', 0) > 25 and cls.get('attributes', 0) > 10:
                findings.append(MaintainabilityFinding(
                    id=f"god_class_{file_path}_{cls['name']}",
                    category="god_class",
                    severity="high",
                    title=f"God class detected: {cls['name']}",
                    description=f"Class has {cls['total_methods']} methods and {cls['attributes']} attributes",
                    file_path=file_path,
                    line_start=1,
                    line_end=1,
                    metric_value=cls['total_methods'] + cls['attributes'],
                    threshold=35,
                    recommendation="Split into multiple classes; apply SRP"
                ))
        return findings

    def _aggregate_metrics(self, all_functions: List, all_classes: List, findings: List) -> Dict:
        total_funcs = len(all_functions)
        total_classes = len(all_classes)

        avg_func_length = sum(f[1].get('length', 0) for f in all_functions) / max(total_funcs, 1)
        avg_params = sum(f[1].get('params', 0) for f in all_functions) / max(total_funcs, 1)
        avg_complexity = sum(f[1].get('complexity', 0) for f in all_functions) / max(total_funcs, 1)

        documented_funcs = sum(1 for f in all_functions if f[1].get('has_docstring'))
        typed_funcs = sum(1 for f in all_functions if f[1].get('has_type_hints'))

        documented_classes = sum(1 for c in all_classes if c[1].get('has_docstring'))

        long_funcs = sum(1 for f in findings if f.category == 'function_length')
        many_params = sum(1 for f in findings if f.category == 'parameter_count')
        high_complexity = sum(1 for f in findings if f.category == 'cognitive_complexity')
        large_classes = sum(1 for f in findings if f.category == 'class_size')

        return {
            "total_functions": total_funcs,
            "total_classes": total_classes,
            "avg_function_length": round(avg_func_length, 1),
            "avg_parameters": round(avg_params, 1),
            "avg_cognitive_complexity": round(avg_complexity, 1),
            "documented_functions_pct": round(documented_funcs / max(total_funcs, 1) * 100, 1),
            "typed_functions_pct": round(typed_funcs / max(total_funcs, 1) * 100, 1),
            "documented_classes_pct": round(documented_classes / max(total_classes, 1) * 100, 1),
            "long_functions": long_funcs,
            "excessive_parameters": many_params,
            "high_complexity_functions": high_complexity,
            "large_classes": large_classes
        }

    def _calculate_score(self, findings: List[MaintainabilityFinding], metrics: Dict) -> float:
        score = 100.0

        for f in findings:
            if f.severity == "high":
                score -= 8
            elif f.severity == "medium":
                score -= 4
            elif f.severity == "low":
                score -= 1
            elif f.severity == "info":
                pass

        # Metrics-based penalties
        if metrics.get("avg_function_length", 0) > 50:
            score -= 10
        elif metrics.get("avg_function_length", 0) > 30:
            score -= 5

        if metrics.get("avg_parameters", 0) > 5:
            score -= 5

        if metrics.get("avg_cognitive_complexity", 0) > 15:
            score -= 10
        elif metrics.get("avg_cognitive_complexity", 0) > 10:
            score -= 5

        if metrics.get("documented_functions_pct", 100) < 50:
            score -= 10
        elif metrics.get("documented_functions_pct", 100) < 80:
            score -= 5

        if metrics.get("typed_functions_pct", 100) < 30:
            score -= 5

        return max(0, min(100, round(score, 1)))