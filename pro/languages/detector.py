"""
Language Detection and Registry System
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class Language(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"
    CPP = "cpp"
    CSHARP = "csharp"
    RUBY = "ruby"
    PHP = "php"
    RUST = "rust"
    SWIFT = "swift"
    KOTLIN = "kotlin"
    SCALA = "scala"
    R = "r"
    UNKNOWN = "unknown"


@dataclass
class LanguageInfo:
    language: Language
    extensions: List[str]
    filename_patterns: List[str]
    config_files: List[str]
    shebang_patterns: List[str]
    weight: int = 1


LANGUAGE_REGISTRY: Dict[Language, LanguageInfo] = {
    Language.PYTHON: LanguageInfo(
        language=Language.PYTHON,
        extensions=[".py", ".pyw", ".pyi", ".pyx", ".pxd", ".pxi"],
        filename_patterns=["setup.py", "requirements.txt", "pyproject.toml", "Pipfile", "poetry.lock", "tox.ini"],
        config_files=["setup.cfg", "setup.py", "pyproject.toml", "requirements*.txt", "Pipfile", "poetry.lock"],
        shebang_patterns=["python", "python3"],
        weight=10
    ),
    Language.JAVASCRIPT: LanguageInfo(
        language=Language.JAVASCRIPT,
        extensions=[".js", ".jsx", ".mjs", ".cjs"],
        filename_patterns=["package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"],
        config_files=["package.json", ".eslintrc*", ".prettierrc*", "jest.config*", "webpack.config*"],
        shebang_patterns=["node"],
        weight=10
    ),
    Language.TYPESCRIPT: LanguageInfo(
        language=Language.TYPESCRIPT,
        extensions=[".ts", ".tsx", ".d.ts"],
        filename_patterns=["tsconfig.json", "tslint.json"],
        config_files=["tsconfig.json", "tslint.json", "package.json"],
        shebang_patterns=[],
        weight=10
    ),
    Language.JAVA: LanguageInfo(
        language=Language.JAVA,
        extensions=[".java", ".jsp"],
        filename_patterns=["pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle"],
        config_files=["pom.xml", "build.gradle*", "gradle.properties", "settings.gradle*"],
        shebang_patterns=[],
        weight=10
    ),
    Language.GO: LanguageInfo(
        language=Language.GO,
        extensions=[".go"],
        filename_patterns=["go.mod", "go.sum", "go.work"],
        config_files=["go.mod", "go.sum", "go.work"],
        shebang_patterns=[],
        weight=10
    ),
    Language.CPP: LanguageInfo(
        language=Language.CPP,
        extensions=[".cpp", ".cc", ".cxx", ".c++", ".h", ".hpp", ".hxx", ".h++"],
        filename_patterns=["CMakeLists.txt", "Makefile", "meson.build", "conanfile.txt", "vcpkg.json"],
        config_files=["CMakeLists.txt", "Makefile", "*.cmake", "conanfile.*", "vcpkg.json"],
        shebang_patterns=[],
        weight=10
    ),
    Language.CSHARP: LanguageInfo(
        language=Language.CSHARP,
        extensions=[".cs", ".csx"],
        filename_patterns=["*.csproj", "*.sln", "packages.config", "project.json"],
        config_files=["*.csproj", "*.sln", "packages.config", "Directory.Build.props"],
        shebang_patterns=[],
        weight=10
    ),
    Language.RUBY: LanguageInfo(
        language=Language.RUBY,
        extensions=[".rb", ".rbw", ".rake", ".gemspec"],
        filename_patterns=["Gemfile", "Gemfile.lock", "Rakefile", "config.ru"],
        config_files=["Gemfile", "Gemfile.lock", "*.gemspec", ".rubocop.yml"],
        shebang_patterns=["ruby"],
        weight=5
    ),
    Language.PHP: LanguageInfo(
        language=Language.PHP,
        extensions=[".php", ".phtml", ".php3", ".php4", ".php5", ".php7", ".php8"],
        filename_patterns=["composer.json", "composer.lock", "phpunit.xml", "phpcs.xml"],
        config_files=["composer.json", "composer.lock", "phpunit.xml*", "phpcs.xml*"],
        shebang_patterns=["php"],
        weight=5
    ),
    Language.RUST: LanguageInfo(
        language=Language.RUST,
        extensions=[".rs"],
        filename_patterns=["Cargo.toml", "Cargo.lock"],
        config_files=["Cargo.toml", "Cargo.lock", "rustfmt.toml", "clippy.toml"],
        shebang_patterns=[],
        weight=5
    ),
    Language.SWIFT: LanguageInfo(
        language=Language.SWIFT,
        extensions=[".swift"],
        filename_patterns=["Package.swift", "Package.resolved", "*.xcodeproj", "*.xcworkspace"],
        config_files=["Package.swift", "Package.resolved", "*.xcodeproj", "*.xcworkspace"],
        shebang_patterns=[],
        weight=5
    ),
    Language.KOTLIN: LanguageInfo(
        language=Language.KOTLIN,
        extensions=[".kt", ".kts", ".ktm"],
        filename_patterns=["build.gradle.kts", "settings.gradle.kts", "pom.xml"],
        config_files=["build.gradle.kts", "settings.gradle.kts", "pom.xml"],
        shebang_patterns=[],
        weight=5
    ),
    Language.SCALA: LanguageInfo(
        language=Language.SCALA,
        extensions=[".scala", ".sc"],
        filename_patterns=["build.sbt", "build.sc", "build.gradle"],
        config_files=["build.sbt", "build.sc", "build.gradle*"],
        shebang_patterns=[],
        weight=5
    ),
    Language.R: LanguageInfo(
        language=Language.R,
        extensions=[".r", ".R", ".rmd", ".Rmd"],
        filename_patterns=["DESCRIPTION", "NAMESPACE", "renv.lock"],
        config_files=["DESCRIPTION", "NAMESPACE", "renv.lock", ".Rprofile"],
        shebang_patterns=["Rscript"],
        weight=5
    ),
}


class LanguageDetector:
    def __init__(self):
        self._extension_map: Dict[str, Language] = {}
        self._filename_map: Dict[str, Language] = {}
        self._config_map: Dict[str, Language] = {}
        self._shebang_map: Dict[str, Language] = {}
        self._build_maps()

    def _build_maps(self):
        for lang, info in LANGUAGE_REGISTRY.items():
            for ext in info.extensions:
                self._extension_map[ext.lower()] = lang
            for pattern in info.filename_patterns:
                self._filename_map[pattern.lower()] = lang
            for pattern in info.config_files:
                self._config_map[pattern.lower()] = lang
            for pattern in info.shebang_patterns:
                self._shebang_map[pattern.lower()] = lang

    def detect_from_extension(self, filepath: str) -> Optional[Language]:
        ext = Path(filepath).suffix.lower()
        return self._extension_map.get(ext)

    def detect_from_filename(self, filename: str) -> Optional[Language]:
        fname = filename.lower()
        for pattern, lang in self._filename_map.items():
            if self._match_pattern(fname, pattern):
                return lang
        return None

    def detect_from_config(self, filename: str) -> Optional[Language]:
        fname = filename.lower()
        for pattern, lang in self._config_map.items():
            if self._match_pattern(fname, pattern):
                return lang
        return None

    def detect_from_shebang(self, first_line: str) -> Optional[Language]:
        first_line = first_line.lower()
        for pattern, lang in self._shebang_map.items():
            if pattern in first_line:
                return lang
        return None

    def _match_pattern(self, filename: str, pattern: str) -> bool:
        if "*" in pattern:
            import fnmatch
            return fnmatch.fnmatch(filename, pattern)
        return filename == pattern

    def detect_language(self, file_path: str, content: str = "") -> Language:
        path = Path(file_path)
        
        # Check explicit config files first (highest confidence)
        lang = self.detect_from_config(path.name)
        if lang:
            return lang
        
        # Check filename patterns
        lang = self.detect_from_filename(path.name)
        if lang:
            return lang
        
        # Check extension
        lang = self.detect_from_extension(file_path)
        if lang:
            return lang
        
        # Check shebang
        if content:
            first_line = content.split('\n')[0] if content else ""
            if first_line.startswith('#!'):
                lang = self.detect_from_shebang(first_line)
                if lang:
                    return lang
        
        return Language.UNKNOWN

    def detect_repository_languages(self, repo_path: str, file_contents: Dict[str, str]) -> Dict[Language, int]:
        counts = {}
        for rel_path, content in file_contents.items():
            lang = self.detect_language(rel_path, content)
            if lang != Language.UNKNOWN:
                counts[lang] = counts.get(lang, 0) + 1
        return counts

    def get_primary_language(self, file_contents: Dict[str, str]) -> Language:
        counts = self.detect_repository_languages("", file_contents)
        if not counts:
            return Language.UNKNOWN
        return max(counts.items(), key=lambda x: x[1])[0]

    def get_supported_languages(self) -> List[Language]:
        return list(LANGUAGE_REGISTRY.keys())

    def get_language_info(self, language: Language) -> Optional[LanguageInfo]:
        return LANGUAGE_REGISTRY.get(language)


# Global detector instance
_detector = None

def get_detector() -> LanguageDetector:
    global _detector
    if _detector is None:
        _detector = LanguageDetector()
    return _detector