"""
Complexity Analysis Skill - Uses radon for cyclomatic complexity, maintainability index, etc.
"""
import radon.complexity as radon_cc
import radon.metrics as radon_metrics
from radon.raw import analyze as radon_raw
from typing import List
import ast
from advanced.skills.base import BaseSkill
from advanced.models import AgentContext, CategoryScore, AnalysisCategory, Finding, Severity, MetricResult


class ComplexitySkill(BaseSkill):
    def __init__(self):
        super().__init__("Complexity Analysis", AnalysisCategory.COMPLEXITY, weight=1.5)

    def analyze(self, context: AgentContext) -> CategoryScore:
        findings = []
        metrics = []
        all_complexities = []
        all_mi_scores = []
        total_functions = 0
        total_classes = 0
        high_complexity_functions = []

        for file_path, content in context.file_contents.items():
            try:
                cc_results = radon_cc.cc_visit(content)
                for item in cc_results:
                    all_complexities.append(item.complexity)
                    total_functions += 1
                    if item.complexity > 15:
                        high_complexity_functions.append({
                            'file': file_path,
                            'function': item.name,
                            'complexity': item.complexity,
                            'line': item.lineno
                        })
                        findings.append(self._create_finding(
                            finding_id=f"complexity_{file_path}_{item.name}",
                            severity=Severity.HIGH if item.complexity > 20 else Severity.MEDIUM,
                            title=f"High cyclomatic complexity: {item.name}",
                            description=f"Function '{item.name}' has cyclomatic complexity of {item.complexity} (threshold: 15)",
                            file_path=file_path,
                            line_number=item.lineno,
                            evidence=f"Complexity: {item.complexity}",
                            recommendation="Consider breaking this function into smaller, more focused functions"
                        ))

                mi_score = radon_metrics.mi_visit(content, multi=True)
                all_mi_scores.append(mi_score)

                raw_metrics = radon_raw(content)
                total_classes += len([n for n in ast.parse(content).body if isinstance(n, ast.ClassDef)])

            except Exception as e:
                findings.append(self._create_finding(
                    finding_id=f"parse_error_{file_path}",
                    severity=Severity.LOW,
                    title=f"Parse error in {file_path}",
                    description=str(e),
                    file_path=file_path,
                    recommendation="Fix syntax errors to enable full analysis"
                ))

        avg_complexity = sum(all_complexities) / len(all_complexities) if all_complexities else 0
        avg_mi = sum(all_mi_scores) / len(all_mi_scores) if all_mi_scores else 100
        max_complexity = max(all_complexities) if all_complexities else 0

        metrics.extend([
            self._create_metric("avg_cyclomatic_complexity", avg_complexity, threshold=10, 
                               details=f"Across {total_functions} functions"),
            self._create_metric("max_cyclomatic_complexity", max_complexity, threshold=20,
                               details="Highest single function complexity"),
            self._create_metric("avg_maintainability_index", avg_mi, threshold=65,
                               details="Higher is better (0-100)"),
            self._create_metric("total_functions", float(total_functions)),
            self._create_metric("total_classes", float(total_classes)),
            self._create_metric("high_complexity_functions", float(len(high_complexity_functions)), threshold=5)
        ])

        score = 100
        if avg_complexity > 15:
            score -= 30
        elif avg_complexity > 10:
            score -= 15
        elif avg_complexity > 5:
            score -= 5

        if max_complexity > 30:
            score -= 20
        elif max_complexity > 20:
            score -= 10

        if avg_mi < 50:
            score -= 25
        elif avg_mi < 65:
            score -= 10

        score = max(0, min(100, score))

        return CategoryScore(
            category=self.category,
            score=score,
            weight=self.weight,
            findings=findings,
            metrics=metrics
        )