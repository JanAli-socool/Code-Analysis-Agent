"""
Security Analysis Skill - Uses bandit for security vulnerability detection
"""
import json
import subprocess
import tempfile
import os
from typing import List
from advanced.skills.base import BaseSkill
from advanced.models import AgentContext, CategoryScore, AnalysisCategory, Finding, Severity, MetricResult


class SecuritySkill(BaseSkill):
    def __init__(self):
        super().__init__("Security Analysis", AnalysisCategory.SECURITY, weight=2.0)

    def analyze(self, context: AgentContext) -> CategoryScore:
        findings = []
        metrics = []

        repo_path = context.repository_path
        
        try:
            result = subprocess.run(
                ['python', '-m', 'bandit', '-r', repo_path, '-f', 'json', '-ll'],
                capture_output=True,
                text=True,
                timeout=60
            )
            bandit_results = json.loads(result.stdout) if result.stdout else {"results": []}
        except Exception as e:
            bandit_results = {"results": [], "error": str(e)}

        severity_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        confidence_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}

        for item in bandit_results.get("results", []):
            severity = item.get("issue_severity", "LOW")
            confidence = item.get("issue_confidence", "LOW")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            confidence_counts[confidence] = confidence_counts.get(confidence, 0) + 1

            findings.append(self._create_finding(
                finding_id=f"security_{item.get('file_path', 'unknown')}_{item.get('line_number', 0)}",
                severity=Severity(severity.lower()),
                title=f"Security issue: {item.get('test_name', 'Unknown')}",
                description=item.get("issue_text", ""),
                file_path=item.get("file_path"),
                line_number=item.get("line_number"),
                evidence=f"Code: {item.get('code', '')}\nConfidence: {confidence}",
                recommendation=item.get("more_info", "Review and remediate this security issue")
            ))

        total_issues = sum(severity_counts.values())
        critical_weight = severity_counts.get("HIGH", 0) * 3 + severity_counts.get("MEDIUM", 0) * 2 + severity_counts.get("LOW", 0)

        metrics.extend([
            self._create_metric("total_security_issues", float(total_issues), threshold=0),
            self._create_metric("high_severity_issues", float(severity_counts.get("HIGH", 0)), threshold=0),
            self._create_metric("medium_severity_issues", float(severity_counts.get("MEDIUM", 0)), threshold=5),
            self._create_metric("low_severity_issues", float(severity_counts.get("LOW", 0)), threshold=10),
            self._create_metric("high_confidence_issues", float(confidence_counts.get("HIGH", 0)), threshold=0)
        ])

        score = 100
        score -= severity_counts.get("HIGH", 0) * 15
        score -= severity_counts.get("MEDIUM", 0) * 8
        score -= severity_counts.get("LOW", 0) * 2
        score = max(0, min(100, score))

        return CategoryScore(
            category=self.category,
            score=score,
            weight=self.weight,
            findings=findings,
            metrics=metrics
        )