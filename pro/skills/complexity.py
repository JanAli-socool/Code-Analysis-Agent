"""
Enhanced Complexity Skill with Halstead metrics, cognitive complexity, and duplication detection.
"""
import ast
import json
import subprocess
import tempfile
import os
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from collections import Counter

import radon.complexity as radon_cc
import radon.metrics as radon_metrics
import radon.raw as radon_raw
from radon.visitors import ComplexityVisitor

from pro.config.loader import get_config
from pro.cache.manager import AnalysisCache


@dataclass
class ComplexityFinding:
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


class ComplexitySkill:
    def __init__(self, cache: AnalysisCache = None):
        self.cache = cache
        self.config = get_config().analysis.complexity

    def analyze(self, repo_path: str, file_contents: Dict[str, str]) -> Dict[str, Any]:
        config = self.config
        cache_key = "complexity_skill"

        if self.cache:
            cached = self.cache.get(repo_path, cache_key, config, file_contents)
            if cached:
                return cached

        findings = []
        all_metrics = []

        py_files = {k: v for k, v in file_contents.items() if k.endswith('.py')}

        for file_path, content in py_files.items():
            file_findings, file_metrics = self._analyze_file(file_path, content)
            findings.extend(file_findings)
            all_metrics.append(file_metrics)

        # Aggregate metrics
        agg_metrics = self._aggregate_metrics(all_metrics)
        
        # Cross-file duplication detection
        dup_findings = self._detect_duplication(py_files)
        findings.extend(dup_findings)

        # Cyclomatic complexity distribution
        cc_dist = self._complexity_distribution(all_metrics)
        agg_metrics.append({"name": "complexity_distribution", "value": cc_dist})

        result = {
            "findings": [f.__dict__ for f in findings],
            "metrics": agg_metrics,
            "score": self._calculate_score(findings, agg_metrics)
        }

        if self.cache:
            self.cache.set(repo_path, cache_key, config, file_contents, result)

        return result

    def _analyze_file(self, file_path: str, content: str) -> tuple:
        findings = []
        metrics = {"file": file_path}

        try:
            # Radon cyclomatic complexity
            cc_results = radon_cc.cc_visit(content)
            complexities = [item.complexity for item in cc_results]
            
            metrics.update({
                "functions": len(cc_results),
                "avg_complexity": sum(complexities) / len(complexities) if complexities else 0,
                "max_complexity": max(complexities) if complexities else 0,
                "complexity_counts": Counter(complexities)
            })

            # Flag high complexity functions
            for item in cc_results:
                if item.complexity > self.config.get('max_cyclomatic_complexity', 15):
                    findings.append(ComplexityFinding(
                        id=f"cc_{file_path}_{item.name}_{item.lineno}",
                        category="cyclomatic_complexity",
                        severity="high" if item.complexity > 25 else "medium",
                        title=f"High cyclomatic complexity: {item.name}",
                        description=f"Function has cyclomatic complexity {item.complexity} (threshold: {self.config.get('max_cyclomatic_complexity', 15)})",
                        file_path=file_path,
                        line_start=item.lineno,
                        line_end=item.endline or item.lineno,
                        metric_value=item.complexity,
                        threshold=self.config.get('max_cyclomatic_complexity', 15),
                        recommendation="Decompose into smaller functions; extract conditional logic"
                    ))

            # Maintainability Index
            mi_score = radon_metrics.mi_visit(content, multi=True)
            metrics["maintainability_index"] = mi_score
            if mi_score < self.config.get('max_maintainability_index', 65):
                findings.append(ComplexityFinding(
                    id=f"mi_{file_path}",
                    category="maintainability_index",
                    severity="medium" if mi_score < 40 else "low",
                    title=f"Low maintainability index: {mi_score:.1f}",
                    description=f"File maintainability index below threshold ({self.config.get('max_maintainability_index', 65)})",
                    file_path=file_path,
                    line_start=1,
                    line_end=len(content.split('\n')),
                    metric_value=mi_score,
                    threshold=self.config.get('max_maintainability_index', 65),
                    recommendation="Reduce complexity, improve naming, add documentation"
                ))

            # Raw metrics
            raw = radon_raw.analyze(content)
            metrics.update({
                "loc": raw.loc,
                "lloc": raw.lloc,
                "comments": raw.comments,
                "multi": raw.multi,
                "blank": raw.blank,
                "single_comments": raw.single_comments
            })

            # Halstead metrics (via radon)
            try:
                from radon.metrics import h_visit
                halstead = h_visit(content)
                if halstead:
                    h = halstead[0]
                    metrics.update({
                        "halstead_volume": h.volume,
                        "halstead_difficulty": h.difficulty,
                        "halstead_effort": h.effort,
                        "halstead_time": h.time,
                        "halstead_bugs": h.bugs
                    })
            except Exception:
                pass

            # Cognitive complexity (manual calculation)
            cog_complexity = self._calculate_cognitive_complexity(content)
            metrics["cognitive_complexity"] = cog_complexity

            # Nesting depth
            max_nesting = self._max_nesting_depth(content)
            metrics["max_nesting_depth"] = max_nesting
            if max_nesting > self.config.get('max_nesting_depth', 4):
                findings.append(ComplexityFinding(
                    id=f"nesting_{file_path}",
                    category="nesting_depth",
                    severity="medium",
                    title=f"Excessive nesting depth: {max_nesting}",
                    description=f"Maximum nesting depth exceeds threshold ({self.config.get('max_nesting_depth', 4)})",
                    file_path=file_path,
                    line_start=1,
                    line_end=len(content.split('\n')),
                    metric_value=max_nesting,
                    threshold=self.config.get('max_nesting_depth', 4),
                    recommendation="Extract nested logic into functions; use guard clauses"
                ))

        except Exception as e:
            metrics["error"] = str(e)

        return findings, metrics

    def _calculate_cognitive_complexity(self, content: str) -> float:
        """Calculate cognitive complexity - more accurate than cyclomatic."""
        try:
            tree = ast.parse(content)
            total = 0
            for node in ast.walk(tree):
                if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                    total += 1
                elif isinstance(node, ast.BoolOp):
                    total += len(node.values) - 1
                elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                    total += 1
                elif isinstance(node, ast.Lambda):
                    total += 1
                elif isinstance(node, ast.Try):
                    total += len(node.handlers)
            return total
        except Exception:
            return 0

    def _max_nesting_depth(self, content: str) -> int:
        try:
            tree = ast.parse(content)
            max_depth = 0
            
            def visit(node, depth=0):
                nonlocal max_depth
                max_depth = max(max_depth, depth)
                nesting_nodes = (ast.If, ast.While, ast.For, ast.Try, ast.With, ast.FunctionDef, ast.ClassDef)
                if isinstance(node, nesting_nodes):
                    for child in ast.iter_child_nodes(node):
                        visit(child, depth + 1)
                else:
                    for child in ast.iter_child_nodes(node):
                        visit(child, depth)
            
            visit(tree)
            return max_depth
        except Exception:
            return 0

    def _aggregate_metrics(self, all_metrics: List[Dict]) -> List[Dict]:
        if not all_metrics:
            return []

        agg = {}
        numeric_keys = [
            'functions', 'avg_complexity', 'max_complexity', 'maintainability_index',
            'loc', 'lloc', 'comments', 'blank', 'cognitive_complexity', 'max_nesting_depth',
            'halstead_volume', 'halstead_difficulty', 'halstead_effort', 'halstead_bugs'
        ]

        for key in numeric_keys:
            values = [m.get(key, 0) for m in all_metrics if key in m and m[key] is not None]
            if values:
                agg[f"total_{key}"] = sum(values)
                agg[f"avg_{key}"] = sum(values) / len(values)
                agg[f"max_{key}"] = max(values)

        # File count
        agg["total_files"] = len(all_metrics)

        # Comment ratio
        total_loc = agg.get("total_loc", 1)
        total_comments = agg.get("total_comments", 0)
        agg["comment_ratio"] = total_comments / total_loc if total_loc > 0 else 0

        return [{"name": k, "value": v} for k, v in agg.items()]

    def _detect_duplication(self, py_files: Dict[str, str]) -> List[ComplexityFinding]:
        """Detect code duplication using normalized AST comparison."""
        findings = []
        file_signatures = {}

        for file_path, content in py_files.items():
            try:
                tree = ast.parse(content)
                # Normalize: remove names, keep structure
                normalized = self._normalize_ast(tree)
                sig = hash(normalized)
                file_signatures[file_path] = sig
            except Exception:
                pass

        # Find duplicates
        sig_to_files = {}
        for f, sig in file_signatures.items():
            sig_to_files.setdefault(sig, []).append(f)

        for sig, files in sig_to_files.items():
            if len(files) > 1:
                for f in files:
                    findings.append(ComplexityFinding(
                        id=f"dup_{sig}_{f}",
                        category="duplication",
                        severity="medium",
                        title=f"Duplicate code structure",
                        description=f"File has identical structure to: {', '.join([x for x in files if x != f])}",
                        file_path=f,
                        line_start=1,
                        line_end=1,
                        metric_value=len(files),
                        threshold=1,
                        recommendation="Extract common functionality into shared module"
                    ))

        return findings

    def _normalize_ast(self, tree: ast.AST) -> str:
        """Create normalized AST signature."""
        parts = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.If, ast.For, ast.While, ast.Try)):
                parts.append(node.__class__.__name__)
        return '|'.join(parts)

    def _complexity_distribution(self, all_metrics: List[Dict]) -> Dict[str, int]:
        dist = {"1-5": 0, "6-10": 0, "11-20": 0, "21-50": 0, "50+": 0}
        for m in all_metrics:
            for count, cnt in m.get("complexity_counts", {}).items():
                if count <= 5:
                    dist["1-5"] += cnt
                elif count <= 10:
                    dist["6-10"] += cnt
                elif count <= 20:
                    dist["11-20"] += cnt
                elif count <= 50:
                    dist["21-50"] += cnt
                else:
                    dist["50+"] += cnt
        return dist

    def _calculate_score(self, findings: List[ComplexityFinding], metrics: List[Dict]) -> float:
        score = 100.0
        metric_dict = {m['name']: m['value'] for m in metrics}

        # Penalize based on findings
        for f in findings:
            if f.severity == "high":
                score -= 10
            elif f.severity == "medium":
                score -= 5
            elif f.severity == "low":
                score -= 2

        # Penalize based on aggregate metrics
        avg_cc = metric_dict.get('avg_avg_complexity', 0)
        if avg_cc > 15:
            score -= 20
        elif avg_cc > 10:
            score -= 10
        elif avg_cc > 5:
            score -= 5

        max_cc = metric_dict.get('max_max_complexity', 0)
        if max_cc > 30:
            score -= 15
        elif max_cc > 20:
            score -= 10

        avg_mi = metric_dict.get('avg_maintainability_index', 100)
        if avg_mi < 40:
            score -= 20
        elif avg_mi < 65:
            score -= 10

        return max(0, min(100, round(score, 1)))