"""
Java Language Skill
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
class JavaFinding:
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


class JavaSkill:
    def __init__(self, cache: AnalysisCache = None):
        self.cache = cache
        self.config = get_config()

    def analyze(self, repo_path: str, file_contents: Dict[str, str]) -> Dict[str, Any]:
        config = self.config.analysis
        cache_key = "java_skill"

        if self.cache:
            cached = self.cache.get(repo_path, cache_key, config.__dict__, file_contents)
            if cached:
                return cached

        findings = []
        java_files = {k: v for k, v in file_contents.items() if k.endswith('.java')}

        if not java_files:
            return {"findings": [], "metrics": {}, "score": 100.0, "file_count": 0}

        # Run SpotBugs/FindBugs if available
        spotbugs_findings = self._run_spotbugs(repo_path, java_files)
        findings.extend(spotbugs_findings)

        # Run Checkstyle if available
        checkstyle_findings = self._run_checkstyle(repo_path, java_files)
        findings.extend(checkstyle_findings)

        # Custom pattern detection
        custom_findings = self._run_custom_patterns(java_files)
        findings.extend(custom_findings)

        # Maven/Gradle analysis
        build_findings = self._analyze_build_files(file_contents)
        findings.extend(build_findings)

        # Calculate metrics
        metrics = self._calculate_metrics(java_files, findings)
        score = self._calculate_score(findings, metrics)

        result = {
            "findings": [f.__dict__ for f in findings],
            "metrics": metrics,
            "score": score,
            "file_count": len(java_files),
            "lines_of_code": sum(len(c.split('\n')) for c in java_files.values())
        }

        if self.cache:
            self.cache.set(repo_path, "java_skill", {}, file_contents, result)

        return result

    def _run_spotbugs(self, repo_path: str, java_files: Dict[str, str]) -> List[Any]:
        findings = []
        
        # Check if spotbugs is available via Maven/Gradle
        try:
            # Try Maven spotbugs plugin
            result = subprocess.run(['mvn', 'spotbugs:check', '-q'], 
                                  cwd=repo_path, capture_output=True, text=True, timeout=180)
            # SpotBugs returns non-zero when bugs found
            if result.returncode in (0, 1):
                # Parse XML output if available
                pass
        except FileNotFoundError:
            pass
        
        return findings

    def _run_checkstyle(self, repo_path: str, java_files: Dict[str, str]) -> List[Any]:
        findings = []
        
        try:
            result = subprocess.run(['mvn', 'checkstyle:check', '-q'],
                                  cwd=repo_path, capture_output=True, text=True, timeout=180)
        except FileNotFoundError:
            pass
        
        return findings

    def _run_custom_patterns(self, java_files: Dict[str, str]) -> List[JavaFinding]:
        findings = []
        
        patterns = [
            {
                "id": "sql-injection",
                "name": "SQL Injection Risk",
                "pattern": re.compile(r'Statement.*executeQuery\s*\(\s*["\'].*\+.*["\']'),
                "severity": "high",
                "message": "Potential SQL injection via string concatenation",
                "recommendation": "Use PreparedStatement with parameterized queries"
            },
            {
                "id": "hardcoded-password",
                "name": "Hardcoded Password/Secret",
                "pattern": re.compile(r'(password|secret|apiKey|api_key|privateKey|private_key)\s*=\s*["\'][^"\']{8,}["\']', re.IGNORECASE),
                "severity": "high",
                "message": "Hardcoded credential detected",
                "recommendation": "Use environment variables or secret management"
            },
            {
                "id": "empty-catch",
                "name": "Empty Catch Block",
                "pattern": re.compile(r'catch\s*\([^)]*\)\s*\{\s*\}'),
                "severity": "medium",
                "message": "Empty catch block - exceptions silently ignored",
                "recommendation": "Handle or log the exception"
            },
            {
                "id": "system-out-print",
                "name": "System.out.println in Production",
                "pattern": re.compile(r'System\.out\.print'),
                "severity": "low",
                "message": "System.out.println in production code",
                "recommendation": "Use proper logging framework (SLF4J, Log4j)"
            },
            {
                "id": "print-stack-trace",
                "name": "printStackTrace() Usage",
                "pattern": re.compile(r'\.printStackTrace\s*\(\s*\)'),
                "severity": "medium",
                "message": "printStackTrace() prints to stderr directly",
                "recommendation": "Use logger.error() with exception"
            },
            {
                "id": "runtime-exec",
                "name": "Runtime.exec() Usage",
                "pattern": re.compile(r'Runtime\.getRuntime\s*\(\s*\)\.exec'),
                "severity": "high",
                "message": "Runtime.exec() - command injection risk",
                "recommendation": "Use ProcessBuilder with command list"
            },
            {
                "id": "deserialization",
                "name": "Unsafe Deserialization",
                "pattern": re.compile(r'ObjectInputStream.*readObject'),
                "severity": "high",
                "message": "Unsafe deserialization - potential RCE",
                "recommendation": "Validate input, use safe serialization formats"
            },
            {
                "id": "weak-random",
                "name": "Weak Random Number Generation",
                "pattern": re.compile(r'new Random\s*\('),
                "severity": "medium",
                "message": "java.util.Random is not cryptographically secure",
                "recommendation": "Use SecureRandom for security-sensitive operations"
            },
            {
                "id": "hardcoded-crypto-key",
                "name": "Hardcoded Cryptographic Key",
                "pattern": re.compile(r'(SecretKeySpec|IvParameterSpec).*["\'][A-Za-z0-9+/=]{16,}["\']'),
                "severity": "critical",
                "message": "Hardcoded cryptographic key/IV",
                "recommendation": "Use key management system or environment variables"
            },
            {
                "id": "insecure-xml-parser",
                "name": "Insecure XML Parser (XXE)",
                "pattern": re.compile(r'DocumentBuilderFactory.*newInstance\s*\(\s*\)'),
                "severity": "high",
                "message": "Default DocumentBuilderFactory vulnerable to XXE",
                "recommendation": "Set setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true)"
            },
            {
                "id": "path-traversal",
                "name": "Path Traversal Risk",
                "pattern": re.compile(r'new File\s*\(\s*.*\+\s*.*\)'),
                "severity": "medium",
                "message": "Potential path traversal via string concatenation",
                "recommendation": "Validate and normalize paths using Path.normalize()"
            },
        ]

        for file_path, content in java_files.items():
            lines = content.split('\n')
            for pattern_def in patterns:
                for match in pattern_def["pattern"].finditer(content):
                    line_num = content[:match.start()].count('\n') + 1
                    line_content = lines[line_num - 1] if line_num <= len(lines) else ''
                    
                    findings.append(JavaFinding(
                        id=f"java_{pattern_def['id']}_{file_path}_{line_num}",
                        category="java",
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

    def _analyze_build_files(self, file_contents: Dict[str, str]) -> List[JavaFinding]:
        findings = []
        
        for file_path, content in file_contents.items():
            filename = Path(file_path).name
            
            if filename == 'pom.xml':
                findings.extend(self._analyze_pom(content, file_path))
            elif filename in ('build.gradle', 'build.gradle.kts'):
                findings.extend(self._analyze_gradle(content, file_path))
            elif filename == 'settings.gradle':
                findings.extend(self._analyze_settings_gradle(content, file_path))
        
        return findings

    def _analyze_pom(self, content: str, file_path: str) -> List[JavaFinding]:
        findings = []
        
        # Check for dependency versions
        if '<version>' not in content and '<dependencyManagement>' not in content:
            findings.append(JavaFinding(
                id=f"unmanaged_deps_{file_path}",
                category="dependencies",
                severity="medium",
                title="Unmanaged dependency versions",
                description="Dependencies declared without version management",
                file_path=file_path,
                line_start=1,
                line_end=1,
                column_start=1,
                column_end=1,
                code_snippet="",
                recommendation="Use dependencyManagement or BOMs to manage versions",
                rule_id="unmanaged_dependencies"
            ))
        
        # Check for snapshot dependencies
        snapshot_count = len(re.findall(r'<version>[^<]*-SNAPSHOT</version>', content))
        if snapshot_count > 0:
            findings.append(JavaFinding(
                id=f"snapshot_deps_{file_path}",
                category="dependencies",
                severity="medium",
                title=f"SNAPSHOT dependencies ({snapshot_count})",
                description="SNAPSHOT dependencies are not reproducible",
                file_path=file_path,
                line_start=1,
                line_end=1,
                column_start=1,
                column_end=1,
                code_snippet="",
                recommendation="Replace SNAPSHOT with release versions for production",
                rule_id="snapshot_dependencies"
            ))
        
        # Check for known vulnerable dependencies
        vulnerable_patterns = {
            'log4j': r'<artifactId>log4j</artifactId>\s*<version>1\.',
            'struts2': r'<artifactId>struts2-core</artifactId>\s*<version>2\.(0|1|2|3|4|5)\.',
            'spring-boot': r'<artifactId>spring-boot-starter</artifactId>\s*<version>1\.|2\.[0-4]\.',
        }
        
        for name, pattern in vulnerable_patterns.items():
            if re.search(pattern, content):
                findings.append(JavaFinding(
                    id=f"vuln_{name}_{file_path}",
                    category="security",
                    severity="high",
                    title=f"Known vulnerable dependency: {name}",
                    description=f"Dependency {name} has known vulnerabilities",
                    file_path=file_path,
                    line_start=1,
                    line_end=1,
                    column_start=1,
                    column_end=1,
                    code_snippet="",
                    recommendation=f"Upgrade {name} to a secure version",
                    rule_id=f"vulnerable_{name}"
                ))
        
        return findings

    def _analyze_gradle(self, content: str, file_path: str) -> List[JavaFinding]:
        findings = []
        
        # Check for dynamic versions
        if re.search(r'version\s+["\']\+\.[\'\"]', content):
            findings.append(JavaFinding(
                id=f"dynamic_version_{file_path}",
                category="dependencies",
                severity="medium",
                title="Dynamic version resolution",
                description="Using dynamic version '+' in dependencies",
                file_path=file_path,
                line_start=1,
                line_end=1,
                column_start=1,
                column_end=1,
                code_snippet="",
                recommendation="Pin all dependency versions",
                rule_id="dynamic_version"
            ))
        
        # Check for mavenCentral() without HTTPS
        if 'mavenCentral()' in content and 'https://repo.maven.apache.org/maven2' not in content:
            findings.append(JavaFinding(
                id=f"insecure_repo_{file_path}",
                category="security",
                severity="medium",
                title="Insecure Maven repository",
                description="Using mavenCentral() without explicit HTTPS",
                file_path=file_path,
                line_start=1,
                line_end=1,
                column_start=1,
                column_end=1,
                code_snippet="",
                recommendation="Explicitly use https://repo.maven.apache.org/maven2",
                rule_id="insecure_repository"
            ))
        
        return findings

    def _analyze_settings_gradle(self, content: str, file_path: str) -> List[JavaFinding]:
        findings = []
        
        # Check for insecure repositories
        if 'http://' in content and 'maven' in content.lower():
            findings.append(JavaFinding(
                id=f"insecure_http_repo_{file_path}",
                category="security",
                severity="high",
                title="Insecure HTTP repository",
                description="Repository URL uses HTTP instead of HTTPS",
                file_path=file_path,
                line_start=1,
                line_end=1,
                column_start=1,
                column_end=1,
                code_snippet="",
                recommendation="Use HTTPS for all repository URLs",
                rule_id="insecure_http_repository"
            ))
        
        return findings

    def _calculate_metrics(self, java_files: Dict[str, str], findings: List[Any]) -> Dict[str, Any]:
        total_lines = sum(len(c.split('\n')) for c in java_files.values())
        total_files = len(java_files)
        
        severity_counts = Counter(f.severity for f in findings)
        category_counts = Counter(f.category for f in findings)
        
        # Class/interface/enum counts
        class_count = sum(len(re.findall(r'\bclass\s+\w+', c)) for c in java_files.values())
        interface_count = sum(len(re.findall(r'\binterface\s+\w+', c)) for c in java_files.values())
        enum_count = sum(len(re.findall(r'\benum\s+\w+', c)) for c in java_files.values())
        
        # Method counts
        method_count = sum(len(re.findall(r'(public|private|protected)\s+\w+\s+\w+\s*\(', c)) for c in java_files.values())
        
        return {
            "total_files": len(java_files),
            "total_lines": sum(len(c.split('\n')) for c in java_files.values()),
            "total_classes": class_count,
            "total_interfaces": interface_count,
            "total_enums": enum_count,
            "total_methods": method_count,
            "total_findings": len(findings),
            "critical_findings": Counter(f.severity for f in findings).get("critical", 0),
            "high_findings": Counter(f.severity for f in findings).get("high", 0),
            "medium_findings": Counter(f.severity for f in findings).get("medium", 0),
            "low_findings": Counter(f.severity for f in findings).get("low", 0),
            "findings_by_category": dict(category_counts),
            "avg_lines_per_file": total_lines / max(len(java_files), 1)
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
        
        # Bonus for modern Java features
        return max(0, min(100, round(score, 1)))