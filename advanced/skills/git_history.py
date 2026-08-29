"""
Git History Analysis Skill - Commit patterns, churn, bus factor, hotspots
"""
import subprocess
import json
from collections import Counter
from datetime import datetime, timedelta
from typing import List, Dict
from advanced.skills.base import BaseSkill
from advanced.models import AgentContext, CategoryScore, AnalysisCategory, Finding, Severity, MetricResult


class GitHistorySkill(BaseSkill):
    def __init__(self):
        super().__init__("Git History Analysis", AnalysisCategory.GIT_HISTORY, weight=1.0)

    def analyze(self, context: AgentContext) -> CategoryScore:
        findings = []
        metrics = []

        try:
            repo_root = context.repository_path
            
            result = subprocess.run(
                ['git', 'log', '--pretty=format:%H|%an|%ae|%ad|%s', '--date=short', '-n', '500'],
                cwd=repo_root, capture_output=True, text=True, timeout=30
            )
            commits = self._parse_commits(result.stdout)

            result = subprocess.run(
                ['git', 'log', '--pretty=format:', '--name-only', '-n', '200'],
                cwd=repo_root, capture_output=True, text=True, timeout=30
            )
            file_changes = self._parse_file_changes(result.stdout)

            result = subprocess.run(
                ['git', 'shortlog', '-sn', '-n', '20'],
                cwd=repo_root, capture_output=True, text=True, timeout=30
            )
            authors = self._parse_authors(result.stdout)

        except Exception as e:
            findings.append(self._create_finding(
                finding_id="git_error",
                severity=Severity.LOW,
                title="Git analysis failed",
                description=str(e),
                recommendation="Ensure repository has git history"
            ))
            return CategoryScore(
                category=self.category,
                score=50,
                weight=self.weight,
                findings=findings,
                metrics=[]
            )

        total_commits = len(commits)
        unique_authors = len(authors)
        recent_commits = [c for c in commits if self._is_recent(c['date'], 30)]
        recent_authors = set(c['author'] for c in recent_commits)

        if unique_authors <= 1:
            findings.append(self._create_finding(
                finding_id="bus_factor",
                severity=Severity.HIGH,
                title="Bus factor risk: Single author",
                description="Only one contributor to the repository",
                evidence=f"Total authors: {unique_authors}",
                recommendation="Ensure knowledge sharing and documentation for critical components"
            ))
        elif unique_authors <= 2:
            findings.append(self._create_finding(
                finding_id="low_bus_factor",
                severity=Severity.MEDIUM,
                title="Low bus factor",
                description=f"Only {unique_authors} contributors",
                evidence=f"Authors: {', '.join(list(authors.keys())[:5])}",
                recommendation="Encourage more contributors to reduce knowledge silos"
            ))

        hotspots = Counter(file_changes).most_common(10)
        for file_path, changes in hotspots:
            if changes > 20:
                findings.append(self._create_finding(
                    finding_id=f"hotspot_{file_path.replace('/', '_')}",
                    severity=Severity.MEDIUM if changes > 50 else Severity.LOW,
                    title=f"High churn file: {file_path}",
                    description=f"File modified {changes} times in recent history",
                    evidence=f"Changes: {changes}",
                    recommendation="Consider refactoring frequently changed files to reduce complexity"
                ))

        large_commits = [c for c in commits if c.get('files_changed', 0) > 20]
        if large_commits:
            findings.append(self._create_finding(
                finding_id="large_commits",
                severity=Severity.LOW,
                title="Large commits detected",
                description=f"{len(large_commits)} commits with >20 files changed",
                recommendation="Prefer smaller, focused commits for better reviewability"
            ))

        fix_commits = [c for c in commits if any(kw in c['message'].lower() for kw in ['fix', 'bug', 'hotfix', 'patch'])]
        fix_ratio = len(fix_commits) / max(total_commits, 1)

        metrics.extend([
            self._create_metric("total_commits", float(total_commits)),
            self._create_metric("unique_authors", float(unique_authors)),
            self._create_metric("recent_commits_30d", float(len(recent_commits))),
            self._create_metric("active_authors_30d", float(len(recent_authors))),
            self._create_metric("top_hotspot_changes", float(hotspots[0][1]) if hotspots else 0, threshold=30),
            self._create_metric("fix_commit_ratio", fix_ratio * 100, threshold=20),
            self._create_metric("large_commits_count", float(len(large_commits)), threshold=10)
        ])

        score = 50
        score += min(20, unique_authors * 5)
        score += min(15, len(recent_commits) * 0.5)
        score -= len(hotspots) * 1
        score -= fix_ratio * 50
        score -= len(large_commits) * 2
        score = max(0, min(100, score))

        return CategoryScore(
            category=self.category,
            score=score,
            weight=self.weight,
            findings=findings,
            metrics=metrics
        )

    def _parse_commits(self, output: str) -> List[Dict]:
        commits = []
        for line in output.strip().split('\n'):
            if not line:
                continue
            parts = line.split('|', 4)
            if len(parts) >= 5:
                commits.append({
                    'hash': parts[0],
                    'author': parts[1],
                    'email': parts[2],
                    'date': parts[3],
                    'message': parts[4],
                    'files_changed': 0
                })
        return commits

    def _parse_file_changes(self, output: str) -> List[str]:
        files = []
        for line in output.strip().split('\n'):
            if line.strip():
                files.append(line.strip())
        return files

    def _parse_authors(self, output: str) -> Dict[str, int]:
        authors = {}
        for line in output.strip().split('\n'):
            if line.strip():
                parts = line.strip().split('\t', 1)
                if len(parts) == 2:
                    authors[parts[1]] = int(parts[0])
        return authors

    def _is_recent(self, date_str: str, days: int) -> bool:
        try:
            commit_date = datetime.strptime(date_str, '%Y-%m-%d')
            return (datetime.now() - commit_date).days <= days
        except Exception:
            return False