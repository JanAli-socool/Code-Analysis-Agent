"""
Enhanced Dependencies Skill with license compliance, vulnerability scanning, and SBOM generation.
"""
import json
import subprocess
import re
import os
import tempfile
import hashlib
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
from urllib import request, parse
import urllib.error
from functools import lru_cache

from pro.config.loader import get_config
from pro.cache.manager import AnalysisCache


# Module-level cache for pip outdated results
_pip_outdated_cache = {}
_pip_outdated_cache_time = 0
PIP_OUTDATED_CACHE_TTL = 3600  # 1 hour

@lru_cache(maxsize=1)
def _get_pip_outdated_cached() -> List[Dict]:
    """Get pip outdated packages with caching."""
    global _pip_outdated_cache, _pip_outdated_cache_time
    
    current_time = time.time()
    if current_time - _pip_outdated_cache_time < PIP_OUTDATED_CACHE_TTL and _pip_outdated_cache:
        return _pip_outdated_cache
    
    try:
        result = subprocess.run(
            ['python', '-m', 'pip', 'list', '--outdated', '--format=json'],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            _pip_outdated_cache = json.loads(result.stdout)
            _pip_outdated_cache_time = current_time
            return _pip_outdated_cache
    except Exception:
        pass
    
    return []

def _clear_pip_outdated_cache():
    """Clear the pip outdated cache (for testing)."""
    global _pip_outdated_cache, _pip_outdated_cache_time
    _pip_outdated_cache = {}
    _pip_outdated_cache_time = 0


def _check_outdated(deps: List[Dict], repo_path: str) -> List[Dict]:
    outdated = []
    if not deps:
        return outdated

    pip_outdated = _get_pip_outdated_cached()
    if not pip_outdated:
        return outdated

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
    
    return outdated


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
            outdated = _check_outdated(deps, repo_path)
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

        if config.get('check_supply_chain', True):
            supply_chain_issues = self._check_supply_chain(deps)
            metrics["supply_chain_issues_count"] = len(supply_chain_issues)
            for issue in supply_chain_issues:
                findings.append(DependencyFinding(
                    id=f"supply_chain_{issue['package']}_{issue['id']}",
                    category="supply_chain",
                    severity=issue['severity'].lower(),
                    title=f"Supply chain issue in {issue['package']}: {issue['id']}",
                    description=issue['description'],
                    file_path=issue.get('source_file'),
                    line_start=None,
                    line_end=None,
                    metric_value=1,
                    threshold=0,
                    recommendation=issue.get('recommendation', 'Review and mitigate supply chain risk')
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
        try:
            import tomllib
            data = tomllib.loads(content)
            
            if 'project' in data:
                for dep in data['project'].get('dependencies', []):
                    deps.append(self._parse_req_line(dep))
                for extra_name, extra_deps in data['project'].get('optional-dependencies', {}).items():
                    for dep in extra_deps:
                        d = self._parse_req_line(dep)
                        d['extras'] = [extra_name]
                        deps.append(d)
            
            if 'tool' in data and 'poetry' in data['tool']:
                poetry = data['tool']['poetry']
                for name, spec in poetry.get('dependencies', {}).items():
                    if name != 'python':
                        deps.append(self._parse_poetry_dep(name, spec))
                for group_name, group_deps in poetry.get('group', {}).items():
                    for name, spec in group_deps.get('dependencies', {}).items():
                        d = self._parse_poetry_dep(name, spec)
                        d['extras'] = [group_name]
                        deps.append(d)
        except Exception:
            pass
        return deps

    def _parse_req_line(self, line: str) -> Dict[str, Any]:
        import re
        match = re.match(r'^([a-zA-Z0-9_\-\.]+)([=<>!~]+.*)?', line.strip())
        if match:
            name = match.group(1).lower()
            version = match.group(2).lstrip('=<>!~') if match.group(2) else 'unknown'
        else:
            name = line.strip().lower()
            version = 'unknown'
        return {
            'name': name,
            'version': version,
            'type': 'pypi',
            'purl': f"pkg:pypi/{name}@{version}"
        }

    def _parse_poetry_dep(self, name: str, spec: Any) -> Dict[str, Any]:
        if isinstance(spec, str):
            version = spec
        elif isinstance(spec, dict):
            version = spec.get('version', 'unknown')
        else:
            version = 'unknown'
        return {
            'name': name.lower(),
            'version': version.lstrip('^~>=<'),
            'type': 'pypi',
            'purl': f"pkg:pypi/{name.lower()}@{version.lstrip('^~>=<')}"
        }

    def _parse_poetry_lock(self, content: str) -> List[Dict]:
        deps = []
        try:
            data = json.loads(content)
            for pkg in data.get('package', []):
                deps.append({
                    'name': pkg['name'].lower(),
                    'version': pkg['version'],
                    'type': 'pypi',
                    'purl': f"pkg:pypi/{pkg['name'].lower()}@{pkg['version']}"
                })
        except Exception:
            pass
        return deps

    def _parse_pipfile(self, content: str) -> List[Dict]:
        deps = []
        try:
            import tomllib
            data = tomllib.loads(content)
            for section in ['packages', 'dev-packages']:
                for name, spec in data.get(section, {}).items():
                    if isinstance(spec, str):
                        version = spec
                    elif isinstance(spec, dict):
                        version = spec.get('version', 'unknown')
                    else:
                        version = 'unknown'
                    deps.append({
                        'name': name.lower(),
                        'version': version.lstrip('^~>=<') if isinstance(spec, str) else 'unknown',
                        'type': 'pypi',
                        'purl': f"pkg:pypi/{name.lower()}@{version.lstrip('^~>=<') if isinstance(spec, str) else 'unknown'}"
                    })
        except Exception:
            pass
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

    # ==================== Supply Chain Scanning ====================

    def _check_supply_chain(self, deps: List[Dict]) -> List[Dict]:
        """Check for dependency confusion and supply chain issues using multiple sources."""
        findings = []
        
        # Check each dependency against multiple sources
        for dep in deps:
            name = dep['name']
            
            # Check OSV (Open Source Vulnerabilities)
            osv_results = self._check_osv(name, dep.get('current', 'unknown'))
            for vuln in osv_results:
                vuln['package'] = name
                vuln['source'] = 'OSV'
            
            # Check OSS Index
            oss_results = self._check_oss_index(name)
            for vuln in oss_results:
                vuln['package'] = name
                vuln['source'] = 'OSS Index'
            
            # Check deps.dev
            deps_dev_results = self._check_deps_dev(name)
            for issue in deps_dev_results:
                issue['package'] = name
                issue['source'] = 'deps.dev'
            
            # Check for dependency confusion (typosquatting, etc.)
            confusion_results = self._check_dependency_confusion(name, deps)
            for issue in confusion_results:
                issue['package'] = name
                issue['source'] = 'Dependency Confusion Check'
            
            # Collect all findings
            all_findings = osv_results + oss_results + deps_dev_results + confusion_results
            for finding in all_findings:
                findings.append({
                    'package': name,
                    'id': finding.get('id', ''),
                    'severity': finding.get('severity', 'MEDIUM'),
                    'description': finding.get('description', ''),
                    'source': finding.get('source', ''),
                    'fixed_version': finding.get('fixed_version', ''),
                    'recommendation': finding.get('recommendation', '')
                })
        
        return findings

    def _check_osv(self, package: str, version: str) -> List[Dict]:
        """Check OSV (Open Source Vulnerabilities) database."""
        findings = []
        try:
            url = f"https://api.osv.dev/v1/query"
            payload = {
                "package": {"name": package, "ecosystem": "PyPI"},
                "version": version
            }
            
            data = json.dumps(payload).encode('utf-8')
            req = request.Request(
                "https://api.osv.dev/v1/query",
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            
            with request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                for vuln in data.get('vulns', []):
                    findings.append({
                        'id': vuln.get('id', ''),
                        'severity': self._map_osv_severity(vuln),
                        'description': vuln.get('details', vuln.get('summary', '')),
                        'fixed_version': self._extract_fixed_version(vuln),
                        'recommendation': f"Update to a non-vulnerable version. See {vuln.get('id', '')} for details."
                    })
        except Exception:
            pass
        return findings

    def _check_oss_index(self, package: str) -> List[Dict]:
        """Check OSS Index (Sonatype) for vulnerabilities."""
        findings = []
        try:
            url = "https://ossindex.sonatype.org/api/v3/component-report"
            payload = [{"coordinates": f"pkg:pypi/{package}"}]
            
            data = json.dumps(payload).encode('utf-8')
            req = request.Request(
                url,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            
            with request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                for item in data:
                    for vuln in item.get('vulnerabilities', []):
                        findings.append({
                            'id': vuln.get('id', ''),
                            'severity': vuln.get('cvssScore', '').upper() if vuln.get('cvssScore') else 'MEDIUM',
                            'description': vuln.get('title', ''),
                            'fixed_version': '',
                            'recommendation': f"See {vuln.get('id', '')} for details. Consider upgrading."
                        })
        except Exception:
            pass
        return findings

    def _check_deps_dev(self, package: str) -> List[Dict]:
        """Check deps.dev for package information and issues."""
        findings = []
        try:
            url = f"https://api.deps.dev/v3alpha/systems/pypi/packages/{package}"
            req = request.Request(url)
            
            with request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                for vuln in data.get('vulnerabilities', []):
                    findings.append({
                        'id': vuln.get('id', ''),
                        'severity': vuln.get('severity', 'MEDIUM'),
                        'description': vuln.get('description', ''),
                        'fixed_version': vuln.get('fixedVersion', ''),
                        'recommendation': f"Update to version {vuln.get('fixedVersion', 'latest')} or later."
                    })
                
                if data.get('isMalicious', False):
                    findings.append({
                        'id': 'MALICIOUS_PACKAGE',
                        'severity': 'CRITICAL',
                        'description': f'Package {package} flagged as potentially malicious on deps.dev',
                        'fixed_version': '',
                        'recommendation': 'Immediately remove this package and investigate.'
                    })
        except Exception:
            pass
        return findings

    def _check_dependency_confusion(self, package: str, all_deps: List[Dict]) -> List[Dict]:
        """Check for potential dependency confusion attacks (typosquatting, etc.)."""
        findings = []
        
        typo_patterns = [
            package.replace('-', '_'),
            package.replace('_', '-'),
            package + 's',
            package[:-1] if len(package) > 3 else package,
            package + '2',
            package + '-utils',
            package + '-tools',
            package + '-lib',
            package + '-client',
        ]
        
        dep_names = {d['name'].lower() for d in all_deps}
        for typo in typo_patterns:
            if typo.lower() in dep_names and typo.lower() != package.lower():
                findings.append({
                    'id': 'TYPOSQUATTING_DETECTED',
                    'severity': 'HIGH',
                    'description': f'Potential typosquatting detected: {typo} resembles {package}',
                    'fixed_version': '',
                    'recommendation': f'Review dependency {typo} - it may be a typosquatting attempt targeting {package}.'
                })
        
        return findings

    def _map_osv_severity(self, vuln: Dict) -> str:
        """Map OSV severity to our severity levels."""
        for severity in vuln.get('severity', []):
            if severity.get('type') == 'CVSS_V3':
                score = severity.get('score', '0')
                try:
                    score_val = float(score.split(':')[-1]) if ':' in score else float(score)
                    if score_val >= 9.0:
                        return 'CRITICAL'
                    elif score_val >= 7.0:
                        return 'HIGH'
                    elif score_val >= 4.0:
                        return 'MEDIUM'
                    else:
                        return 'LOW'
                except:
                    pass
        return 'MEDIUM'

    def _extract_fixed_version(self, vuln: Dict) -> str:
        """Extract fixed version from OSV vulnerability data."""
        for affected in vuln.get('affected', []):
            for range_info in affected.get('ranges', []):
                for event in range_info.get('events', []):
                    if 'fixed' in event:
                        return event['fixed']
        return ''

    def _calculate_score(self, findings: List[DependencyFinding], metrics: Dict) -> float:
        """Calculate overall score based on findings and metrics."""
        score = 100.0

        score -= metrics.get("vulnerabilities_count", 0) * 20
        score -= metrics.get("outdated_count", 0) * 2
        score -= metrics.get("license_issues_count", 0) * 5
        score -= metrics.get("supply_chain_issues_count", 0) * 10

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