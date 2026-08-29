"""
Base Skill Interface for Specialized Analysis Agents
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from advanced.models import AgentContext, Finding, MetricResult, CategoryScore, AnalysisCategory, Severity


class BaseSkill(ABC):
    def __init__(self, name: str, category: AnalysisCategory, weight: float = 1.0):
        self.name = name
        self.category = category
        self.weight = weight

    @abstractmethod
    def analyze(self, context: AgentContext) -> CategoryScore:
        pass

    def _create_finding(self, finding_id: str, severity: Severity, title: str, 
                       description: str, file_path: str = None, line_number: int = None,
                       evidence: str = "", recommendation: str = "") -> Finding:
        return Finding(
            id=finding_id,
            category=self.category.value,
            severity=severity,
            title=title,
            description=description,
            file_path=file_path,
            line_number=line_number,
            evidence=evidence,
            recommendation=recommendation
        )

    def _create_metric(self, name: str, value: float, threshold: float = None, 
                      status: str = "pass", details: str = "") -> MetricResult:
        if threshold is not None:
            if value > threshold * 1.5:
                status = "fail"
            elif value > threshold:
                status = "warn"
        return MetricResult(name=name, value=value, threshold=threshold, status=status, details=details)