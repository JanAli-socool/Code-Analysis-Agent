"""
Maintainability Analysis Skill - Code duplication, naming conventions, structure
"""
import ast
import os
from collections import Counter
from typing import List, Set
from advanced.skills.base import BaseSkill
from advanced.models import AgentContext, CategoryScore, AnalysisCategory, Finding, Severity, MetricResult


class MaintainabilitySkill(BaseSkill):
    def __init__(self):
        super().__init__("Maintainability Analysis", AnalysisCategory.MAINTAINABILITY, weight=1.5)

    def analyze(self, context: AgentContext) -> CategoryScore:
        findings = []
        metrics = []

        all_functions = []
        all_classes = []
        all_names = []
        long_functions = []
        large_classes = []
        duplicate_names = []

        for file_path, content in context.file_contents.items():
            try:
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        all_functions.append((file_path, node.name, node.lineno, len(node.body)))
                        all_names.append(node.name)
                        if len(node.body) > 50:
                            long_functions.append((file_path, node.name, len(node.body), node.lineno))
                    elif isinstance(node, ast.ClassDef):
                        methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                        all_classes.append((file_path, node.name, node.lineno, len(methods)))
                        all_names.append(node.name)
                        if len(methods) > 20:
                            large_classes.append((file_path, node.name, len(methods), node.lineno))
                    elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                        all_names.append(node.id)

            except Exception:
                pass

        name_counts = Counter(all_names)
        duplicates = {name: count for name, count in name_counts.items() if count > 3}
        
        for name, count in duplicates.items():
            duplicate_names.append((name, count))

        for file_path, func_name, line_count, line_no in long_functions:
            findings.append(self._create_finding(
                finding_id=f"long_func_{file_path}_{func_name}",
                severity=Severity.MEDIUM if line_count > 100 else Severity.LOW,
                title=f"Long function: {func_name}",
                description=f"Function has {line_count} lines (recommended: <50)",
                file_path=file_path,
                line_number=line_no,
                evidence=f"Lines: {line_count}",
                recommendation="Break into smaller functions with single responsibilities"
            ))

        for file_path, class_name, method_count, line_no in large_classes:
            findings.append(self._create_finding(
                finding_id=f"large_class_{file_path}_{class_name}",
                severity=Severity.MEDIUM if method_count > 30 else Severity.LOW,
                title=f"Large class: {class_name}",
                description=f"Class has {method_count} methods (recommended: <20)",
                file_path=file_path,
                line_number=line_no,
                evidence=f"Methods: {method_count}",
                recommendation="Consider splitting into multiple classes following SRP"
            ))

        for name, count in duplicate_names[:10]:
            findings.append(self._create_finding(
                finding_id=f"dup_name_{name}",
                severity=Severity.LOW,
                title=f"Repeated identifier: {name}",
                description=f"Name '{name}' used {count} times across codebase",
                evidence=f"Count: {count}",
                recommendation="Consider more descriptive, unique names"
            ))

        avg_func_length = sum(f[3] for f in all_functions) / len(all_functions) if all_functions else 0
        avg_class_methods = sum(c[3] for c in all_classes) / len(all_classes) if all_classes else 0

        metrics.extend([
            self._create_metric("total_functions", float(len(all_functions))),
            self._create_metric("total_classes", float(len(all_classes))),
            self._create_metric("avg_function_length", avg_func_length, threshold=30,
                               details="Lines per function"),
            self._create_metric("avg_class_methods", avg_class_methods, threshold=15,
                               details="Methods per class"),
            self._create_metric("long_functions_count", float(len(long_functions)), threshold=5),
            self._create_metric("large_classes_count", float(len(large_classes)), threshold=3),
            self._create_metric("duplicate_names_count", float(len(duplicate_names)), threshold=10)
        ])

        score = 100
        score -= len(long_functions) * 3
        score -= len(large_classes) * 5
        score -= len(duplicate_names) * 1
        if avg_func_length > 50:
            score -= 10
        if avg_class_methods > 25:
            score -= 10
        score = max(0, min(100, score))

        return CategoryScore(
            category=self.category,
            score=score,
            weight=self.weight,
            findings=findings,
            metrics=metrics
        )