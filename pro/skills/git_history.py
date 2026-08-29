"""
Enhanced Git History Skill with advanced metrics, churn analysis, and team insights.
"""
import subprocess
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from pro.config.loader import get_config
from pro.cache.manager import AnalysisCache


@dataclass
class GitHistoryFinding:
    id: str
    category: str
    severity: str
    title: str
    description: str
    file_path: Optional[str]
    line_start: Optional[int]
    line_end: Optional[int]
    metric_value: float
    threshold: float
    recommendation: str


class GitHistorySkill:
    def __init__(self, cache: AnalysisCache = None):
        self.cache = cache
        self.config = get_config().analysis.git_history

    def analyze(self, repo_path: str, file_contents: Dict[str, str]) -> Dict[str, Any]:
        config = self.config
        cache_key = "git_history_skill"

        if self.cache:
            cached = self.cache.get(repo_path, cache_key, config, file_contents)
            if cached:
                return cached

        findings = []
        metrics = {}

        try:
            # Get commit data
            commits = self._get_commits(repo_path)
            file_changes = self._get_file_changes(repo_path)
            authors = self._get_authors(repo_path)
            
            metrics.update({
                "total_commits": len(commits),
                "unique_authors": len(authors),
                "first_commit_date": commits[-1]['date'] if commits else None,
                "last_commit_date": commits[0]['date'] if commits else None
            })

            # Recent activity (30 days)
            recent_cutoff = datetime.now() - timedelta(days=30)
            recent_commits = [c for c in commits if self._parse_date(c['date']) >= recent_cutoff]
            recent_authors = set(c['author'] for c in recent_commits)
            
            metrics.update({
                "recent_commits_30d": len(recent_commits),
                "active_authors_30d": len(recent_authors)
            })

            # Bus factor
            if len(authors) < config.get('min_authors', 2):
                findings.append(GitHistoryFinding(
                    id="bus_factor_low",
                    category="bus_factor",
                    severity="high" if len(authors) == 1 else "medium",
                    title=f"Bus factor risk: {len(authors)} author(s)",
                    description=f"Only {len(authors)} contributor(s) to the repository",
                    file_path=None,
                    line_start=None,
                    line_end=None,
                    metric_value=len(authors),
                    threshold=config.get('min_authors', 2),
                    recommendation="Ensure knowledge sharing; document critical components; add contributors"
                ))

            # Hotspot analysis
            hotspots = Counter(file_changes).most_common(20)
            metrics["top_hotspots"] = dict(hotspots[:10])
            
            if hotspots:
                top_file, top_changes = hotspots[0]
                if top_changes > config.get('hotspot_threshold', 20):
                    findings.append(GitHistoryFinding(
                        id=f"hotspot_{top_file.replace('/', '_')}",
                        category="code_churn",
                        severity="medium" if top_changes > 50 else "low",
                        title=f"High churn file: {top_file}",
                        description=f"File modified {top_changes} times in history",
                        file_path=top_file,
                        line_start=None,
                        line_end=None,
                        metric_value=top_changes,
                        threshold=config.get('hotspot_threshold', 20),
                        recommendation="Consider refactoring frequently changed files to reduce complexity"
                    ))

            # Fix commit ratio
            fix_keywords = ['fix', 'bug', 'hotfix', 'patch', 'defect', 'issue']
            fix_commits = [c for c in commits if any(kw in c['message'].lower() for kw in fix_keywords)]
            fix_ratio = len(fix_commits) / max(len(commits), 1)
            metrics["fix_commit_ratio"] = round(fix_ratio * 100, 1)
            
            if fix_ratio > config.get('max_fix_commit_ratio', 0.2):
                findings.append(GitHistoryFinding(
                    id="high_fix_ratio",
                    category="fix_commit_ratio",
                    severity="medium",
                    title=f"High fix commit ratio: {fix_ratio*100:.1f}%",
                    description=f"{len(fix_commits)} of {len(commits)} commits are fixes",
                    file_path=None,
                    line_start=None,
                    line_end=None,
                    metric_value=fix_ratio * 100,
                    threshold=config.get('max_fix_commit_ratio', 0.2) * 100,
                    recommendation="Investigate root causes; improve testing and code review"
                ))

            # Large commits
            large_commits = [c for c in commits if c.get('files_changed', 0) > 20]
            metrics["large_commits_count"] = len(large_commits)
            
            if large_commits:
                findings.append(GitHistoryFinding(
                    id="large_commits",
                    category="commit_size",
                    severity="low",
                    title=f"Large commits detected: {len(large_commits)}",
                    description=f"{len(large_commits)} commits with >20 files changed",
                    file_path=None,
                    line_start=None,
                    line_end=None,
                    metric_value=len(large_commits),
                    threshold=10,
                    recommendation="Prefer smaller, focused commits for better reviewability"
                ))

            # Commit frequency
            if len(commits) > 1:
                first = self._parse_date(commits[-1]['date'])
                last = self._parse_date(commits[0]['date'])
                days = (last - first).days
                if days > 0:
                    commits_per_week = len(commits) / (days / 7)
                    metrics["commits_per_week"] = round(commits_per_week, 1)

            # Author distribution
            author_commits = Counter(c['author'] for c in commits)
            metrics["author_distribution"] = dict(author_commits)
            
            # Bus factor by commits (how many authors for 80% of commits)
            sorted_authors = author_commits.most_common()
            cumulative = 0
            bus_factor_80 = 0
            for author, count in sorted_authors:
                cumulative += count
                bus_factor_80 += 1
                if cumulative >= len(commits) * 0.8:
                    break
            metrics["bus_factor_80"] = bus_factor_80

            # Merge commits
            merge_commits = [c for c in commits if c.get('is_merge', False)]
            metrics["merge_commits"] = len(merge_commits)
            metrics["merge_ratio"] = round(len(merge_commits) / max(len(commits), 1) * 100, 1)

            # Time-based patterns
            commits_by_hour = Counter(self._parse_date(c['date']).hour for c in commits)
            metrics["commits_by_hour"] = dict(commits_by_hour)
            
            commits_by_weekday = Counter(self._parse_date(c['date']).weekday() for c in commits)
            metrics["commits_by_weekday"] = dict(commits_by_weekday)

        except Exception as e:
            metrics["error"] = str(e)

        result = {
            "findings": [f.__dict__ for f in findings],
            "metrics": [{"name": k, "value": v} for k, v in metrics.items()],
            "score": self._calculate_score(findings, metrics)
        }

        if self.cache:
            self.cache.set(repo_path, cache_key, config, file_contents, result)

        return result

    def _get_commits(self, repo_path: str, limit: int = 500) -> List[Dict]:
        try:
            result = subprocess.run([
                'git', 'log', 
                f'--pretty=format:%H|%an|%ae|%ad|%s|%P',
                '--date=iso-strict',
                f'-n', str(limit)
            ], cwd=repo_path, capture_output=True, text=True, timeout=30)
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('|', 5)
                if len(parts) >= 5:
                    # Check if merge commit (has multiple parents)
                    parents = parts[5].split() if len(parts) > 5 else []
                    is_merge = len(parents) > 1
                    
                    commits.append({
                        'hash': parts[0],
                        'author': parts[1],
                        'email': parts[2],
                        'date': parts[3],
                        'message': parts[4],
                        'is_merge': is_merge,
                        'files_changed': 0  # Will be filled by _get_file_changes
                    })
            return commits
        except Exception:
            return []

    def _get_file_changes(self, repo_path: str, limit: int = 200) -> List[str]:
        try:
            result = subprocess.run([
                'git', 'log', 
                '--pretty=format:',
                '--name-only',
                f'-n', str(limit)
            ], cwd=repo_path, capture_output=True, text=True, timeout=30)
            
            files = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    files.append(line.strip())
            return files
        except Exception:
            return []

    def _get_authors(self, repo_path: str) -> Dict[str, int]:
        try:
            result = subprocess.run([
                'git', 'shortlog', '-sn', '-n', '20'
            ], cwd=repo_path, capture_output=True, text=True, timeout=30)
            
            authors = {}
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.strip().split('\t', 1)
                    if len(parts) == 2:
                        authors[parts[1]] = int(parts[0])
            return authors
        except Exception:
            return {}

    def _parse_date(self, date_str: str) -> datetime:
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except Exception:
            return datetime.now()

    def _calculate_score(self, findings: List[GitHistoryFinding], metrics: Dict) -> float:
        score = 50.0  # Base score

        # Author diversity
        authors = metrics.get("unique_authors", 0)
        score += min(20, authors * 5)

        # Recent activity
        recent = metrics.get("recent_commits_30d", 0)
        score += min(15, recent * 0.5)

        # Fix ratio penalty
        fix_ratio = metrics.get("fix_commit_ratio", 0)
        score -= fix_ratio * 0.5

        # Large commits penalty
        large = metrics.get("large_commits_count", 0)
        score -= large * 2

        # Hotspot penalty
        hotspots = metrics.get("top_hotspots", {})
        if hotspots:
            top_changes = max(hotspots.values())
            score -= min(10, top_changes / 5)

        # Merge ratio bonus (shows collaboration)
        merge_ratio = metrics.get("merge_ratio", 0)
        if merge_ratio > 10:
            score += 5

        # Bus factor 80
        bf80 = metrics.get("bus_factor_80", 1)
        if bf80 >= 3:
            score += 10
        elif bf80 >= 2:
            score += 5

        # Findings penalties
        for f in findings:
            if f.severity == "high":
                score -= 10
            elif f.severity == "medium":
                score -= 5
            elif f.severity == "low":
                score -= 2

        return max(0, min(100, round(score, 1)))