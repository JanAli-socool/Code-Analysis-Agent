"""
Testing Analysis Skill - Test coverage, test quality, test patterns
"""
import os
import subprocess
import ast
from typing import List
from advanced.skills.base import BaseSkill
from advanced.models import AgentContext, CategoryScore, AnalysisCategory, Finding, Severity, MetricResult


class TestingSkill(BaseSkill):
    def __init__(self):
        super().__init__("Testing Analysis", AnalysisCategory.TESTING, weight=1.5)

    def analyze(self, context: AgentContext) -> CategoryScore:
        findings = []
        metrics = []

        test_files = [f for f in context.file_contents.keys() 
                     if 'test' in f.lower() or f.endswith('_test.py') or f.startswith('test_')]
        source_files = [f for f in context.file_contents.keys() 
                       if f.endswith('.py') and f not in test_files]

        test_functions = 0
        test_classes = 0
        assertions = 0
        has_pytest = False
        has_unittest = False
        coverage_data = {}

        for file_path in test_files:
            content = context.file_contents[file_path]
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                        test_functions += 1
                    elif isinstance(node, ast.ClassDef) and node.name.startswith('Test'):
                        test_classes += 1
                    elif isinstance(node, ast.Call):
                        if hasattr(node.func, 'attr') and node.func.attr in ['assertEqual', 'assertTrue', 'assertFalse', 'assertRaises']:
                            assertions += 1
                        elif hasattr(node.func, 'id') and node.func.id.startswith('assert'):
                            assertions += 1
                
                if 'pytest' in content:
                    has_pytest = True
                if 'unittest' in content:
                    has_unittest = True
            except Exception:
                pass

        try:
            repo_root = context.repository_path
            result = subprocess.run(
                ['coverage', 'run', '-m', 'pytest', '--tb=short', '-q'],
                cwd=repo_root, capture_output=True, text=True, timeout=120
            )
            result = subprocess.run(
                ['coverage', 'json', '-o', '/tmp/coverage.json'],
                cwd=repo_root, capture_output=True, text=True
            )
            import json
            with open('/tmp/coverage.json') as f:
                coverage_data = json.load(f)
        except Exception:
            coverage_data = {}

        total_coverage = coverage_data.get('totals', {}).get('percent_covered', 0)
        files_covered = len([f for f in coverage_data.get('files', {}) if coverage_data['files'][f].get('summary', {}).get('percent_covered', 0) > 0])

        if len(source_files) > 0 and len(test_files) == 0:
            findings.append(self._create_finding(
                finding_id="no_tests",
                severity=Severity.HIGH,
                title="No test files found",
                description=f"Repository has {len(source_files)} source files but no test files detected",
                recommendation="Add unit tests for critical functionality"
            ))

        if total_coverage > 0 and total_coverage < 50:
            findings.append(self._create_finding(
                finding_id="low_coverage",
                severity=Severity.MEDIUM,
                title=f"Low test coverage: {total_coverage:.1f}%",
                description="Test coverage is below recommended 50% threshold",
                evidence=f"Coverage: {total_coverage:.1f}%",
                recommendation="Increase test coverage, especially for core business logic"
            ))

        if test_functions > 0 and assertions / test_functions < 1.5:
            findings.append(self._create_finding(
                finding_id="weak_assertions",
                severity=Severity.LOW,
                title="Low assertion density in tests",
                description=f"Average {assertions/test_functions:.1f} assertions per test function",
                recommendation="Add more specific assertions to improve test effectiveness"
            ))

        metrics.extend([
            self._create_metric("test_files_count", float(len(test_files))),
            self._create_metric("source_files_count", float(len(source_files))),
            self._create_metric("test_functions_count", float(test_functions)),
            self._create_metric("test_classes_count", float(test_classes)),
            self._create_metric("total_assertions", float(assertions)),
            self._create_metric("test_coverage_percent", total_coverage, threshold=80),
            self._create_metric("files_with_coverage", float(files_covered)),
            self._create_metric("uses_pytest", 1.0 if has_pytest else 0.0),
            self._create_metric("uses_unittest", 1.0 if has_unittest else 0.0)
        ])

        score = 0
        if len(test_files) > 0:
            score += 30
        if total_coverage >= 80:
            score += 40
        elif total_coverage >= 50:
            score += 25
        elif total_coverage > 0:
            score += 10
        if test_functions > len(source_files) * 2:
            score += 15
        elif test_functions > len(source_files):
            score += 10
        if assertions / max(test_functions, 1) >= 2:
            score += 10
        if has_pytest or has_unittest:
            score += 5

        score = min(100, score)

        return CategoryScore(
            category=self.category,
            score=score,
            weight=self.weight,
            findings=findings,
            metrics=metrics
        )