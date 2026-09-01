"""
JavaScript/TypeScript Language Skill
"""
import json
import re
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, List
from dataclasses import dataclass
from collections import Counter

from pro.config.loader import get_config
from pro.cache.manager import AnalysisCache


@dataclass
class JSFinding:
    id: str
    category: str
    severity: str
    title: str
    description: str
    file_path: str
    line_start: int
    line_end: int
    column_start: int
    column_end: int
    code_snippet: str
    recommendation: str
    rule_id: str


class JavaScriptSkill:
    def __init__(self, cache: AnalysisCache = None):
        self.cache = cache
        self.config = get_config()

    def analyze(self, repo_path: str, file_contents: Dict[str, str]) -> Dict[str, Any]:
        config = self.config.analysis
        cache_key = "javascript_skill"

        if self.cache:
            cached = self.cache.get(repo_path, cache_key, config.__dict__, file_contents)
            if cached:
                return cached

        findings = []
        metrics = {}

        js_files = {k: v for k, v in file_contents.items() 
                   if k.endswith(('.js', '.jsx', '.mjs', '.cjs', '.ts', '.tsx'))}

        if not js_files:
            return {"findings": [], "metrics": {}, "score": 100.0, "file_count": 0}

        # Run ESLint if available
        eslint_findings = self._run_eslint(repo_path, js_files)
        findings.extend(eslint_findings)

        # Custom pattern detection
        custom_findings = self._run_custom_patterns(js_files)
        findings.extend(custom_findings)

        # Package.json analysis
        pkg_findings = self._analyze_package_json(file_contents)
        findings.extend(pkg_findings)

        # TypeScript analysis
        ts_findings = self._analyze_typescript(js_files)
        findings.extend(ts_findings)

        # Calculate metrics
        metrics = self._calculate_metrics(js_files, findings)
        
        # Calculate score
        score = self._calculate_score(findings, metrics)

        result = {
            "findings": [f.__dict__ for f in findings],
            "metrics": metrics,
            "score": score,
            "file_count": len(js_files),
            "lines_of_code": sum(len(c.split('\n')) for c in js_files.values())
        }

        if self.cache:
            self.cache.set(repo_path, cache_key, config.__dict__, file_contents, result)

        return result

    def _run_eslint(self, repo_path: str, js_files: Dict[str, str]) -> List[JSFinding]:
        findings = []
        
        # Check if eslint is available - use shorter timeout and handle missing npx
        try:
            result = subprocess.run(['npx', 'eslint', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return findings
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # eslint/npx not available or too slow, skip gracefully
            return findings

        with tempfile.TemporaryDirectory() as tmpdir:
            # Write JS/TS files
            for rel_path, content in js_files.items():
                full_path = os.path.join(tmpdir, rel_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w') as f:
                    f.write(content)

            # Run eslint with shorter timeout for CI
            try:
                result = subprocess.run([
                    'npx', 'eslint', '.', '--format', 'json',
                    '--ext', '.js,.jsx,.ts,.tsx,.mjs,.cjs'
                ], cwd=tmpdir, capture_output=True, text=True, timeout=30)
                
                if result.returncode in (0, 1):  # 0 = no issues, 1 = issues found
                    eslint_results = json.loads(result.stdout) if result.stdout else []
                    for file_result in eslint_results:
                        file_path = file_result.get('filePath', '').replace(tmpdir + os.sep, '')
                        for message in file_result.get('messages', []):
                            findings.append(JSFinding(
                                id=f"eslint_{message.get('ruleId', 'unknown')}_{file_path}_{message.get('line', 0)}",
                                category="javascript",
                                severity=self._map_eslint_severity(message.get('severity', 2)),
                                title=f"ESLint: {message.get('ruleId', 'unknown')}",
                                description=message.get('message', ''),
                                file_path=file_path,
                                line_start=message.get('line', 1),
                                line_end=message.get('endLine', message.get('line', 1)),
                                column_start=message.get('column', 1),
                                column_end=message.get('endColumn', message.get('column', 1)),
                                code_snippet="",
                                recommendation=message.get('message', ''),
                                rule_id=message.get('ruleId', 'eslint')
                            ))
            except Exception:
                pass

        return findings

    def _map_eslint_severity(self, severity: int) -> str:
        return {1: "low", 2: "high"}.get(severity, "medium")

    def _run_custom_patterns(self, js_files: Dict[str, str]) -> List[JSFinding]:
        findings = []
        
        patterns = [
            {
                "id": "eval-usage",
                "name": "Eval Usage",
                "pattern": re.compile(r'\beval\s*\('),
                "severity": "high",
                "message": "Use of eval() - code injection risk",
                "recommendation": "Use JSON.parse() or safe alternatives"
            },
            {
                "id": "innerHTML-assignment",
                "name": "innerHTML Assignment",
                "pattern": re.compile(r'\.innerHTML\s*='),
                "severity": "high",
                "message": "Direct innerHTML assignment - XSS risk",
                "recommendation": "Use textContent or sanitize HTML"
            },
            {
                "id": "document-write",
                "name": "document.write Usage",
                "pattern": re.compile(r'document\.write\s*\('),
                "severity": "medium",
                "message": "document.write() usage - blocks parsing",
                "recommendation": "Use DOM manipulation methods"
            },
            {
                "id": "console-log",
                "name": "Console.log in Production",
                "pattern": re.compile(r'console\.(log|debug|info|warn|error)\s*\('),
                "severity": "low",
                "message": "Console logging in production code",
                "recommendation": "Remove or use proper logging library"
            },
            {
                "id": "debugger-statement",
                "name": "Debugger Statement",
                "pattern": re.compile(r'\bdebugger\b'),
                "severity": "medium",
                "message": "Debugger statement in production code",
                "recommendation": "Remove debugger statements"
            },
            {
                "id": "hardcoded-secret-js",
                "name": "Hardcoded Secret",
                "pattern": re.compile(r'(api[_-]?key|secret|password|token|private[_-]?key)\s*[:=]\s*["\'][^"\']{8,}["\']', re.IGNORECASE),
                "severity": "high",
                "message": "Hardcoded secret detected",
                "recommendation": "Use environment variables or secret management"
            },
            {
                "id": "alert-usage",
                "name": "Alert Usage",
                "pattern": re.compile(r'\balert\s*\('),
                "severity": "low",
                "message": "Alert() usage - blocks UI",
                "recommendation": "Use proper UI notifications"
            },
            {
                "id": "with-statement",
                "name": "With Statement",
                "pattern": re.compile(r'\bwith\s*\('),
                "severity": "medium",
                "message": "With statement usage - deprecated",
                "recommendation": "Avoid with statement"
            },
        ]

        for file_path, content in js_files.items():
            lines = content.split('\n')
            for pattern_def in patterns:
                for match in pattern_def["pattern"].finditer(content):
                    line_num = content[:match.start()].count('\n') + 1
                    line_content = lines[line_num - 1] if line_num <= len(lines) else ''
                    
                    findings.append(JSFinding(
                        id=f"js_{pattern_def['id']}_{file_path}_{line_num}",
                        category="javascript",
                        severity=pattern_def["severity"],
                        title=pattern_def["name"],
                        description=pattern_def["message"],
                        file_path=file_path,
                        line_start=line_num,
                        line_end=line_num,
                        column_start=match.start() - content.rfind('\n', 0, match.start()),
                        column_end=match.end() - content.rfind('\n', 0, match.start()),
                        code_snippet=line_content.strip(),
                        recommendation=pattern_def["recommendation"],
                        rule_id=pattern_def["id"]
                    ))

        return findings

    def _analyze_package_json(self, file_contents: Dict[str, str]) -> List[JSFinding]:
        findings = []
        
        for file_path, content in file_contents.items():
            if Path(file_path).name == 'package.json':
                try:
                    pkg = json.loads(content)
                    
                    # Check for known vulnerable patterns
                    deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
                    
                    # Check for unpinned versions
                    for name, version in deps.items():
                        if version in ('*', 'latest', 'next'):
                            findings.append(JSFinding(
                                id=f"unpinned_{name}",
                                category="dependencies",
                                severity="medium",
                                title=f"Unpinned dependency: {name}",
                                description=f"Dependency {name} uses unpinned version '{version}'",
                                file_path=file_path,
                                line_start=1,
                                line_end=1,
                                column_start=1,
                                column_end=1,
                                code_snippet=f'"{name}": "{version}"',
                                recommendation=f"Pin {name} to a specific version"
                            ))
                        
                        # Check for known vulnerable packages (simplified)
                        known_vulnerable = {
                            'event-stream': '3.3.6',
                            'flatmap-stream': '0.1.1',
                            'lodash': '<4.17.21',
                            'axios': '<0.21.1',
}
                        for vuln_pkg, vuln_ver in known_vulnerable.items():
                            if vuln_pkg in deps:
                                findings.append(JSFinding(
                                    id=f"vulnerable_{vuln_pkg}",
                                    category="security",
                                    severity="high",
                                    title=f"Known vulnerable package: {vuln_pkg}",
                                    description=f"Package {vuln_pkg}@{deps[vuln_pkg]} has known vulnerabilities",
                                    file_path=file_path,
                                    line_start=1,
                                    line_end=1,
                                    column_start=1,
                                    column_end=1,
                                    code_snippet=f'"{vuln_pkg}": "{deps[vuln_pkg]}"',
                                    recommendation=f"Update {vuln_pkg} to a secure version",
                                    rule_id="vulnerable_package"
                                ))
                    
                    # Check for missing security fields
                    if not pkg.get('license'):
                        findings.append(JSFinding(
                            id="missing_license",
                            category="license",
                            severity="low",
                            title="Missing license field",
                            description="package.json missing license field",
                            file_path=file_path,
                            line_start=1,
                            line_end=1,
                            column_start=1,
                            column_end=1,
                            code_snippet="",
                            recommendation="Add SPDX license identifier",
                            rule_id="missing_license"
                        ))
                    
                    # Check for missing repository field
                    if not pkg.get('repository'):
                        findings.append(JSFinding(
                            id="missing_repository",
                            category="metadata",
                            severity="low",
                            title="Missing repository field",
                            description="package.json missing repository field",
                            file_path=file_path,
                            line_start=1,
                            line_end=1,
                            column_start=1,
                            column_end=1,
                            code_snippet="",
                            recommendation="Add repository URL for discoverability",
                            rule_id="missing_repository"
                        ))

                except json.JSONDecodeError:
                    findings.append(JSFinding(
                        id="invalid_package_json",
                        category="syntax",
                        severity="high",
                        title="Invalid package.json",
                        description="package.json contains invalid JSON",
                        file_path=file_path,
                        line_start=1,
                        line_end=1,
                        column_start=1,
                        column_end=1,
                        code_snippet="",
                        recommendation="Fix JSON syntax errors",
                        rule_id="invalid_package_json"
                    ))

        return findings

    def _analyze_typescript(self, js_files: Dict[str, str]) -> List[JSFinding]:
        findings = []
        
        ts_files = {k: v for k, v in js_files.items() if k.endswith(('.ts', '.tsx'))}
        
        if not ts_files:
            return findings

        for file_path, content in ts_files.items():
            lines = content.split('\n')
            
            # Check for any type usage
            any_count = len(re.findall(r'\bany\b', content))
            if any_count > 5:
                findings.append(JSFinding(
                    id=f"excessive_any_{file_path}",
                    category="typescript",
                    severity="medium",
                    title=f"Excessive 'any' usage ({any_count} occurrences)",
                    description="Excessive use of 'any' type reduces type safety",
                    file_path=file_path,
                    line_start=1,
                    line_end=len(lines),
                    column_start=1,
                    column_end=1,
                    code_snippet="",
                    recommendation="Replace 'any' with specific types",
                    rule_id="excessive_any"
                ))

            # Check for @ts-ignore
            ts_ignore_count = len(re.findall(r'@ts-ignore', content))
            if ts_ignore_count > 3:
                findings.append(JSFinding(
                    id=f"excessive_ts_ignore_{file_path}",
                    category="typescript",
                    severity="low",
                    title=f"Excessive @ts-ignore usage ({ts_ignore_count})",
                    description="Excessive @ts-ignore suppresses type checking",
                    file_path=file_path,
                    line_start=1,
                    line_end=len(lines),
                    column_start=1,
                    column_end=1,
                    code_snippet="",
                    recommendation="Fix underlying type errors instead of suppressing",
                    rule_id="excessive_ts_ignore"
                ))

            # Check for non-null assertion (!) overuse
            non_null_count = len(re.findall(r'!\s*[.;,)]', content))
            if non_null_count > 10:
                findings.append(JSFinding(
                    id=f"excessive_non_null_{file_path}",
                    category="typescript",
                    severity="low",
                    title=f"Excessive non-null assertions ({non_null_count})",
                    description="Frequent non-null assertions may hide null issues",
                    file_path=file_path,
                    line_start=1,
                    line_end=len(lines),
                    column_start=1,
                    column_end=1,
                    code_snippet="",
                    recommendation="Add proper null checks",
                    rule_id="excessive_non_null"
                ))

        return findings

    def _calculate_metrics(self, js_files: Dict[str, str], findings: List[JSFinding]) -> Dict[str, Any]:
        total_lines = sum(len(c.split('\n')) for c in js_files.values())
        total_files = len(js_files)
        
        severity_counts = Counter(f.severity for f in findings)
        category_counts = Counter(f.category for f in findings)
        
        ts_files = {k: v for k, v in js_files.items() if k.endswith(('.ts', '.tsx'))}
        js_only_files = {k: v for k, v in js_files.items() if k.endswith(('.js', '.jsx', '.mjs', '.cjs'))}
        
        return {
            "total_files": total_files,
            "javascript_files": len(js_only_files),
            "typescript_files": len(ts_files),
            "total_lines": total_lines,
            "total_findings": len(findings),
            "critical_findings": severity_counts.get("critical", 0),
            "high_findings": severity_counts.get("high", 0),
            "medium_findings": severity_counts.get("medium", 0),
            "low_findings": severity_counts.get("low", 0),
            "findings_by_category": dict(category_counts),
            "avg_lines_per_file": total_lines / max(total_files, 1)
        }

    def _calculate_score(self, findings: List[JSFinding], metrics: Dict[str, Any]) -> float:
        score = 100.0
        
        severity_penalties = {
            "critical": 20,
            "high": 10,
            "medium": 5,
            "low": 1
        }
        
        for f in findings:
            score -= severity_penalties.get(f.severity, 0)
        
        # Bonus for TypeScript usage
        if metrics.get("typescript_files", 0) > 0:
            score += 5
        
        return max(0, min(100, round(score, 1)))