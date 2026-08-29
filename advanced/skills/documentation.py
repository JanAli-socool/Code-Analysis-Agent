"""
Documentation Analysis Skill - Docstrings, README, type hints, comments
"""
import ast
import os
from typing import List
from advanced.skills.base import BaseSkill
from advanced.models import AgentContext, CategoryScore, AnalysisCategory, Finding, Severity, MetricResult


class DocumentationSkill(BaseSkill):
    def __init__(self):
        super().__init__("Documentation Analysis", AnalysisCategory.DOCUMENTATION, weight=1.0)

    def analyze(self, context: AgentContext) -> CategoryScore:
        findings = []
        metrics = []

        total_functions = 0
        documented_functions = 0
        total_classes = 0
        documented_classes = 0
        total_modules = 0
        documented_modules = 0
        type_hinted_functions = 0
        has_readme = False
        readme_quality = 0

        for file_path, content in context.file_contents.items():
            if not file_path.endswith('.py'):
                continue

            total_modules += 1
            try:
                tree = ast.parse(content)
                
                if ast.get_docstring(tree):
                    documented_modules += 1

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        total_functions += 1
                        if ast.get_docstring(node):
                            documented_functions += 1
                        if node.returns or any(arg.annotation for arg in node.args.args):
                            type_hinted_functions += 1
                    elif isinstance(node, ast.ClassDef):
                        total_classes += 1
                        if ast.get_docstring(node):
                            documented_classes += 1

            except Exception:
                pass

        readme_files = [f for f in context.file_contents.keys() 
                       if os.path.basename(f).lower().startswith('readme')]
        if readme_files:
            has_readme = True
            readme_content = context.file_contents[readme_files[0]]
            readme_quality = self._score_readme(readme_content)

        if total_functions > 0 and documented_functions / total_functions < 0.5:
            findings.append(self._create_finding(
                finding_id="low_func_docs",
                severity=Severity.MEDIUM,
                title="Low function documentation coverage",
                description=f"Only {documented_functions}/{total_functions} functions have docstrings",
                evidence=f"Coverage: {documented_functions/total_functions*100:.1f}%",
                recommendation="Add docstrings to public functions and complex logic"
            ))

        if total_classes > 0 and documented_classes / total_classes < 0.5:
            findings.append(self._create_finding(
                finding_id="low_class_docs",
                severity=Severity.MEDIUM,
                title="Low class documentation coverage",
                description=f"Only {documented_classes}/{total_classes} classes have docstrings",
                evidence=f"Coverage: {documented_classes/total_classes*100:.1f}%",
                recommendation="Add docstrings to all public classes"
            ))

        if total_functions > 0 and type_hinted_functions / total_functions < 0.3:
            findings.append(self._create_finding(
                finding_id="low_type_hints",
                severity=Severity.LOW,
                title="Low type hint usage",
                description=f"Only {type_hinted_functions}/{total_functions} functions have type hints",
                evidence=f"Coverage: {type_hinted_functions/total_functions*100:.1f}%",
                recommendation="Add type hints for better code clarity and IDE support"
            ))

        if not has_readme:
            findings.append(self._create_finding(
                finding_id="no_readme",
                severity=Severity.HIGH,
                title="Missing README file",
                description="Repository lacks a README.md for documentation",
                recommendation="Add README with project overview, installation, and usage instructions"
            ))

        metrics.extend([
            self._create_metric("total_functions", float(total_functions)),
            self._create_metric("documented_functions", float(documented_functions)),
            self._create_metric("function_doc_coverage", documented_functions/max(total_functions,1)*100, threshold=80),
            self._create_metric("total_classes", float(total_classes)),
            self._create_metric("documented_classes", float(documented_classes)),
            self._create_metric("class_doc_coverage", documented_classes/max(total_classes,1)*100, threshold=80),
            self._create_metric("total_modules", float(total_modules)),
            self._create_metric("documented_modules", float(documented_modules)),
            self._create_metric("module_doc_coverage", documented_modules/max(total_modules,1)*100, threshold=60),
            self._create_metric("type_hinted_functions", float(type_hinted_functions)),
            self._create_metric("type_hint_coverage", type_hinted_functions/max(total_functions,1)*100, threshold=50),
            self._create_metric("has_readme", 1.0 if has_readme else 0.0),
            self._create_metric("readme_quality_score", float(readme_quality), threshold=50)
        ])

        score = 0
        if has_readme:
            score += 20
            score += min(20, readme_quality * 0.4)
        if total_functions > 0:
            score += (documented_functions / total_functions) * 30
        if total_classes > 0:
            score += (documented_classes / total_classes) * 20
        if total_functions > 0:
            score += (type_hinted_functions / total_functions) * 10
        score = min(100, score)

        return CategoryScore(
            category=self.category,
            score=score,
            weight=self.weight,
            findings=findings,
            metrics=metrics
        )

    def _score_readme(self, content: str) -> float:
        score = 0
        sections = ['install', 'usage', 'example', 'api', 'contribut', 'license', 'author', 'description']
        content_lower = content.lower()
        for section in sections:
            if section in content_lower:
                score += 10
        if len(content) > 500:
            score += 10
        if '```' in content:
            score += 10
        return min(100, score)