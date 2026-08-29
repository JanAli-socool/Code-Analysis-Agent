"""
Dependencies Analysis Skill - Outdated packages, vulnerabilities, license issues
"""
import json
import subprocess
import os
import re
from typing import List, Dict
from advanced.skills.base import BaseSkill
from advanced.models import AgentContext, CategoryScore, AnalysisCategory, Finding, Severity, MetricResult


class DependenciesSkill(BaseSkill):
    def __init__(self):
        super().__init__("Dependencies Analysis", AnalysisCategory.DEPENDENCIES, weight=1.0)

    def analyze(self, context: AgentContext) -> CategoryScore:
        findings = []
        metrics = []

        req_files = []
        for file_path in context.file_contents.keys():
            if any(x in file_path.lower() for x in ['requirements', 'setup.py', 'pyproject.toml', 'pipfile', 'poetry.lock']):
                req_files.append(file_path)

        all_deps = {}
        outdated = []
        vulnerabilities = []

        for req_file in req_files:
            content = context.file_contents[req_file]
            deps = self._parse_requirements(content, req_file)
            all_deps.update(deps)

        if all_deps:
            try:
                result = subprocess.run(
                    ['pip', 'list', '--outdated', '--format=json'],
                    capture_output=True, text=True, timeout=30
                )
                outdated = json.loads(result.stdout) if result.stdout else []
            except Exception:
                pass

            try:
                result = subprocess.run(
                    ['pip', 'audit', '--format=json'],
                    capture_output=True, text=True, timeout=60
                )
                audit_result = json.loads(result.stdout) if result.stdout else {"vulnerabilities": []}
                vulnerabilities = audit_result.get("vulnerabilities", [])
            except Exception:
                pass

        for dep in outdated:
            findings.append(self._create_finding(
                finding_id=f"outdated_{dep.get('name', '')}",
                severity=Severity.MEDIUM if self._is_major_version_behind(dep) else Severity.LOW,
                title=f"Outdated dependency: {dep.get('name')}",
                description=f"Current: {dep.get('version')}, Latest: {dep.get('latest_version')}",
                evidence=f"Installed: {dep.get('version')}, Latest: {dep.get('latest_version')}",
                recommendation=f"Update {dep.get('name')} to latest version"
            ))

        for vuln in vulnerabilities:
            findings.append(self._create_finding(
                finding_id=f"vuln_{vuln.get('name', '')}_{vuln.get('id', '')}",
                severity=Severity.HIGH,
                title=f"Vulnerability in {vuln.get('name')}: {vuln.get('id')}",
                description=vuln.get('description', 'Security vulnerability detected'),
                evidence=f"Fixed in: {vuln.get('fixed_versions', 'Unknown')}",
                recommendation=f"Upgrade {vuln.get('name')} to a patched version"
            ))

        license_issues = self._check_licenses(all_deps)
        for issue in license_issues:
            findings.append(self._create_finding(
                finding_id=f"license_{issue['package']}",
                severity=Severity.MEDIUM,
                title=f"License concern: {issue['package']}",
                description=f"Package uses {issue['license']} license which may have restrictions",
                evidence=f"License: {issue['license']}",
                recommendation="Review license compatibility with your use case"
            ))

        metrics.extend([
            self._create_metric("total_dependencies", float(len(all_deps))),
            self._create_metric("outdated_count", float(len(outdated)), threshold=5),
            self._create_metric("vulnerabilities_count", float(len(vulnerabilities)), threshold=0),
            self._create_metric("license_issues_count", float(len(license_issues)), threshold=0),
            self._create_metric("requirements_files", float(len(req_files)))
        ])

        score = 100
        score -= len(vulnerabilities) * 20
        score -= len(outdated) * 2
        score -= len(license_issues) * 5
        score = max(0, min(100, score))

        return CategoryScore(
            category=self.category,
            score=score,
            weight=self.weight,
            findings=findings,
            metrics=metrics
        )

    def _parse_requirements(self, content: str, file_path: str) -> Dict[str, str]:
        deps = {}
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                match = re.match(r'^([a-zA-Z0-9_-]+)', line)
                if match:
                    deps[match.group(1).lower()] = file_path
        return deps

    def _is_major_version_behind(self, dep: dict) -> bool:
        try:
            current = dep.get('version', '0.0.0').split('.')[0]
            latest = dep.get('latest_version', '0.0.0').split('.')[0]
            return int(latest) > int(current)
        except Exception:
            return False

    def _check_licenses(self, deps: Dict[str, str]) -> List[Dict]:
        problematic = ['gpl', 'agpl', 'lgpl']
        issues = []
        for dep in deps:
            try:
                result = subprocess.run(
                    ['pip', 'show', dep],
                    capture_output=True, text=True, timeout=10
                )
                for line in result.stdout.split('\n'):
                    if line.startswith('License:'):
                        license_str = line.split(':', 1)[1].strip().lower()
                        if any(p in license_str for p in problematic):
                            issues.append({'package': dep, 'license': license_str})
            except Exception:
                pass
        return issues