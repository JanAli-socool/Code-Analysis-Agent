"""
Configuration management with validation and environment override support.
"""
import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass
class AnalysisConfig:
    weights: Dict[str, float]
    risk_thresholds: Dict[str, int]
    complexity: Dict[str, Any]
    security: Dict[str, Any]
    testing: Dict[str, Any]
    maintainability: Dict[str, Any]
    architecture: Dict[str, Any]
    dependencies: Dict[str, Any]
    documentation: Dict[str, Any]
    git_history: Dict[str, Any]
    # Language-specific configurations
    javascript: Dict[str, Any]
    java: Dict[str, Any]
    go: Dict[str, Any]
    cpp: Dict[str, Any]


@dataclass
class ExecutionConfig:
    parallel: bool
    max_workers: int
    timeout_per_skill: int
    timeout_total: int
    cache_enabled: bool
    cache_ttl_hours: int
    cache_dir: str
    include_patterns: list
    exclude_patterns: list


@dataclass
class OutputConfig:
    formats: list
    severity_levels: list
    include_metrics: bool
    include_recommendations: bool
    group_by: str


@dataclass
class BenchmarkConfig:
    enabled: bool
    baseline_file: str
    regression_threshold: float
    track_metrics: list


@dataclass
class IntegrationsConfig:
    github_actions: bool
    gitlab_ci: bool
    sarif_version: str
    exit_on_critical: bool
    exit_on_high: bool


@dataclass
class AppConfig:
    analysis: AnalysisConfig
    execution: ExecutionConfig
    output: OutputConfig
    benchmark: BenchmarkConfig
    integrations: IntegrationsConfig


class ConfigLoader:
    _instance: Optional['ConfigLoader'] = None
    _config: Optional[AppConfig] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, config_path: Optional[str] = None) -> AppConfig:
        if self._config is not None:
            return self._config

        if config_path is None:
            config_path = self._find_config_file()

        with open(config_path, 'r') as f:
            raw = yaml.safe_load(f)

        # Apply environment variable overrides
        raw = self._apply_env_overrides(raw)

        # Validate and create config objects
        self._config = AppConfig(
            analysis=AnalysisConfig(**raw['analysis']),
            execution=ExecutionConfig(**raw['execution']),
            output=OutputConfig(**raw['output']),
            benchmark=BenchmarkConfig(**raw['benchmark']),
            integrations=IntegrationsConfig(**raw['integrations'])
        )
        return self._config

    def _find_config_file(self) -> str:
        search_paths = [
            Path.cwd() / "code_analysis_config.yaml",
            Path.cwd() / ".code_analysis.yaml",
            Path(__file__).parent / "settings.yaml",
            Path.home() / ".code_analysis.yaml",
        ]
        for path in search_paths:
            if path.exists():
                return str(path)
        # Return default
        return str(Path(__file__).parent / "settings.yaml")

    def _apply_env_overrides(self, config: Dict) -> Dict:
        """Apply environment variable overrides: CODE_ANALYSIS_<SECTION>_<KEY>"""
        prefix = "CODE_ANALYSIS_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                parts = key[len(prefix):].lower().split('_')
                if len(parts) >= 2:
                    section = parts[0]
                    sub_key = '_'.join(parts[1:])
                    if section in config and sub_key in config[section]:
                        # Type conversion
                        orig_value = config[section][sub_key]
                        if isinstance(orig_value, bool):
                            config[section][sub_key] = value.lower() in ('true', '1', 'yes')
                        elif isinstance(orig_value, int):
                            config[section][sub_key] = int(value)
                        elif isinstance(orig_value, float):
                            config[section][sub_key] = float(value)
                        elif isinstance(orig_value, list):
                            config[section][sub_key] = value.split(',')
                        else:
                            config[section][sub_key] = value
        return config

    def get(self) -> AppConfig:
        if self._config is None:
            return self.load()
        return self._config

    def reload(self, config_path: Optional[str] = None) -> AppConfig:
        self._config = None
        return self.load(config_path)


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Singleton accessor for configuration."""
    return ConfigLoader().load()