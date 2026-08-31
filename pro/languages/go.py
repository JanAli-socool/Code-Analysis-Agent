"""
Go Language Skill
"""
import re
import json
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass
from collections import Counter

from pro.config.loader import get_config
from pro.cache.manager import AnalysisCache


@dataclass
class GoFinding:
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


class GoSkill:
    def __init__(self, cache: AnalysisCache = None):
        self.cache = cache
        self.config = get_config()

    def analyze(self, repo_path: str, file_contents: Dict[str, str]) -> Dict[str, Any]:
        config = self.config.analysis
        cache_key = "go_skill"

        if self.cache:
            cached = self.cache.get(repo_path, cache_key, self.config.analysis.__dict__, file_contents)
            if cached:
                return cached

        findings = []
        go_files = {k: v for k, v in file_contents.items() if k.endswith('.go')}

        if not go_files:
            return {"findings": [], "metrics": {}, "score": 100.0, "file_count": 0}

        # Run go vet
        govet_findings = self._run_govet(repo_path, go_files)
        findings.extend(govet_findings)

        # Run staticcheck if available
        staticcheck_findings = self._run_staticcheck(repo_path, go_files)
        findings.extend(staticcheck_findings)

        # Run golint if available
        golint_findings = self._run_golint(repo_path, go_files)
        findings.extend(golint_findings)

        # Custom pattern detection
        custom_findings = self._run_custom_patterns(go_files)
        findings.extend(custom_findings)

        # Go module analysis
        mod_findings = self._analyze_go_mod(file_contents)
        findings.extend(mod_findings)

        # Calculate metrics
        metrics = self._calculate_metrics(go_files, findings)
        score = self._calculate_score(findings, metrics)

        result = {
            "findings": [f.__dict__ for f in findings],
            "metrics": metrics,
            "score": score,
            "file_count": len(go_files),
            "lines_of_code": sum(len(c.split('\n')) for c in go_files.values())
        }

        if self.cache:
            self.cache.set(repo_path, "go_skill", {}, file_contents, result)

        return result

    def _run_govet(self, repo_path: str, go_files: Dict[str, str]) -> List[Any]:
        findings = []
        
        try:
            # Check if go is available
            result = subprocess.run(['go', 'version'], capture_output=True, timeout=5)
            if result.returncode != 0:
                return findings
        except FileNotFoundError:
            return findings

        with tempfile.TemporaryDirectory() as tmpdir:
            # Write Go files
            for rel_path, content in go_files.items():
                full_path = os.path.join(tmpdir, rel_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w') as f:
                    f.write(content)

            # Create minimal go.mod if not exists
            go_mod = os.path.join(tmpdir, 'go.mod')
            if not os.path.exists(go_mod):
                with open(go_mod, 'w') as f:
                    f.write('module temp\n\ngo 1.21\n')

            try:
                result = subprocess.run(['go', 'vet', './...'], 
                                      cwd=tmpdir, capture_output=True, text=True, timeout=60)
                if result.returncode in (0, 1):
                    # Parse output
                    for line in result.stdout.split('\n') + result.stderr.split('\n'):
                        if line.strip() and ':' in line:
                            # Parse format: file:line:col: message
                            parts = line.split(':', 3)
                            if len(parts) >= 4:
                                file_path = parts[0]
                                line_num = int(parts[1]) if parts[1].isdigit() else 1
                                col_num = int(parts[2]) if parts[2].isdigit() else 1
                                message = parts[3].strip() if len(parts) > 3 else line
                                
                                from pro.languages.go import GoFinding
                                findings.append(GoFinding(
                                    id=f"govet_{file_path}_{line_num}",
                                    category="go",
                                    severity="medium",
                                    title="go vet finding",
                                    description=message,
                                    file_path=file_path,
                                    line_start=line_num,
                                    line_end=line_num,
                                    column_start=col_num,
                                    column_end=col_num + 1,
                                    code_snippet="",
                                    recommendation="Fix go vet issue",
                                    rule_id="govet"
                                ))
            except Exception:
                pass

        return findings

    def _run_staticcheck(self, repo_path: str, go_files: Dict[str, str]) -> List[Any]:
        # Similar to govet but for staticcheck
        return []

    def _run_golint(self, repo_path: str, go_files: Dict[str, str]) -> List[Any]:
        return []

    def _run_custom_patterns(self, go_files: Dict[str, str]) -> List[Any]:
        findings = []
        
        patterns = [
            {
                "id": "sql-injection",
                "name": "SQL Injection Risk",
                "pattern": re.compile(r'fmt\.Sprintf\s*\([^)]*%s[^)]*\)\s*\.\s*Query'),
                "severity": "high",
                "message": "Potential SQL injection via string formatting",
                "recommendation": "Use parameterized queries with database/sql"
            },
            {
                "id": "sql-concat",
                "name": "SQL String Concatenation",
                "pattern": re.compile(r'["\']SELECT.*\+.*["\']'),
                "severity": "high",
                "message": "SQL query built via string concatenation",
                "recommendation": "Use parameterized queries with placeholders"
            },
            {
                "id": "hardcoded-secret",
                "name": "Hardcoded Secret",
                "pattern": re.compile(r'(password|secret|apiKey|api_key|token|privateKey)\s*[:=]\s*["\'][^"\']{8,}["\']', re.IGNORECASE),
                "severity": "high",
                "message": "Hardcoded credential detected",
                "recommendation": "Use environment variables or secret management"
            },
            {
                "id": "weak-random",
                "name": "Weak Random",
                "pattern": re.compile(r'math/rand\.(Int|Float|Seed)'),
                "severity": "medium",
                "message": "math/rand is not cryptographically secure",
                "recommendation": "Use crypto/rand for security-sensitive operations"
            },
            {
                "id": "sql-injection-format",
                "name": "SQL Format String Injection",
                "pattern": re.compile(r'fmt\.Sprintf\s*\([^)]*%[^)]*\)\s*\.\s*(Query|Exec)'),
                "severity": "high",
                "message": "Potential SQL injection via fmt.Sprintf",
                "recommendation": "Use parameterized queries"
            },
            {
                "id": "path-traversal",
                "name": "Path Traversal",
                "pattern": re.compile(r'path\.Join\s*\([^)]*\.\./'),
                "severity": "high",
                "message": "Potential path traversal",
                "recommendation": "Use filepath.Clean and validate paths"
            },
            {
                "id": "insecure-temp",
                "name": "Insecure Temp File",
                "pattern": re.compile(r'ioutil\.TempFile'),
                "severity": "medium",
                "message": "ioutil.TempFile is deprecated and insecure",
                "recommendation": "Use os.CreateTemp with proper permissions"
            },
            {
                "id": "http-no-timeout",
                "name": "HTTP Client Without Timeout",
                "pattern": re.compile(r'http\.Client\s*\{\s*\}'),
                "severity": "medium",
                "message": "HTTP client without timeout",
                "recommendation": "Set Timeout on http.Client"
            },
            {
                "id": "tls-insecure-skip",
                "name": "TLS InsecureSkipVerify",
                "pattern": re.compile(r'InsecureSkipVerify\s*:\s*true'),
                "severity": "high",
                "message": "TLS certificate verification disabled",
                "recommendation": "Use proper TLS configuration or custom CA"
            },
            {
                "id": "defer-in-loop",
                "name": "Defer in Loop",
                "pattern": re.compile(r'for\s+[^}]*defer\s+'),
                "severity": "medium",
                "message": "Defer in loop - resources not released until function returns",
                "recommendation": "Extract defer to helper function or use closure"
            },
        ]

        findings = []
        for file_path, content in go_files.items():
            lines = content.split('\n')
            for pattern_def in patterns:
                for match in pattern_def["pattern"].finditer(content):
                    line_num = content[:match.start()].count('\n') + 1
                    line_content = lines[line_num - 1] if line_num <= len(lines) else ''
                    
                    findings.append(GoFinding(
                        id=f"go_{pattern_def['id']}_{file_path}_{line_num}",
                        category="go",
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

    def _analyze_go_mod(self, file_contents: Dict[str, str]) -> List[Any]:
        findings = []
        
        for file_path, content in file_contents.items():
            if Path(file_path).name == 'go.mod':
                # Check for replace directives to local paths
                if 'replace' in content:
                    findings.append({
                        "id": f"go_mod_replace_{file_path}",
                        "category": "dependencies",
                        "severity": "low",
                        "title": "Go module has replace directives",
                        "description": "go.mod contains replace directives",
                        "file_path": file_path,
                        "line_start": 1,
                        "line_end": 1,
                        "column_start": 1,
                        "column_end": 1,
                        "code_snippet": "",
                        "recommendation": "Ensure replace directives are intentional",
                        "rule_id": "go_mod_replace"
                    })
                
                # Check for replace to local paths
                if re.search(r'replace\s+\S+\s+=>\s*\./', content):
                    findings.append({
                        "id": f"go_mod_local_replace_{file_path}",
                        "category": "dependencies",
                        "severity": "medium",
                        "title": "Go module replaces with local path",
                        "description": "go.mod replaces module with local path",
                        "file_path": file_path,
                        "line_start": 1,
                        "line_end": 1,
                        "column_start": 1,
                        "column_end": 1,
                        "code_snippet": "",
                        "recommendation": "Use versioned dependencies instead of local replaces",
                        "rule_id": "go_mod_local_replace"
                    })

                # Check for indirect dependencies
                if '// indirect' in content:
                    findings.append({
                        "id": f"go_mod_indirect_{file_path}",
                        "category": "dependencies",
                        "severity": "low",
                        "title": "Indirect dependencies in go.mod",
                        "description": "go.mod contains indirect dependencies",
                        "file_path": file_path,
                        "line_start": 1,
                        "line_end": 1,
                        "column_start": 1,
                        "column_end": 1,
                        "code_snippet": "",
                        "recommendation": "Review indirect dependencies",
                        "rule_id": "go_mod_indirect"
                    })

        return findings

    def _calculate_metrics(self, go_files: Dict[str, str], findings: List[Any]) -> Dict[str, Any]:
        total_lines = sum(len(c.split('\n')) for c in go_files.values())
        total_files = len(go_files)
        
        severity_counts = Counter(f.severity for f in findings)
        category_counts = Counter(f.category for f in findings)
        
        # Go-specific metrics
        func_count = sum(len(re.findall(r'\bfunc\s+\w+', c)) for c in go_files.values())
        struct_count = sum(len(re.findall(r'\bstruct\s*{', c)) for c in go_files.values())
        interface_count = sum(len(re.findall(r'\binterface\s*{', c)) for c in go_files.values())
        goroutine_count = sum(len(re.findall(r'\bgo\s+\w', c)) for c in go_files.values())
        channel_count = sum(len(re.findall(r'make\s*\(\s*chan', c)) for c in go_files.values())
        
        return {
            "total_files": len(go_files),
            "total_lines": sum(len(c.split('\n')) for c in go_files.values()),
            "total_functions": func_count,
            "total_structs": struct_count,
            "total_interfaces": interface_count,
            "goroutines": goroutine_count,
            "channels": channel_count,
            "total_findings": len(findings),
            "critical_findings": Counter(f.severity for f in findings).get("critical", 0),
            "high_findings": Counter(f.severity for f in findings).get("high", 0),
            "medium_findings": Counter(f.severity for f in findings).get("medium", 0),
            "low_findings": Counter(f.severity for f in findings).get("low", 0),
            "findings_by_category": dict(category_counts),
            "avg_lines_per_file": total_lines / max(len(go_files), 1)
        }

    def _calculate_score(self, findings: List[Any], metrics: Dict[str, Any]) -> float:
        score = 100.0
        
        severity_penalties = {
            "critical": 20,
            "high": 10,
            "medium": 5,
            "low": 1
        }
        
        for f in findings:
            score -= severity_penalties.get(f.severity, 0)
        
        return max(0, min(100, round(score, 1)))