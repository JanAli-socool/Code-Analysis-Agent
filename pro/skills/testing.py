"""
Enhanced Testing Skill with coverage analysis, mutation testing, and test quality metrics.
"""
import ast
import json
import subprocess
import os
import tempfile
import shutil
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from pro.config.loader import get_config
from pro.cache.manager import AnalysisCache


@dataclass
class TestingFinding:
    id: str
    category: str
    severity: str
    title: str
    description: str
    file_path: Optional[str]
    line_start: Optional[int]
    line_end: Optional[int]
    metric_value: float
    threshold: float
    recommendation: str


class TestingSkill:
    def __init__(self, cache: AnalysisCache = None):
        self.cache = cache
        self.config = get_config().analysis.testing

    def analyze(self, repo_path: str, file_contents: Dict[str, str]) -> Dict[str, Any]:
        config = self.config
        cache_key = "testing_skill"

        if self.cache:
            cached = self.cache.get(repo_path, cache_key, config, file_contents)
            if cached:
                return cached

        findings = []
        metrics = {}

        # Discover test files
        test_files, source_files = self._discover_files(file_contents)
        
        metrics.update({
            "test_files_count": len(test_files),
            "source_files_count": len(source_files),
            "test_to_source_ratio": len(test_files) / max(len(source_files), 1)
        })

        # Analyze test structure
        test_structure = self._analyze_test_structure(test_files, file_contents)
        metrics.update(test_structure)

        # Run coverage if possible
        coverage_data = self._run_coverage(repo_path, file_contents)
        metrics.update(coverage_data)

        # Run mutation testing (if available)
        mutation_data = self._run_mutation_testing(repo_path, file_contents)
        metrics.update(mutation_data)

        # Check test quality
        quality_findings = self._check_test_quality(test_files, file_contents)
        findings.extend(quality_findings)

        # Check for missing tests
        missing_test_findings = self._check_missing_tests(source_files, test_files, file_contents)
        findings.extend(missing_test_findings)

        result = {
            "findings": [f.__dict__ for f in findings],
            "metrics": [{"name": k, "value": v} for k, v in metrics.items()],
            "score": self._calculate_score(findings, metrics)
        }

        if self.cache:
            self.cache.set(repo_path, cache_key, config, file_contents, result)

        return result

    def _discover_files(self, file_contents: Dict[str, str]) -> tuple:
        test_files = []
        source_files = []

        for path in file_contents.keys():
            if not path.endswith('.py'):
                continue
            name = Path(path).name
            if (name.startswith('test_') or name.endswith('_test.py') or 
                'test' in Path(path).parts or name == 'conftest.py'):
                test_files.append(path)
            else:
                source_files.append(path)

        return test_files, source_files

    def _analyze_test_structure(self, test_files: List[str], file_contents: Dict[str, str]) -> Dict:
        total_tests = 0
        total_assertions = 0
        test_classes = 0
        test_functions = 0
        uses_pytest = False
        uses_unittest = False
        parametrized_tests = 0
        fixtures = 0

        for file_path in test_files:
            content = file_contents.get(file_path, '')
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        if node.name.startswith('test_'):
                            test_functions += 1
                            total_tests += 1
                            # Count assertions
                            for n in ast.walk(node):
                                if isinstance(n, ast.Call):
                                    if (isinstance(n.func, ast.Attribute) and 
                                        n.func.attr.startswith('assert')):
                                        total_assertions += 1
                                    elif (isinstance(n.func, ast.Name) and 
                                          n.func.id.startswith('assert')):
                                        total_assertions += 1
                            # Check for pytest parametrize
                            for dec in node.decorator_list:
                                if (isinstance(dec, ast.Call) and 
                                    isinstance(dec.func, ast.Attribute) and
                                    dec.func.attr == 'parametrize'):
                                    parametrized_tests += 1
                                elif (isinstance(dec, ast.Name) and dec.id == 'fixture'):
                                    fixtures += 1
                    elif isinstance(node, ast.ClassDef):
                        if node.name.startswith('Test'):
                            test_classes += 1
                
                if 'pytest' in content:
                    uses_pytest = True
                if 'unittest' in content:
                    uses_unittest = True

            except Exception:
                pass

        return {
            "total_test_functions": test_functions,
            "total_test_classes": test_classes,
            "total_assertions": total_assertions,
            "assertions_per_test": total_assertions / max(test_functions, 1),
            "parametrized_tests": parametrized_tests,
            "fixtures_count": fixtures,
            "uses_pytest": uses_pytest,
            "uses_unittest": uses_unittest
        }

    def _run_coverage(self, repo_path: str, file_contents: Dict[str, str]) -> Dict:
        """Run coverage analysis."""
        metrics = {"coverage_percent": 0.0, "covered_files": 0, "uncovered_files": 0}

        # Check if pytest and coverage are available
        try:
            # Create temp directory with source
            with tempfile.TemporaryDirectory() as tmpdir:
                for rel_path, content in file_contents.items():
                    if rel_path.endswith('.py'):
                        full_path = Path(tmpdir) / rel_path
                        full_path.parent.mkdir(parents=True, exist_ok=True)
                        full_path.write_text(content)

                # Run pytest with coverage
                cmd = ['python', '-m', 'pytest', '--cov=.', '--cov-report=json', 
                       '--tb=short', '-q', '--disable-warnings']
                result = subprocess.run(cmd, cwd=tmpdir, capture_output=True, text=True, timeout=180)

                # Parse coverage.json
                cov_file = Path(tmpdir) / 'coverage.json'
                if cov_file.exists():
                    with open(cov_file) as f:
                        cov_data = json.load(f)
                    
                    totals = cov_data.get('totals', {})
                    metrics["coverage_percent"] = totals.get('percent_covered', 0.0)
                    
                    files_cov = cov_data.get('files', {})
                    metrics["covered_files"] = sum(1 for f in files_cov.values() 
                                                  if f.get('summary', {}).get('percent_covered', 0) > 0)
                    metrics["uncovered_files"] = sum(1 for f in files_cov.values() 
                                                    if f.get('summary', {}).get('percent_covered', 0) == 0)
                    
                    # Per-file coverage
                    file_coverage = {}
                    for f, data in files_cov.items():
                        file_coverage[f] = data.get('summary', {}).get('percent_covered', 0)
                    metrics["file_coverage"] = file_coverage

        except Exception as e:
            metrics["coverage_error"] = str(e)

        return metrics

    def _run_mutation_testing(self, repo_path: str, file_contents: Dict[str, str]) -> Dict:
        """Run mutation testing with mutmut if available."""
        metrics = {"mutation_score": 0.0, "mutants_killed": 0, "mutants_survived": 0}

        try:
            # Check if mutmut is available
            result = subprocess.run(['python', '-m', 'mutmut', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return metrics

            with tempfile.TemporaryDirectory() as tmpdir:
                for rel_path, content in file_contents.items():
                    if rel_path.endswith('.py'):
                        full_path = Path(tmpdir) / rel_path
                        full_path.parent.mkdir(parents=True, exist_ok=True)
                        full_path.write_text(content)

                # Run mutmut (this can be slow, limit time)
                cmd = ['python', '-m', 'mutmut', 'run', '--paths-to-mutate=.', '--runner=pytest']
                result = subprocess.run(cmd, cwd=tmpdir, capture_output=True, text=True, timeout=300)

                # Parse results
                result_cmd = ['python', '-m', 'mutmut', 'results']
                res = subprocess.run(result_cmd, cwd=tmpdir, capture_output=True, text=True, timeout=30)
                
                # Parse output for mutation score
                for line in res.stdout.split('\n'):
                    if 'mutation score' in line.lower():
                        try:
                            score = float(line.split()[-1].replace('%', ''))
                            metrics["mutation_score"] = score
                        except Exception:
                            pass

        except Exception:
            pass

        return metrics

    def _check_test_quality(self, test_files: List[str], file_contents: Dict[str, str]) -> List[TestingFinding]:
        findings = []

        for file_path in test_files:
            content = file_contents.get(file_path, '')
            try:
                tree = ast.parse(content)
                
                # Check for test functions without assertions
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                        has_assert = False
                        for n in ast.walk(node):
                            if isinstance(n, ast.Call):
                                if (isinstance(n.func, ast.Attribute) and n.func.attr.startswith('assert')):
                                    has_assert = True
                                elif (isinstance(n.func, ast.Name) and n.func.id.startswith('assert')):
                                    has_assert = True
                        
                        if not has_assert:
                            findings.append(TestingFinding(
                                id=f"no_assert_{file_path}_{node.name}",
                                category="test_quality",
                                severity="medium",
                                title=f"Test without assertions: {node.name}",
                                description="Test function contains no assertions",
                                file_path=file_path,
                                line_start=node.lineno,
                                line_end=node.end_lineno or node.lineno,
                                metric_value=0,
                                threshold=1,
                                recommendation="Add assertions to verify behavior"
                            ))

                # Check for overly broad exception handling
                for node in ast.walk(tree):
                    if isinstance(node, ast.ExceptHandler):
                        if node.type is None:  # bare except:
                            findings.append(TestingFinding(
                                id=f"bare_except_{file_path}_{node.lineno}",
                                category="test_quality",
                                severity="low",
                                title="Bare except clause in test",
                                description="Test catches all exceptions without specification",
                                file_path=file_path,
                                line_start=node.lineno,
                                line_end=node.lineno,
                                metric_value=0,
                                threshold=0,
                                recommendation="Specify exception types to catch"
                            ))

            except Exception:
                pass

        return findings

    def _check_missing_tests(self, source_files: List[str], test_files: List[str], 
                            file_contents: Dict[str, str]) -> List[TestingFinding]:
        findings = []

        if not test_files and source_files:
            findings.append(TestingFinding(
                id="no_test_files",
                category="test_coverage",
                severity="high",
                title="No test files found",
                description=f"Repository has {len(source_files)} source files but no test files",
                file_path=None,
                line_start=None,
                line_end=None,
                metric_value=0,
                threshold=1,
                recommendation="Add unit tests for critical functionality"
            ))
            return findings

        # Check each source file has corresponding test
        tested_modules = set()
        for tf in test_files:
            content = file_contents.get(tf, '')
            # Simple import detection
            for line in content.split('\n'):
                if line.startswith('from ') or line.startswith('import '):
                    parts = line.split()
                    if len(parts) >= 2:
                        module = parts[1].split('.')[0]
                        tested_modules.add(module)

        for sf in source_files:
            module_name = Path(sf).stem
            if module_name not in tested_modules and not module_name.startswith('_'):
                findings.append(TestingFinding(
                    id=f"missing_test_{sf}",
                    category="test_coverage",
                    severity="medium",
                    title=f"No tests for module: {module_name}",
                    description=f"Source module {sf} appears untested",
                    file_path=sf,
                    line_start=1,
                    line_end=1,
                    metric_value=0,
                    threshold=1,
                    recommendation=f"Create test file for {module_name}"
                ))

        return findings

    def _calculate_score(self, findings: List[TestingFinding], metrics: Dict) -> float:
        score = 0.0

        # Base score for having tests
        if metrics.get("test_files_count", 0) > 0:
            score += 20

        # Coverage score (up to 40 points)
        coverage = metrics.get("coverage_percent", 0)
        if coverage >= 90:
            score += 40
        elif coverage >= 80:
            score += 35
        elif coverage >= 60:
            score += 25
        elif coverage >= 40:
            score += 15
        elif coverage > 0:
            score += 10

        # Test density (up to 20 points)
        test_ratio = metrics.get("test_to_source_ratio", 0)
        if test_ratio >= 1.0:
            score += 20
        elif test_ratio >= 0.5:
            score += 15
        elif test_ratio >= 0.25:
            score += 10

        # Assertion density (up to 10 points)
        assertions_per_test = metrics.get("assertions_per_test", 0)
        if assertions_per_test >= 3:
            score += 10
        elif assertions_per_test >= 2:
            score += 7
        elif assertions_per_test >= 1:
            score += 5

        # Mutation score (up to 10 points)
        mutation = metrics.get("mutation_score", 0)
        if mutation >= 80:
            score += 10
        elif mutation >= 60:
            score += 7
        elif mutation >= 40:
            score += 5
        elif mutation > 0:
            score += 3

        # Penalties for findings
        for f in findings:
            if f.severity == "high":
                score -= 10
            elif f.severity == "medium":
                score -= 5
            elif f.severity == "low":
                score -= 2

        return max(0, min(100, round(score, 1)))