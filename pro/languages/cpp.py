"""
C/C++ Language Skill
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
class CppFinding:
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


class CppSkill:
    def __init__(self, cache: AnalysisCache = None):
        self.cache = cache
        self.config = get_config()

    def analyze(self, repo_path: str, file_contents: Dict[str, str]) -> Dict[str, Any]:
        config = self.config.analysis
        cache_key = "cpp_skill"

        if self.cache:
            cached = self.cache.get(repo_path, cache_key, self.config.analysis.__dict__, file_contents)
            if cached:
                return cached

        findings = []
        cpp_files = {k: v for k, v in file_contents.items() 
                    if k.endswith(('.cpp', '.cc', '.cxx', '.c++', '.c', '.h', '.hpp', '.hxx', '.h++'))}

        if not cpp_files:
            return {"findings": [], "metrics": {}, "score": 100.0, "file_count": 0}

        # Run cppcheck if available
        cppcheck_findings = self._run_cppcheck(repo_path, cpp_files)
        findings.extend(cppcheck_findings)

        # Run clang-tidy if available
        clangtidy_findings = self._run_clang_tidy(repo_path, cpp_files)
        findings.extend(clangtidy_findings)

        # Custom pattern detection
        custom_findings = self._run_custom_patterns(cpp_files)
        findings.extend(custom_findings)

        # CMake/Makefile analysis
        build_findings = self._analyze_build_files(file_contents)
        findings.extend(build_findings)

        # Calculate metrics
        metrics = self._calculate_metrics(cpp_files, findings)
        score = self._calculate_score(findings, metrics)

        result = {
            "findings": [f.__dict__ for f in findings],
            "metrics": metrics,
            "score": score,
            "file_count": len(cpp_files),
            "lines_of_code": sum(len(c.split('\n')) for c in cpp_files.values())
        }

        if self.cache:
            self.cache.set(repo_path, "cpp_skill", {}, file_contents, result)

        return result

    def _run_cppcheck(self, repo_path: str, cpp_files: Dict[str, str]) -> List[Any]:
        findings = []
        
        try:
            result = subprocess.run(['cppcheck', '--version'], capture_output=True, timeout=5)
            if result.returncode != 0:
                return findings
        except FileNotFoundError:
            return findings

        with tempfile.TemporaryDirectory() as tmpdir:
            for rel_path, content in cpp_files.items():
                full_path = os.path.join(tmpdir, rel_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w') as f:
                    f.write(content)

            try:
                result = subprocess.run([
                    'cppcheck', '--enable=all', '--inline-suppr', '--quiet',
                    '--output-file=-', '.'
                ], cwd=tmpdir, capture_output=True, text=True, timeout=120)
                
                # cppcheck outputs to stderr
                for line in (result.stdout + result.stderr).split('\n'):
                    if line.strip() and ':' in line and 'error' in line.lower():
                        # Parse cppcheck output format
                        pass
            except Exception:
                pass

        return findings

    def _run_clang_tidy(self, repo_path: str, cpp_files: Dict[str, str]) -> List[Any]:
        return []

    def _run_custom_patterns(self, cpp_files: Dict[str, str]) -> List[Any]:
        findings = []
        
        patterns = [
            {
                "id": "buffer-overflow",
                "name": "Buffer Overflow Risk",
                "pattern": re.compile(r'\b(strcpy|strcat|sprintf|gets|scanf)\s*\('),
                "severity": "critical",
                "message": "Unsafe function - potential buffer overflow",
                "recommendation": "Use safe alternatives: strncpy, strncat, snprintf, fgets"
            },
            {
                "id": "format-string",
                "name": "Format String Vulnerability",
                "pattern": re.compile(r'printf\s*\([^)]*%[^)]*\)\s*;'),
                "severity": "high",
                "message": "Potential format string vulnerability",
                "recommendation": "Use format string literals: printf(\"%s\", user_input)"
            },
            {
                "id": "use-after-free",
                "name": "Potential Use After Free",
                "pattern": re.compile(r'free\s*\([^)]*\)\s*;[^}]*\w+\s*->'),
                "severity": "high",
                "message": "Potential use after free",
                "recommendation": "Set pointer to NULL after free"
            },
            {
                "id": "memory-leak",
                "name": "Potential Memory Leak",
                "pattern": re.compile(r'malloc\s*\([^)]*\)\s*;[^}]*(?!free)'),
                "severity": "medium",
                "message": "Potential memory leak - malloc without matching free",
                "recommendation": "Ensure every malloc has a matching free"
            },
            {
                "id": "double-free",
                "name": "Potential Double Free",
                "pattern": re.compile(r'free\s*\([^)]*\)\s*;[^}]*free\s*\(\s*\1\s*\)'),
                "severity": "high",
                "message": "Potential double free",
                "recommendation": "Set pointer to NULL after free"
            },
            {
                "id": "null-dereference",
                "name": "Potential Null Pointer Dereference",
                "pattern": re.compile(r'\w+\s*=\s*malloc\s*\([^)]*\)\s*;[^}]*\w+\s*->'),
                "severity": "high",
                "message": "Potential null pointer dereference after malloc",
                "recommendation": "Check malloc return value before use"
            },
            {
                "id": "integer-overflow",
                "name": "Integer Overflow Risk",
                "pattern": re.compile(r'\b(malloc|calloc|realloc)\s*\(\s*\w+\s*\*\s*\w+'),
                "severity": "medium",
                "message": "Potential integer overflow in allocation size",
                "recommendation": "Check for overflow before multiplication"
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
                "id": "system-command",
                "name": "System Command Injection",
                "pattern": re.compile(r'system\s*\([^)]*\+'),
                "severity": "high",
                "message": "Command injection via system() with concatenation",
                "recommendation": "Use exec family with argument array"
            },
            {
                "id": "shell-exec",
                "name": "Shell Execution",
                "pattern": re.compile(r'popen\s*\('),
                "severity": "high",
                "message": "popen() with user input - command injection risk",
                "recommendation": "Use fork/exec with argument array"
            },
            {
                "id": "unsafe-random",
                "name": "Insecure Random",
                "pattern": re.compile(r'\brand\s*\(\s*\)'),
                "severity": "medium",
                "message": "rand() is not cryptographically secure",
                "recommendation": "Use /dev/urandom or cryptographic RNG"
            },
            {
                "id": "path-traversal",
                "name": "Path Traversal",
                "pattern": re.compile(r'fopen\s*\([^)]*\.\./'),
                "severity": "high",
                "message": "Potential path traversal",
                "recommendation": "Validate and sanitize file paths"
            },
            {
                "id": "weak-crypto",
                "name": "Weak Cryptography",
                "pattern": re.compile(r'\b(MD5|SHA1|DES|RC4|ECB)\b'),
                "severity": "high",
                "message": "Weak cryptographic algorithm",
                "recommendation": "Use SHA-256+, AES-GCM, ChaCha20-Poly1305"
            },
            {
                "id": "hardcoded-key",
                "name": "Hardcoded Cryptographic Key",
                "pattern": re.compile(r'(key|iv|salt)\s*=\s*["\'][A-Za-z0-9+/=]{16,}["\']'),
                "severity": "critical",
                "message": "Hardcoded cryptographic key/IV",
                "recommendation": "Use key management system or environment variables"
            },
        ]

        findings = []
        for file_path, content in cpp_files.items():
            lines = content.split('\n')
            for pattern_def in patterns:
                for match in pattern_def["pattern"].finditer(content):
                    line_num = content[:match.start()].count('\n') + 1
                    line_content = lines[line_num - 1] if line_num <= len(lines) else ''
                    
                    findings.append(CppFinding(
                        id=f"cpp_{pattern_def['id']}_{file_path}_{line_num}",
                        category="cpp",
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

    def _analyze_build_files(self, file_contents: Dict[str, str]) -> List[Any]:
        findings = []
        
        for file_path, content in file_contents.items():
            filename = Path(file_path).name
            
            if filename in ('CMakeLists.txt', 'cmake', 'CMakeCache.txt'):
                findings.extend(self._analyze_cmake(content, file_path))
            elif filename in ('Makefile', 'makefile', 'GNUmakefile'):
                findings.extend(self._analyze_makefile(content, file_path))
            elif filename in ('conanfile.txt', 'conanfile.py', 'vcpkg.json', 'pkg-config'):
                findings.extend(self._analyze_package_manager(content, file_path, filename))
        
        return findings

    def _analyze_cmake(self, content: str, file_path: str) -> List[Any]:
        findings = []
        
        # Check for minimum CMake version
        if not re.search(r'cmake_minimum_required\s*\(', content):
            findings.append({
                "id": f"cmake_no_version_{file_path}",
                "category": "build",
                "severity": "low",
                "title": "Missing cmake_minimum_required",
                "description": "CMakeLists.txt missing cmake_minimum_required()",
                "file_path": file_path,
                "line_start": 1,
                "line_end": 1,
                "column_start": 1,
                "column_end": 1,
                "code_snippet": "",
                "recommendation": "Add cmake_minimum_required(VERSION 3.10)",
                "rule_id": "cmake_minimum_required"
            })
        
        # Check for C++ standard
        if not re.search(r'set\s*\(\s*CMAKE_CXX_STANDARD\s+\d+', content):
            findings.append({
                "id": f"cmake_no_cxx_standard_{file_path}",
                "category": "build",
                "severity": "medium",
                "title": "C++ standard not specified",
                "description": "CMakeLists.txt doesn't set C++ standard",
                "file_path": file_path,
                "line_start": 1,
                "line_end": 1,
                "column_start": 1,
                "column_end": 1,
                "code_snippet": "",
                "recommendation": "Set CMAKE_CXX_STANDARD to 17 or higher",
                "rule_id": "cmake_cxx_standard"
            })
        
        # Check for warning flags
        if not re.search(r'(Wall|Wextra|Wpedantic|Werror)', content):
            findings.append({
                "id": f"cmake_no_warnings_{file_path}",
                "category": "build",
                "severity": "low",
                "title": "Compiler warnings not enabled",
                "description": "CMakeLists.txt doesn't enable compiler warnings",
                "file_path": file_path,
                "line_start": 1,
                "line_end": 1,
                "column_start": 1,
                "column_end": 1,
                "code_snippet": "",
                "recommendation": "Add -Wall -Wextra -Wpedantic -Werror",
                "rule_id": "cmake_warnings"
            })
        
        # Check for secure flags
        if not re.search(r'(FORTIFY_SOURCE|stack-protector|PIE)', content):
            findings.append({
                "id": f"cmake_no_hardening_{file_path}",
                "category": "security",
                "severity": "medium",
                "title": "Missing compiler hardening flags",
                "description": "CMakeLists.txt doesn't enable security hardening",
                "file_path": file_path,
                "line_start": 1,
                "line_end": 1,
                "column_start": 1,
                "column_end": 1,
                "code_snippet": "",
                "recommendation": "Add -D_FORTIFY_SOURCE=2 -fstack-protector-strong -fPIE",
                "rule_id": "cmake_hardening"
            })
        
        return findings

    def _analyze_makefile(self, content: str, file_path: str) -> List[Any]:
        findings = []
        
        # Check for security flags
        if not re.search(r'-fstack-protector|-D_FORTIFY_SOURCE|-fPIE|-fPIC', content):
            findings.append({
                "id": f"makefile_no_hardening_{file_path}",
                "category": "security",
                "severity": "medium",
                "title": "Missing compiler hardening flags",
                "description": "Makefile doesn't enable security hardening flags",
                "file_path": file_path,
                "line_start": 1,
                "line_end": 1,
                "column_start": 1,
                "column_end": 1,
                "code_snippet": "",
                "recommendation": "Add -fstack-protector-strong -D_FORTIFY_SOURCE=2 -fPIE",
                "rule_id": "makefile_hardening"
            })
        
        # Check for warning flags
        if not re.search(r'-Wall|-Wextra|-Wpedantic|-Werror', content):
            findings.append({
                "id": f"makefile_no_warnings_{file_path}",
                "category": "build",
                "severity": "low",
                "title": "Compiler warnings not enabled",
                "description": "Makefile doesn't enable compiler warnings",
                "file_path": file_path,
                "line_start": 1,
                "line_end": 1,
                "column_start": 1,
                "column_end": 1,
                "code_snippet": "",
                "recommendation": "Add -Wall -Wextra -Wpedantic -Werror",
                "rule_id": "makefile_warnings"
            })
        
        return findings

    def _analyze_package_manager(self, content: str, file_path: str, filename: str) -> List[Any]:
        findings = []
        
        if filename in ('conanfile.txt', 'conanfile.py'):
            # Check for outdated packages
            pass
        
        return findings

    def _calculate_metrics(self, cpp_files: Dict[str, str], findings: List[Any]) -> Dict[str, Any]:
        total_lines = sum(len(c.split('\n')) for c in cpp_files.values())
        total_files = len(cpp_files)
        
        severity_counts = Counter(f.severity for f in findings)
        category_counts = Counter(f.category for f in findings)
        
        # C++ specific metrics
        class_count = sum(len(re.findall(r'\bclass\s+\w+', c)) for c in cpp_files.values())
        struct_count = sum(len(re.findall(r'\bstruct\s+\w+', c)) for c in cpp_files.values())
        template_count = sum(len(re.findall(r'\btemplate\s*<', c)) for c in cpp_files.values())
        virtual_count = sum(len(re.findall(r'\bvirtual\s+', c)) for c in cpp_files.values())
        namespace_count = sum(len(re.findall(r'\bnamespace\s+\w+', c)) for c in cpp_files.values())
        
        return {
            "total_files": len(cpp_files),
            "total_lines": sum(len(c.split('\n')) for c in cpp_files.values()),
            "total_classes": class_count,
            "total_structs": struct_count,
            "total_templates": template_count,
            "virtual_functions": virtual_count,
            "namespaces": namespace_count,
            "total_findings": len(findings),
            "critical_findings": Counter(f.severity for f in findings).get("critical", 0),
            "high_findings": Counter(f.severity for f in findings).get("high", 0),
            "medium_findings": Counter(f.severity for f in findings).get("medium", 0),
            "low_findings": Counter(f.severity for f in findings).get("low", 0),
            "findings_by_category": dict(category_counts),
            "avg_lines_per_file": total_lines / max(len(cpp_files), 1)
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