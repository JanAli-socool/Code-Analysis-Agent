"""
GitHub App Integration for PR Annotations and Status Checks.
Provides PR comments, inline annotations, and commit status updates.
"""
import json
import os
import base64
import hmac
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import jwt
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class CheckStatus(Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class CheckConclusion(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    NEUTRAL = "neutral"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    TIMED_OUT = "timed_out"
    ACTION_REQUIRED = "action_required"


class AnnotationLevel(Enum):
    NOTICE = "notice"
    WARNING = "warning"
    FAILURE = "failure"


@dataclass
class GitHubAppConfig:
    app_id: str
    private_key_path: str
    webhook_secret: str
    installation_id: Optional[str] = None


@dataclass
class CheckRun:
    name: str
    head_sha: str
    status: CheckStatus = CheckStatus.IN_PROGRESS
    conclusion: Optional[CheckConclusion] = None
    output_title: str = "Code Analysis"
    output_summary: str = ""
    output_text: str = ""
    annotations: List[Dict[str, Any]] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    completed_at: Optional[str] = None
    external_id: Optional[str] = None


@dataclass
class PRAnnotation:
    path: str
    start_line: int
    end_line: int
    start_column: Optional[int] = None
    end_column: Optional[int] = None
    annotation_level: AnnotationLevel = AnnotationLevel.WARNING
    message: str = ""
    title: Optional[str] = None
    raw_details: Optional[str] = None


class GitHubAppClient:
    """GitHub App client for authentication and API calls."""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, config: GitHubAppConfig):
        self.config = config
        self._private_key = None
        self._installation_token: Optional[str] = None
        self._token_expires_at: float = 0
        self._load_private_key()
    
    def _load_private_key(self) -> None:
        """Load the GitHub App private key."""
        try:
            with open(self.config.private_key_path, "rb") as f:
                self._private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None
                )
        except Exception as e:
            raise ValueError(f"Failed to load private key: {e}")
    
    def _generate_jwt(self) -> str:
        """Generate a JWT for GitHub App authentication."""
        now = int(time.time())
        payload = {
            "iat": now - 60,  # Issued 60 seconds ago
            "exp": now + 600,  # Expires in 10 minutes
            "iss": self.config.app_id
        }
        return jwt.encode(payload, self._private_key, algorithm="RS256")
    
    def get_installation_token(self, installation_id: Optional[str] = None) -> str:
        """Get an installation access token."""
        if self._installation_token and time.time() < self._token_expires_at - 60:
            return self._installation_token
        
        inst_id = installation_id or self.config.installation_id
        if not inst_id:
            raise ValueError("Installation ID required")
        
        jwt_token = self._generate_jwt()
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        response = requests.post(
            f"{self.BASE_URL}/app/installations/{inst_id}/access_tokens",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        self._installation_token = data["token"]
        self._token_expires_at = time.time() + 3600  # 1 hour
        
        return self._installation_token
    
    def _get_headers(self, installation_id: Optional[str] = None) -> Dict[str, str]:
        """Get headers with installation token."""
        token = self.get_installation_token(installation_id)
        return {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
    
    def create_check_run(
        self,
        owner: str,
        repo: str,
        check_run: CheckRun,
        installation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a check run."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/check-runs"
        
        payload = {
            "name": check_run.name,
            "head_sha": check_run.head_sha,
            "status": check_run.status.value,
            "output": {
                "title": check_run.output_title,
                "summary": check_run.output_summary,
                "text": check_run.output_text,
                "annotations": check_run.annotations[:50]  # GitHub limit: 50 per request
            }
        }
        
        if check_run.conclusion:
            payload["conclusion"] = check_run.conclusion.value
            payload["completed_at"] = check_run.completed_at or datetime.utcnow().isoformat() + "Z"
        
        if check_run.external_id:
            payload["external_id"] = check_run.external_id
        
        response = requests.post(
            url,
            headers=self._get_headers(installation_id),
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    
    def update_check_run(
        self,
        owner: str,
        repo: str,
        check_run_id: int,
        check_run: CheckRun,
        installation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update an existing check run."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/check-runs/{check_run_id}"
        
        payload = {
            "name": check_run.name,
            "status": check_run.status.value,
            "output": {
                "title": check_run.output_title,
                "summary": check_run.output_summary,
                "text": check_run.output_text,
                "annotations": check_run.annotations[:50]
            }
        }
        
        if check_run.conclusion:
            payload["conclusion"] = check_run.conclusion.value
            payload["completed_at"] = check_run.completed_at or datetime.utcnow().isoformat() + "Z"
        
        response = requests.patch(
            url,
            headers=self._get_headers(installation_id),
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    
    def create_pr_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
        installation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a comment on a PR."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/issues/{pr_number}/comments"
        
        response = requests.post(
            url,
            headers=self._get_headers(installation_id),
            json={"body": body},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    
    def create_review_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        commit_sha: str,
        path: str,
        line: int,
        body: str,
        installation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a review comment on a specific line in a PR."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}/comments"
        
        response = requests.post(
            url,
            headers=self._get_headers(installation_id),
            json={
                "body": body,
                "commit_id": commit_sha,
                "path": path,
                "line": line,
                "side": "RIGHT"
            },
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    
    def create_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        commit_sha: str,
        body: str,
        event: str = "COMMENT",
        comments: List[Dict[str, Any]] = None,
        installation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a PR review with inline comments."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        
        payload = {
            "commit_id": commit_sha,
            "body": body,
            "event": event
        }
        
        if comments:
            payload["comments"] = comments
        
        response = requests.post(
            url,
            headers=self._get_headers(installation_id),
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    
    def get_pr_files(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        installation_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get files changed in a PR."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}/files"
        
        response = requests.get(
            url,
            headers=self._get_headers(installation_id),
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    
    def get_commit_status(
        self,
        owner: str,
        repo: str,
        sha: str,
        installation_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get status checks for a commit."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/commits/{sha}/check-runs"
        
        response = requests.get(
            url,
            headers=self._get_headers(installation_id),
            timeout=10
        )
        response.raise_for_status()
        return response.json().get("check_runs", [])


class GitHubAnnotations:
    """Helper to convert analysis findings to GitHub annotations."""
    
    @staticmethod
    def findings_to_annotations(
        findings: List[Dict[str, Any]],
        repo_root: str = ""
    ) -> List[PRAnnotation]:
        """Convert analysis findings to GitHub annotations."""
        annotations = []
        
        for finding in findings:
            file_path = finding.get("file_path", "")
            if not file_path:
                continue
            
            # Make path relative to repo root
            if repo_root and file_path.startswith(repo_root):
                file_path = file_path[len(repo_root):].lstrip("/")
            
            line_start = finding.get("line_start", 1)
            line_end = finding.get("line_end", line_start)
            
            # Map severity to annotation level
            severity = finding.get("severity", "medium").lower()
            if severity == "critical":
                level = AnnotationLevel.FAILURE
            elif severity == "high":
                level = AnnotationLevel.FAILURE
            elif severity == "medium":
                level = AnnotationLevel.WARNING
            else:
                level = AnnotationLevel.NOTICE
            
            annotation = PRAnnotation(
                path=file_path,
                start_line=max(1, line_start),
                end_line=max(line_start, line_end),
                start_column=finding.get("column_start"),
                end_column=finding.get("column_end"),
                annotation_level=level,
                message=finding.get("message", finding.get("description", ""))[:65535],
                title=finding.get("title"),
                raw_details=finding.get("recommendation")
            )
            annotations.append(annotation)
        
        return annotations
    
    @staticmethod
    def annotations_to_github_format(annotations: List[PRAnnotation]) -> List[Dict[str, Any]]:
        """Convert PRAnnotation objects to GitHub API format."""
        return [
            {
                "path": a.path,
                "start_line": a.start_line,
                "end_line": a.end_line,
                "start_column": a.start_column,
                "end_column": a.end_column,
                "annotation_level": a.annotation_level.value,
                "message": a.message,
                "title": a.title,
                "raw_details": a.raw_details
            }
            for a in annotations
        ]


class GitHubPRReporter:
    """High-level reporter for PR analysis results."""
    
    def __init__(self, client: GitHubAppClient):
        self.client = client
    
    def report_analysis(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        commit_sha: str,
        analysis_result: Dict[str, Any],
        installation_id: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """Report full analysis results to PR."""
        # Convert findings to annotations
        all_findings = []
        for cat in analysis_result.get("category_scores", []):
            for finding in cat.get("findings", []):
                finding_copy = finding.copy()
                finding_copy["category"] = cat.get("name", "unknown")
                all_findings.append(finding_copy)
        
        annotations = GitHubAnnotations.findings_to_annotations(all_findings)
        github_annotations = GitHubAnnotations.annotations_to_github_format(annotations)
        
        # Create check run
        check_run = CheckRun(
            name="Code Analysis",
            head_sha=commit_sha,
            status=CheckStatus.COMPLETED,
            conclusion=CheckConclusion.SUCCESS if analysis_result.get("risk_level", "").lower() != "critical" else CheckConclusion.FAILURE,
            output_title="Code Analysis Report",
            output_summary=self._generate_summary(analysis_result),
            output_text=self._generate_details(analysis_result),
            annotations=github_annotations[:50],
            completed_at=datetime.utcnow().isoformat() + "Z"
        )
        
        check_result = self.client.create_check_run(owner, repo, check_run, installation_id)
        
        # Create PR comment with summary
        comment_body = self._generate_pr_comment(analysis_result)
        comment_result = self.client.create_pr_comment(owner, repo, pr_number, comment_body, installation_id)
        
        return check_result["id"], check_result
    
    def _generate_summary(self, result: Dict[str, Any]) -> str:
        score = result.get("overall_score", 0)
        risk = result.get("risk_level", "unknown")
        return f"Score: {score}/100 | Risk: {risk.upper()} | {result.get('files_analyzed', 0)} files analyzed"
    
    def _generate_details(self, result: Dict[str, Any]) -> str:
        lines = ["## Category Scores"]
        for cat in result.get("category_scores", []):
            status = "✅" if cat.get("score", 0) >= 80 else "⚠️" if cat.get("score", 0) >= 60 else "❌"
            lines.append(f"- {status} **{cat.get('name', '').title()}**: {cat.get('score', 0)}/100")
        
        if result.get("strengths"):
            lines.append("\n## Strengths")
            for s in result["strengths"]:
                lines.append(f"- {s}")
        
        if result.get("weaknesses"):
            lines.append("\n## Weaknesses")
            for w in result["weaknesses"]:
                lines.append(f"- {w}")
        
        return "\n".join(lines)
    
    def _generate_pr_comment(self, result: Dict[str, Any]) -> str:
        score = result.get("overall_score", 0)
        risk = result.get("risk_level", "unknown")
        
        emoji = "🟢" if score >= 80 else "🟡" if score >= 60 else "🔴"
        
        body = f"""## {emoji} Code Analysis Report

**Overall Score:** {score}/100  
**Risk Level:** {risk.upper()}  
**Files Analyzed:** {result.get('files_analyzed', 0)}  
**Total Lines:** {result.get('total_lines', 0)}

### Category Scores
"""
        for cat in result.get("category_scores", []):
            status = "✅" if cat.get("score", 0) >= 80 else "⚠️" if cat.get("score", 0) >= 60 else "❌"
            body += f"- {status} **{cat.get('name', '').title()}**: {cat.get('score', 0)}/100\n"
        
        if result.get("strengths"):
            body += "\n### ✅ Strengths\n"
            for s in result["strengths"]:
                body += f"- {s}\n"
        
        if result.get("weaknesses"):
            body += "\n### ⚠️ Weaknesses\n"
            for w in result["weaknesses"]:
                body += f"- {w}\n"
        
        body += "\n---\n*Generated by Code Analysis Agent*"
        return body


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook signature."""
    expected = "sha256=" + hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def parse_webhook_event(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parse relevant info from webhook payload."""
    if payload.get("action") not in ("opened", "synchronize", "reopened"):
        return None
    
    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {})
    
    return {
        "action": payload["action"],
        "pr_number": pr.get("number"),
        "pr_title": pr.get("title"),
        "commit_sha": pr.get("head", {}).get("sha"),
        "base_sha": pr.get("base", {}).get("sha"),
        "repo_owner": repo.get("owner", {}).get("login"),
        "repo_name": repo.get("name"),
        "repo_full_name": repo.get("full_name"),
        "installation_id": payload.get("installation", {}).get("id")
    }


if __name__ == "__main__":
    import sys
    print("GitHub App Integration Module")
    print("Usage: Import and use GitHubAppClient, GitHubAppClient, GitHubPRReporter")