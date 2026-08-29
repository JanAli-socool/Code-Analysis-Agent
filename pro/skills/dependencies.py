"""
Enhanced Dependencies Skill with license compliance, vulnerability scanning, and SBOM generation.
"""
import json
import subprocess
import re
import os
import tempfile
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from pro.config.loader import get_config
from pro.cache.manager import AnalysisCache


@dataclass
class DependencyFinding:
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


class DependenciesSkill:
    def __init__(self, cache: AnalysisCache = None):
        self.cache = cache
        self.config = get_config().analysis.dependencies

    def analyze(self, repo_path: str, file_contents: Dict[str, str]) -> Dict[str, Any]:
        config = self.config
        cache_key = "dependencies_skill"

        if self.cache:
            cached = self.cache.get(repo_path, cache_key, config, file_contents)
            if cached:
                return cached

        findings = []
        metrics = {}

        deps = self._parse_all_dependencies(file_contents)
        metrics["total_dependencies"] = len(deps)

        if config.get('check_outdated', True):
            outdated = self._check_outdated(deps, repo_path)
            metrics["outdated_count"] = len(outdated)
            for dep in outdated:
                findings.append(DependencyFinding(
                    id=f"outdated_{dep['name']}",
                    category="outdated_dependency",
                    severity="medium" if dep.get('major_behind', False) else "low",
                    title=f"Outdated dependency: {dep['name']}",
                    description=f"Current: {dep['current']}, Latest: {dep['latest']}",
                    file_path=dep.get('source_file'),
                    line_start=None,
                    line_end=None,
                    metric_value=1,
                    threshold=0,
                    recommendation=f"Update {dep['name']} to {dep['latest']}"
                ))

        if config.get('check_vulnerabilities', True):
            vulns = self._check_vulnerabilities(deps)
            metrics["vulnerabilities_count"] = len(vulns)
            for vuln in vulns:
                findings.append(DependencyFinding(
                    id=f"vuln_{vuln['name']}_{vuln['id']}",
                    category="vulnerability",
                    severity=vuln['severity'].lower(),
                    title=f"Vulnerability in {vuln['name']}: {vuln['id']}",
                    description=vuln.get('description', 'Security vulnerability'),
                    file_path=vuln.get('source_file'),
                    line_start=None,
                    line_end=None,
                    metric_value=1,
                    threshold=0,
                    recommendation=f"Upgrade {vuln['name']} to >= {vuln.get('fixed_version', 'latest')}"
                ))

        if config.get('check_licenses', True):
            license_issues = self._check_licenses(deps, config)
            metrics["license_issues_count"] = len(license_issues)
            for issue in license_issues:
                findings.append(DependencyFinding(
                    id=f"license_{issue['package']}",
                    category="license_compliance",
                    severity="medium",
                    title=f"License concern: {issue['package']}",
                    description=f"Package uses {issue['license']} license which may have restrictions",
                    file_path=issue.get('source_file'),
                    line_start=None,
                    line_end=None,
                    metric_value=1,
                    threshold=0,
                    recommendation="Review license compatibility with your use case"
                ))

        pinned = self._check_pinned_versions(deps)
        metrics["pinned_dependencies"] = pinned
        metrics["unpinned_dependencies"] = len(deps) - pinned

        sbom = self._generate_sbom(deps)
        metrics["sbom"] = sbom

        result = {
            "findings": [f.__dict__ for f in findings],
            "metrics": [{"name": k, "value": v} for k, v in metrics.items()],
            "score": self._calculate_score(findings, metrics)
        }

        if self.cache:
            self.cache.set(repo_path, cache_key, config, file_contents, result)

        return result

    def _parse_all_dependencies(self, file_contents: Dict[str, str]) -> List[Dict]:
        deps = []
        for file_path, content in file_contents.items():
            name = Path(file_path).name.lower()
            if any(x in name for x in ['requirements', 'setup.py', 'pyproject.toml', 'pipfile', 'poetry.lock']):
                file_deps = self._parse_dependency_file(file_path, content)
                for dep in file_deps:
                    dep['source_file'] = file_path
                    deps.append(dep)
        return deps

    def _parse_dependency_file(self, file_path: str, content: str) -> List[Dict]:
        deps = []
        name = Path(file_path).name.lower()

        if name == 'pyproject.toml':
            deps.extend(self._parse_pyproject(content))
        elif name == 'setup.py':
            deps.extend(self._parse_setup_py(content))
        elif name == 'poetry.lock':
            deps.extend(self._parse_poetry_lock(content))
        elif 'requirements' in name or name == 'pipfile':
            deps.extend(self._parse_requirements(content))

        return deps

    def _parse_requirements(self, content: str) -> List[Dict]:
        deps = []
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                match = re.match(r'^([a-zA-Z0-9_\-\.]+)([=<>!~]+.*)?', line)
                if match:
                    deps.append({
                        'name': match.group(1).lower(),
                        'specifier': match.group(2) or '',
                        'current': match.group(2).lstrip('=<>!~') if match.group(2) else 'unknown'
                    })
        return deps

    def _parse_pyproject(self, content: str) -> List[Dict]:
        deps = []
        in_deps = False
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('[') and 'dependencies' in line.lower():
                in_deps = True
                continue
            elif line.startswith('['):
                in_deps = False
                continue
            
            if in_deps and line and not line.startswith('#'):
                match = re.match(r'^([a-zA-Z0-9_\-\.]+)\s*[=<>!~]', line)
                if match:
                    deps.append({
                        'name': match.group(1).lower(),
                        'specifier': line[match.end():].strip(),
                        'current': 'from_pyproject'
                    })
        return deps

    def _parse_setup_py(self, content: str) -> List[Dict]:
        deps = []
        match = re.search(r'install_requires\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if match:
            reqs = match.group(1)
            for line in reqs.split(','):
                line = line.strip().strip('\'"')
                if line:
                    m = re.match(r'^([a-zA-Z0-9_\-\.]+)([=<>!~]+.*)?', line)
                    if m:
                        deps.append({
                            'name': m.group(1).lower(),
                            'specifier': m.group(2) or '',
                            'current': m.group(2).lstrip('=<>!~') if m.group(2) else 'unknown'
                        })
        return deps

    def _parse_poetry_lock(self, content: str) -> List[Dict]:
        deps = []
        try:
            data = json.loads(content) if content.startswith('{') else None
            if data and 'package' in data:
                for pkg in data['package']:
                    deps.append({
                        'name': pkg.get('name', '').lower(),
                        'version': pkg.get('version', ''),
                        'current': pkg.get('version', 'unknown')
                    })
        except Exception:
            pass
        return deps

    def _check_outdated(self, deps: List[Dict], repo_path: str) -> List[Dict]:
        outdated = []
        if not deps:
            return outdated

        try:
            result = subprocess.run(
                ['python', '-m', 'pip', 'list', '--outdated', '--format=json'],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                pip_outdated = json.loads(result.stdout)
                dep_names = {d['name'] for d in deps}
                
                for pkg in pip_outdated:
                    if pkg['name'].lower() in dep_names:
                        current_major = pkg['version'].split('.')[0]
                        latest_major = pkg['latest_version'].split('.')[0]
                        outdated.append({
                            'name': pkg['name'],
                            'current': pkg['version'],
                            'latest': pkg['latest_version'],
                            'major_behind': int(latest_major) > int(current_major)
                        })
        except Exception:
            pass

        return outdated

    def _check_vulnerabilities(self, deps: List[Dict]) -> List[Dict]:
        vulns = []
        if not deps:
            return vulns

        try:
            req_content = '\n'.join(f"{d['name']}{d.get('specifier', '')}" for d in deps)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(req_content)
                req_file = f.name

            try:
                result = subprocess.run(
                    ['python', '-m', 'pip_audit', '-r', req_file, '--format=json'],
                    capture_output=True, text=True, timeout=120
                )
                if result.stdout:
                    audit_data = json.loads(result.stdout)
                    for vuln in audit_data.get('vulnerabilities', []):
                        vulns.append({
                            'name': vuln.get('package', ''),
                            'id': vuln.get('id', ''),
                            'severity': vuln.get('severity', 'MEDIUM'),
                            'description': vuln.get('description', ''),
                            'fixed_version': vuln.get('fixed_versions', [''])[0] if vuln.get('fixed_versions') else ''
                        })
            finally:
                os.unlink(req_file)
        except Exception:
            pass

        return vulns

    def _check_licenses(self, deps: List[Dict], config: Dict) -> List[Dict]:
        issues = []
        blocked = set(config.get('blocked_licenses', []))
        allowed = set(config.get('allowed_licenses', []))

        for dep in deps:
            try:
                result = subprocess.run(
                    ['python', '-m', 'pip', 'show', dep['name']],
                    capture_output=True, text=True, timeout=10
                )
                for line in result.stdout.split('\n'):
                    if line.startswith('License:'):
                        license_str = line.split(':', 1)[1].strip()
                        for blocked_lic in blocked:
                            if blocked_lic.lower() in license_str.lower():
                                issues.append({
                                    'package': dep['name'],
                                    'license': license_str,
                                    'source_file': dep.get('source_file')
                                })
                                break
                        if allowed and not any(a.lower() in license_str.lower() for a in allowed):
                            issues.append({
                                'package': dep['name'],
                                'license': license_str,
                                'source_file': dep.get('source_file')
                            })
                        break
            except Exception:
                pass

        return issues

    def _check_pinned_versions(self, deps: List[Dict]) -> int:
        pinned = 0
        for dep in deps:
            specifier = dep.get('specifier', '')
            if '==' in specifier or '===' in specifier:
                pinned += 1
        return pinned

    def _generate_sbom(self, deps: List[Dict]) -> List[Dict]:
        sbom = []
        for dep in deps:
            sbom.append({
                "name": dep['name'],
                "version": dep.get('current', dep.get('version', 'unknown')),
                "specifier": dep.get('specifier', ''),
                "source_file": dep.get('source_file', '')
            })
        return sbom

    def _calculate_score(self, findings: List[DependencyFinding], metrics: Dict) -> float:
        score = 100.0

        score -= metrics.get("vulnerabilities_count", 0) * 20
        score -= metrics.get("outdated_count", 0) * 2
        score -= metrics.get("license_issues_count", 0) * 5

        total = metrics.get("total_dependencies", 1)
        pinned = metrics.get("pinned_dependencies", 0)
        if total > 0 and pinned / total >= 0.8:
            score += 5

        for f in findings:
            if f.severity == "critical":
                score -= 15
            elif f.severity == "high":
                score -= 10
            elif f.severity == "medium":
                score -= 5
            elif f.severity == "low":
                score -= 2

        return max(0, min(100, round(score, 1)))