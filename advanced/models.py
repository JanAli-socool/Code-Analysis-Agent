from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Finding(BaseModel):
    id: str
    category: str
    severity: Severity
    title: str
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    evidence: str = ""
    recommendation: str = ""


class MetricResult(BaseModel):
    name: str
    value: float
    threshold: Optional[float] = None
    status: str = "pass"  # pass, warn, fail
    details: str = ""


class AnalysisCategory(str, Enum):
    COMPLEXITY = "complexity"
    SECURITY = "security"
    MAINTAINABILITY = "maintainability"
    TESTING = "testing"
    DEPENDENCIES = "dependencies"
    ARCHITECTURE = "architecture"
    DOCUMENTATION = "documentation"
    GIT_HISTORY = "git_history"


class CategoryScore(BaseModel):
    category: AnalysisCategory
    score: float  # 0-100
    weight: float = 1.0
    findings: List[Finding] = []
    metrics: List[MetricResult] = []


class RepositoryAnalysis(BaseModel):
    repository_path: str
    analyzed_at: datetime = Field(default_factory=datetime.now)
    overall_score: float = 0.0
    category_scores: List[CategoryScore] = []
    summary: str = ""
    strengths: List[str] = []
    weaknesses: List[str] = []
    risk_level: str = "unknown"  # low, medium, high, critical
    files_analyzed: int = 0
    total_lines: int = 0


class AgentContext(BaseModel):
    repository_path: str
    analysis: Optional[RepositoryAnalysis] = None
    file_contents: Dict[str, str] = {}
    git_history: List[Dict[str, Any]] = []
    shared_memory: Dict[str, Any] = {}