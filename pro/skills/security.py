"""
Enhanced Security Skill with multiple detectors and SARIF output.
"""
import json
import subprocess
import tempfile
import os
import re
import ast
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from pro.config.loader import get_config
from pro.cache.manager import AnalysisCache


@dataclass
class SecurityFinding:
    id: str
    rule_id: str
    severity: str  # critical, high, medium, low, info
    confidence: str  # high, medium, low
    message: str
    file_path: str
    line_start: int
    line_end: int
    column_start: int
    column_end: int
    code_snippet: str
    cwe: Optional[str] = None
    owasp: Optional[str] = None
    recommendation: str = ""
    references: List[str] = None

    def to_sarif(self) -> Dict:
        return {
            "ruleId": self.rule_id,
            "level": self._severity_to_sarif_level(),
            "message": {"text": self.message},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": self.file_path},
                    "region": {
                        "startLine": self.line_start,
                        "endLine": self.line_end,
                        "startColumn": self.column_start,
                        "endColumn": self.column_end,
                        "snippet": {"text": self.code_snippet}
                    }
                }
            }],
            "properties": {
                "confidence": self.confidence,
                "cwe": self.cwe,
                "owasp": self.owasp,
                "recommendation": self.recommendation,
                "references": self.references or []
            }
        }

    def _severity_to_sarif_level(self) -> str:
        mapping = {
            "critical": "error",
            "high": "error",
            "medium": "warning",
            "low": "note",
            "info": "none"
        }
        return mapping.get(self.severity, "warning")


class SecuritySkill:
    def __init__(self, cache: AnalysisCache = None):
        self.cache = cache
        self.config = get_config().analysis.security
        self._custom_patterns = self._load_custom_patterns()

    def _load_custom_patterns(self) -> List[Dict]:
        """Load custom security patterns for AST-based detection."""
        return [
            {
                "id": "hardcoded-secret",
                "name": "Hardcoded Secret",
                "pattern": re.compile(r'(password|secret|api_key|token|private_key)\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
                "severity": "high",
                "message": "Hardcoded secret detected",
                "cwe": "CWE-798"
            },
            {
                "id": "sql-format-string",
                "name": "SQL Format String Injection",
                "pattern": re.compile(r'(execute|query|cursor)\s*\(\s*f["\'].*\{.*\}.*["\']', re.IGNORECASE),
                "severity": "high",
                "message": "Potential SQL injection via f-string",
                "cwe": "CWE-89"
            },
            {
                "id": "shell-injection",
                "name": "Shell Command Injection",
                "pattern": re.compile(r'(subprocess|os\.system|os\.popen|commands\.getstatusoutput)\s*\(.*\+.*\)', re.IGNORECASE),
                "severity": "critical",
                "message": "Potential shell command injection",
                "cwe": "CWE-78"
            },
            {
                "id": "pickle-loads",
                "name": "Unsafe Pickle Deserialization",
                "pattern": re.compile(r'pickle\.loads?\s*\(', re.IGNORECASE),
                "severity": "high",
                "message": "Unsafe pickle deserialization",
                "cwe": "CWE-502"
            },
            {
                "id": "eval-usage",
                "name": "Eval Usage",
                "pattern": re.compile(r'\beval\s*\(', re.IGNORECASE),
                "severity": "high",
                "message": "Use of eval() - code injection risk",
                "cwe": "CWE-95"
            },
            {
                "id": "exec-usage",
                "name": "Exec Usage",
                "pattern": re.compile(r'\bexec\s*\(', re.IGNORECASE),
                "severity": "high",
                "message": "Use of exec() - code injection risk",
                "cwe": "CWE-95"
            },
            {
                "id": "yaml-unsafe-load",
                "name": "Unsafe YAML Load",
                "pattern": re.compile(r'yaml\.load\s*\((?!.*Loader=yaml\.SafeLoader)', re.IGNORECASE),
                "severity": "medium",
                "message": "Unsafe yaml.load() without SafeLoader",
                "cwe": "CWE-502"
            },
            {
                "id": "debug-enabled",
                "name": "Debug Mode Enabled",
                "pattern": re.compile(r'DEBUG\s*=\s*True', re.IGNORECASE),
                "severity": "low",
                "message": "Debug mode enabled in production code",
                "cwe": "CWE-489"
            }
        ]

    def analyze(self, repo_path: str, file_contents: Dict[str, str]) -> Dict[str, Any]:
        config = self.config
        cache_key = "security_skill"

        # Check cache
        if self.cache:
            cached = self.cache.get(repo_path, cache_key, config, file_contents)
            if cached:
                return cached

        findings = []
        
        # Run Bandit
        bandit_findings = self._run_bandit(repo_path, file_contents)
        findings.extend(bandit_findings)

        # Run custom pattern detection
        custom_findings = self._run_custom_patterns(file_contents)
        findings.extend(custom_findings)

        # Run AST-based semantic analysis
        semantic_findings = self._run_semantic_analysis(file_contents)
        findings.extend(semantic_findings)

        # Calculate metrics
        metrics = self._calculate_metrics(findings)

        result = {
            "findings": [f.__dict__ for f in findings],
            "metrics": metrics,
            "score": self._calculate_score(findings, metrics)
        }

        # Cache result
        if self.cache:
            self.cache.set(repo_path, cache_key, config, file_contents, result)

        return result

    def _run_bandit(self, repo_path: str, file_contents: Dict[str, str]) -> List[SecurityFinding]:
        findings = []
        py_files = {k: v for k, v in file_contents.items() if k.endswith('.py')}

        if not py_files:
            return findings

        with tempfile.TemporaryDirectory() as tmpdir:
            for rel_path, content in py_files.items():
                full_path = os.path.join(tmpdir, rel_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w') as f:
                    f.write(content)

            try:
                cmd = ['python', '-m', 'bandit', '-r', tmpdir, '-f', 'json', 
                       '-ll', '--confidence-level', self.config.get('bandit_confidence_threshold', 'MEDIUM')]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if result.returncode in (0, 1):  # 0 = no issues, 1 = issues found
                    data = json.loads(result.stdout) if result.stdout else {"results": []}
                    for item in data.get("results", []):
                        findings.append(SecurityFinding(
                            id=f"bandit_{item.get('test_id', 'unknown')}_{item.get('line_number', 0)}",
                            rule_id=item.get('test_id', 'BANDIT'),
                            severity=item.get('issue_severity', 'MEDIUM').lower(),
                            confidence=item.get('issue_confidence', 'MEDIUM').lower(),
                            message=item.get('issue_text', ''),
                            file_path=item.get('filename', '').replace(tmpdir + os.sep, ''),
                            line_start=item.get('line_number', 1),
                            line_end=item.get('line_number', 1),
                            column_start=item.get('col_offset', 1),
                            column_end=item.get('end_col_offset', 1),
                            code_snippet=item.get('code', '').strip(),
                            cwe=item.get('issue_cwe', {}).get('id') if item.get('issue_cwe') else None,
                            recommendation=item.get('more_info', ''),
                            references=[item.get('more_info', '')] if item.get('more_info') else []
                        ))
            except Exception as e:
                # Bandit failed, continue with other detectors
                pass

        return findings

    def _run_custom_patterns(self, file_contents: Dict[str, str]) -> List[SecurityFinding]:
        findings = []
        for file_path, content in file_contents.items():
            if not file_path.endswith('.py'):
                continue
            lines = content.split('\n')
            for pattern_def in self._custom_patterns:
                for match in pattern_def['pattern'].finditer(content):
                    line_num = content[:match.start()].count('\n') + 1
                    line_content = lines[line_num - 1] if line_num <= len(lines) else ''
                    findings.append(SecurityFinding(
                        id=f"custom_{pattern_def['id']}_{file_path}_{line_num}",
                        rule_id=f"CUSTOM_{pattern_def['id'].upper()}",
                        severity=pattern_def['severity'],
                        confidence="high",
                        message=pattern_def['message'],
                        file_path=file_path,
                        line_start=line_num,
                        line_end=line_num,
                        column_start=match.start() - content.rfind('\n', 0, match.start()),
                        column_end=match.end() - content.rfind('\n', 0, match.start()),
                        code_snippet=line_content.strip(),
                        cwe=pattern_def.get('cwe'),
                        recommendation=self._get_recommendation(pattern_def['id'])
                    ))
        return findings

    def _run_semantic_analysis(self, file_contents: Dict[str, str]) -> List[SecurityFinding]:
        """AST-based semantic security analysis."""
        findings = []
        for file_path, content in file_contents.items():
            if not file_path.endswith('.py'):
                continue
            try:
                tree = ast.parse(content)
                findings.extend(self._check_ast_patterns(tree, file_path, content))
            except SyntaxError:
                pass
        return findings

    def _check_ast_patterns(self, tree: ast.AST, file_path: str, content: str) -> List[SecurityFinding]:
        findings = []
        lines = content.split('\n')

        for node in ast.walk(tree):
            # Detect: SQL concatenation
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                if self._is_sql_string(node.left) or self._is_sql_string(node.right):
                    findings.append(self._make_finding(
                        file_path, node, lines, "sql-concat",
                        "SQL query built via string concatenation", "high", "CWE-89"
                    ))

            # Detect: subprocess with shell=True
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in ('run', 'Popen', 'call'):
                        for kw in node.keywords:
                            if kw.arg == 'shell' and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                                findings.append(self._make_finding(
                                    file_path, node, lines, "shell-true",
                                    "subprocess called with shell=True", "critical", "CWE-78"
                                ))

            # Detect: random used for secrets
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in ('random', 'choice', 'randint'):
                        if isinstance(node.func.value, ast.Name) and node.func.value.id == 'random':
                            findings.append(self._make_finding(
                                file_path, node, lines, "weak-random",
                                "random module used for security-sensitive operation", "medium", "CWE-338"
                            ))

            # Detect: SSL verification disabled
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg == 'verify' and isinstance(kw.value, ast.Constant) and kw.value.value is False:
                        findings.append(self._make_finding(
                            file_path, node, lines, "ssl-verify-false",
                            "SSL certificate verification disabled", "high", "CWE-295"
                        ))

            # Detect: hardcoded credentials in assignments
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name = target.id.lower()
                        if any(s in name for s in ['password', 'secret', 'token', 'apikey', 'api_key']):
                            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                                if len(node.value.value) > 8:
                                    findings.append(self._make_finding(
                                        file_path, node, lines, "hardcoded-cred",
                                        f"Hardcoded credential in variable '{target.id}'", "high", "CWE-798"
                                    ))

        return findings

    def _is_sql_string(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            sql_keywords = ['select', 'insert', 'update', 'delete', 'from', 'where', 'join']
            return any(kw in node.value.lower() for kw in sql_keywords)
        return False

    def _make_finding(self, file_path: str, node: ast.AST, lines: List[str],
                      rule_id: str, message: str, severity: str, cwe: str) -> SecurityFinding:
        line_start = getattr(node, 'lineno', 1)
        col_start = getattr(node, 'col_offset', 0)
        line_content = lines[line_start - 1] if line_start <= len(lines) else ''
        return SecurityFinding(
            id=f"ast_{rule_id}_{file_path}_{line_start}",
            rule_id=f"AST_{rule_id.upper()}",
            severity=severity,
            confidence="medium",
            message=message,
            file_path=file_path,
            line_start=line_start,
            line_end=line_start,
            column_start=col_start,
            column_end=col_start + len(line_content),
            code_snippet=line_content.strip(),
            cwe=cwe,
            recommendation=self._get_recommendation(rule_id)
        )

    def _get_recommendation(self, rule_id: str) -> str:
        recommendations = {
            "hardcoded-secret": "Use environment variables or secret management system",
            "sql-format-string": "Use parameterized queries or ORM",
            "shell-injection": "Use subprocess with shell=False and argument list",
            "pickle-loads": "Use json or msgpack for serialization",
            "eval-usage": "Use ast.literal_eval or safe evaluation",
            "exec-usage": "Avoid dynamic code execution",
            "yaml-unsafe-load": "Use yaml.safe_load()",
            "debug-enabled": "Set DEBUG=False in production",
            "sql-concat": "Use parameterized queries",
            "shell-true": "Use subprocess with shell=False",
            "weak-random": "Use secrets module for cryptographic randomness",
            "ssl-verify-false": "Enable SSL verification or use custom CA bundle",
            "hardcoded-cred": "Use environment variables or secret management"
        }
        return recommendations.get(rule_id, "Review and remediate this security issue")

    def _calculate_metrics(self, findings: List[SecurityFinding]) -> List[Dict]:
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        confidence_counts = {"high": 0, "medium": 0, "low": 0}
        cwe_counts = {}

        for f in findings:
            severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1
            confidence_counts[f.confidence] = confidence_counts.get(f.confidence, 0) + 1
            if f.cwe:
                cwe_counts[f.cwe] = cwe_counts.get(f.cwe, 0) + 1

        return [
            {"name": "total_findings", "value": len(findings)},
            {"name": "critical_findings", "value": severity_counts["critical"]},
            {"name": "high_findings", "value": severity_counts["high"]},
            {"name": "medium_findings", "value": severity_counts["medium"]},
            {"name": "low_findings", "value": severity_counts["low"]},
            {"name": "high_confidence_findings", "value": confidence_counts["high"]},
            {"name": "unique_cwes", "value": len(cwe_counts)},
            {"name": "top_cwe", "value": max(cwe_counts.items(), key=lambda x: x[1])[0] if cwe_counts else None}
        ]

    def _calculate_score(self, findings: List[SecurityFinding], metrics: List[Dict]) -> float:
        score = 100.0
        metric_dict = {m['name']: m['value'] for m in metrics}
        
        # More reasonable penalties
        score -= metric_dict.get('critical_findings', 0) * 20
        score -= metric_dict.get('high_findings', 0) * 8
        score -= metric_dict.get('medium_findings', 0) * 4
        score -= metric_dict.get('low_findings', 0) * 1
        
        return max(0, min(100, round(score, 1)))