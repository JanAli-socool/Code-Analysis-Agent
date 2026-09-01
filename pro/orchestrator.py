"""
Professional Orchestrator with async parallel execution, caching, and comprehensive reporting.
"""
import asyncio
import json
import os
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

from pro.config.loader import get_config, AppConfig
from pro.cache.manager import AnalysisCache
from pro.execution.async_runner import AsyncSkillRunner, SkillResult as AsyncSkillResult
from pro.skills.complexity import ComplexitySkill
from pro.skills.security import SecuritySkill
from pro.skills.testing import TestingSkill
from pro.skills.architecture import ArchitectureSkill
from pro.skills.dependencies import DependenciesSkill
from pro.skills.maintainability import MaintainabilitySkill
from pro.skills.documentation import DocumentationSkill
from pro.skills.git_history import GitHistorySkill
from pro.languages.detector import get_detector, Language
from pro.languages.javascript import JavaScriptSkill
from pro.languages.java import JavaSkill
from pro.languages.go import GoSkill
from pro.languages.cpp import CppSkill


@dataclass
class SkillResult:
    name: str
    category: str
    score: float
    weight: float
    findings: List[Dict]
    metrics: List[Dict]
    duration_ms: float
    error: Optional[str] = None


@dataclass
class AnalysisResult:
    repository_path: str
    analyzed_at: str
    overall_score: float
    risk_level: str
    category_scores: List[SkillResult]
    summary: str
    strengths: List[str]
    weaknesses: List[str]
    files_analyzed: int
    total_lines: int
    total_duration_ms: float
    config_hash: str


class ProfessionalOrchestrator:
    def __init__(self, repo_path: str, config: AppConfig = None):
        self.repo_path = Path(repo_path).resolve()
        self.config = config or get_config()
        self.logger = self._setup_logger()
        
        # Initialize cache
        cache_dir = self.config.execution.cache_dir
        if not Path(cache_dir).is_absolute():
            cache_dir = self.repo_path / cache_dir
        self.cache = AnalysisCache(str(cache_dir), self.config.execution.cache_ttl_hours) if self.config.execution.cache_enabled else None

        # Initialize skills with weights from config
        weights = self.config.analysis.weights
        self.skills = [
            ("complexity", ComplexitySkill(self.cache), weights.get("complexity", 2.0)),
            ("security", SecuritySkill(self.cache), weights.get("security", 3.0)),
            ("testing", TestingSkill(self.cache), weights.get("testing", 2.0)),
            ("architecture", ArchitectureSkill(self.cache), weights.get("architecture", 2.0)),
            ("maintainability", MaintainabilitySkill(self.cache), weights.get("maintainability", 1.5)),
            ("dependencies", DependenciesSkill(self.cache), weights.get("dependencies", 1.0)),
            ("documentation", DocumentationSkill(self.cache), weights.get("documentation", 0.5)),
            ("git_history", GitHistorySkill(self.cache), weights.get("git_history", 0.5)),
            # Language-specific skills
            ("javascript", JavaScriptSkill(self.cache), weights.get("javascript", 1.5)),
            ("java", JavaSkill(self.cache), weights.get("java", 1.5)),
            ("go", GoSkill(self.cache), weights.get("go", 1.5)),
            ("cpp", CppSkill(self.cache), weights.get("cpp", 1.5)),
        ]

        # Language detector
        self.language_detector = get_detector()

        self.file_contents: Dict[str, str] = {}
        self._config_hash = self._compute_config_hash()

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger("code_analysis")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def _compute_config_hash(self) -> str:
        """Compute hash of relevant configuration for cache invalidation."""
        config_data = {
            "weights": self.config.analysis.weights,
            "thresholds": {
                k: v for k, v in self.config.analysis.__dict__.items() 
                if k not in ['weights', 'risk_thresholds']
            }
        }
        return hashlib.sha256(json.dumps(config_data, sort_keys=True).encode()).hexdigest()[:16]

    def load_repository(self) -> Dict[str, str]:
        """Load all relevant files from repository."""
        self.logger.info(f"Loading repository: {self.repo_path}")
        
        include_patterns = self.config.execution.include_patterns
        exclude_patterns = self.config.execution.exclude_patterns
        
        def should_include(path: Path) -> bool:
            rel = path.relative_to(self.repo_path)
            rel_str = str(rel)
            
            # Check exclude patterns first
            for pattern in exclude_patterns:
                if pattern in rel_str or rel.match(pattern):
                    return False
            
            # Check include patterns
            for pattern in include_patterns:
                if rel.match(pattern) or path.name == pattern:
                    return True
            
            return False

        file_contents = {}
        for file_path in self.repo_path.rglob('*'):
            if file_path.is_file() and should_include(file_path):
                try:
                    relative = file_path.relative_to(self.repo_path)
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    file_contents[str(relative)] = content
                except Exception as e:
                    self.logger.warning(f"Failed to read {file_path}: {e}")

        self.file_contents = file_contents
        self.logger.info(f"Loaded {len(file_contents)} files")
        return file_contents

    def run_analysis(self) -> AnalysisResult:
        """Run complete analysis with parallel skill execution."""
        start_time = time.time()
        
        if not self.file_contents:
            self.load_repository()

        self.logger.info("Starting parallel skill execution")

        # Run skills in parallel
        category_scores = self._run_skills_parallel()

        # Calculate overall score
        overall_score = self._calculate_overall_score(category_scores)
        risk_level = self._determine_risk_level(overall_score, category_scores)
        summary, strengths, weaknesses = self._generate_summary(category_scores)

        total_duration = (time.time() - start_time) * 1000

        result = AnalysisResult(
            repository_path=str(self.repo_path),
            analyzed_at=datetime.now().isoformat(),
            overall_score=overall_score,
            risk_level=risk_level,
            category_scores=category_scores,
            summary=summary,
            strengths=strengths,
            weaknesses=weaknesses,
            files_analyzed=len([f for f in self.file_contents if f.endswith('.py')]),
            total_lines=sum(len(c.split('\n')) for c in self.file_contents.values()),
            total_duration_ms=round(total_duration, 1),
            config_hash=self._config_hash
        )

        self.logger.info(f"Analysis complete: {overall_score}/100 ({risk_level}) in {total_duration:.0f}ms")
        return result

    def _run_skills_parallel(self) -> List[SkillResult]:
        """Execute all skills in parallel using async runner with timeout handling."""
        exec_config = self.config.execution
        
        # Convert skills to format expected by async runner
        skills = [(name, skill, weight) for name, skill, weight in self.skills]
        
        if exec_config.parallel and len(self.skills) > 1:
            # Run async skills
            runner = AsyncSkillRunner(
                max_concurrent=exec_config.max_workers,
                default_timeout=exec_config.timeout_per_skill
            )
            
            try:
                # Run in event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    async_results = loop.run_until_complete(
                        asyncio.wait_for(
                            runner.run_skills(skills, str(self.repo_path), self.file_contents),
                            timeout=exec_config.timeout_total
                        )
                    )
                finally:
                    loop.run_until_complete(runner.shutdown())
                    loop.close()
                
                # Convert async results to SkillResult
                results = []
                for ar in async_results:
                    results.append(SkillResult(
                        name=ar.name,
                        category=ar.category,
                        score=ar.score,
                        weight=ar.weight,
                        findings=ar.findings,
                        metrics=ar.metrics,
                        duration_ms=ar.duration_ms,
                        error=ar.error
                    ))
                return results
            except asyncio.TimeoutError:
                self.logger.error(f"Skills timed out after {exec_config.timeout_total}s")
                return self._run_skills_sequential()
            except Exception as e:
                self.logger.error(f"Async skill execution failed: {e}")
                return self._run_skills_sequential()
        else:
            return self._run_skills_sequential()

    def _run_single_skill(self, name: str, skill: Any, weight: float) -> SkillResult:
        """Run a single skill synchronously."""
        start = time.time()
        try:
            skill_result = skill.analyze(str(self.repo_path), self.file_contents)
            duration = (time.time() - start) * 1000
            
            return SkillResult(
                name=name,
                category=name,
                score=skill_result.get("score", 0.0),
                weight=weight,
                findings=skill_result.get("findings", []),
                metrics=skill_result.get("metrics", []),
                duration_ms=round(duration, 1)
            )
        except Exception as e:
            self.logger.error(f"Skill {name} failed: {e}")
            return SkillResult(
                name=name,
                category=name,
                score=0.0,
                weight=weight,
                findings=[],
                metrics=[],
                duration_ms=0,
                error=str(e)
            )

    def _run_skills_sequential(self) -> List[SkillResult]:
        """Execute all skills sequentially (fallback)."""
        results = []
        for name, skill, weight in self.skills:
            try:
                result = self._run_single_skill(name, skill, weight)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Skill {name} failed: {e}")
                results.append(SkillResult(
                    name=name,
                    category=name,
                    score=0.0,
                    weight=weight,
                    findings=[],
                    metrics=[],
                    duration_ms=0,
                    error=str(e)
                ))
        return results

    def _calculate_overall_score(self, category_scores: List[SkillResult]) -> float:
        total_weight = sum(cs.weight for cs in category_scores if cs.score > 0)
        if total_weight == 0:
            return 0.0
        weighted_sum = sum(cs.score * cs.weight for cs in category_scores if cs.score > 0)
        return round(weighted_sum / total_weight, 1)

    def _determine_risk_level(self, overall_score: float, category_scores: List[SkillResult]) -> str:
        thresholds = self.config.analysis.risk_thresholds
        
        # Check critical categories
        critical_categories = [cs for cs in category_scores 
                              if cs.category in ["security", "architecture"] 
                              and cs.score < 40]
        
        if critical_categories or overall_score < thresholds.get("critical", 35):
            return "critical"
        elif overall_score < thresholds.get("high", 55):
            return "high"
        elif overall_score < thresholds.get("medium", 75):
            return "medium"
        else:
            return "low"

    def _generate_summary(self, category_scores: List[SkillResult]) -> tuple:
        strengths = []
        weaknesses = []

        for cs in sorted(category_scores, key=lambda x: x.score, reverse=True):
            if cs.score >= 80:
                strengths.append(f"Strong {cs.category}: {cs.score}/100")
            elif cs.score < 50:
                weaknesses.append(f"Weak {cs.category}: {cs.score}/100")

        summary_parts = [
            f"Overall Score: {self._calculate_overall_score(category_scores)}/100",
            f"Analyzed {len(category_scores)} categories",
            f"Files: {len([f for f in self.file_contents if f.endswith('.py')])}",
            f"Lines: {sum(len(c.split('\n')) for c in self.file_contents.values())}"
        ]
        
        if strengths:
            summary_parts.append(f"Strengths: {', '.join(strengths[:3])}")
        if weaknesses:
            summary_parts.append(f"Weaknesses: {', '.join(weaknesses[:3])}")

        return ". ".join(summary_parts) + ".", strengths, weaknesses

    # Output methods
    def export_json(self, result: AnalysisResult, output_path: str) -> None:
        """Export full result as JSON."""
        data = {
            "repository": result.repository_path,
            "analyzed_at": result.analyzed_at,
            "overall_score": result.overall_score,
            "risk_level": result.risk_level,
            "summary": result.summary,
            "strengths": result.strengths,
            "weaknesses": result.weaknesses,
            "files_analyzed": result.files_analyzed,
            "total_lines": result.total_lines,
            "total_duration_ms": result.total_duration_ms,
            "config_hash": result.config_hash,
            "categories": []
        }

        for cs in result.category_scores:
            cat_data = {
                "category": cs.category,
                "score": cs.score,
                "weight": cs.weight,
                "duration_ms": cs.duration_ms,
                "error": cs.error,
                "findings": cs.findings,
                "metrics": cs.metrics
            }
            data["categories"].append(cat_data)

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

    def export_sarif(self, result: AnalysisResult, output_path: str) -> None:
        """Export findings as SARIF for GitHub/GitLab integration."""
        sarif = {
            "version": "2.1.0",
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "Code Analysis Agent",
                        "version": "1.0.0",
                        "informationUri": "https://github.com/code-analysis-agent",
                        "rules": []
                    }
                },
                "results": []
            }]
        }

        rule_map = {}
        rule_id_counter = 0

        for cs in result.category_scores:
            for finding in cs.findings:
                rule_key = f"{cs.category}_{finding.get('category', 'unknown')}"
                if rule_key not in rule_map:
                    rule_id_counter += 1
                    rule_map[rule_key] = f"CA{rule_id_counter:04d}"
                    sarif["runs"][0]["tool"]["driver"]["rules"].append({
                        "id": rule_map[rule_key],
                        "name": finding.get("title", "Unknown"),
                        "shortDescription": {"text": finding.get("description", "")},
                        "fullDescription": {"text": finding.get("recommendation", "")},
                        "defaultConfiguration": {"level": self._severity_to_sarif(finding.get("severity", "medium"))},
                        "properties": {"category": cs.category}
                    })

                # Create result - ensure line/column numbers are integers (not None)
                file_path = finding.get("file_path", "")
                line_start = finding.get("line_start")
                line_end = finding.get("line_end")
                col_start = finding.get("column_start")
                col_end = finding.get("column_end")
                
                # Convert None to defaults, ensure integers
                if line_start is None:
                    line_start = 1
                if line_end is None:
                    line_end = 1
                if col_start is None:
                    col_start = 1
                if col_end is None:
                    col_end = 1
                
                sarif["runs"][0]["results"].append({
                    "ruleId": rule_map[rule_key],
                    "level": self._severity_to_sarif(finding.get("severity", "medium")),
                    "message": {"text": finding.get("message", finding.get("description", ""))},
                    "locations": [{
                        "physicalLocation": {
                            "artifactLocation": {"uri": file_path} if file_path else {"uri": "."},
                            "region": {
                                "startLine": int(line_start),
                                "endLine": int(line_end),
                                "startColumn": int(col_start),
                                "endColumn": int(col_end)
                            }
                        }
                    }],
                    "properties": {
                        "category": cs.category,
                        "metric_value": finding.get("metric_value"),
                        "threshold": finding.get("threshold"),
                        "recommendation": finding.get("recommendation", "")
                    }
                })

        with open(output_path, 'w') as f:
            json.dump(sarif, f, indent=2)

    def _severity_to_sarif(self, severity: str) -> str:
        mapping = {
            "critical": "error",
            "high": "error",
            "medium": "warning",
            "low": "note",
            "info": "none"
        }
        return mapping.get(severity.lower(), "warning")

    def export_markdown(self, result: AnalysisResult, output_path: str) -> None:
        """Export human-readable markdown report."""
        lines = [
            f"# Code Analysis Report",
            f"",
            f"**Repository:** {result.repository_path}",
            f"**Analyzed:** {result.analyzed_at}",
            f"**Overall Score:** {result.overall_score}/100",
            f"**Risk Level:** {result.risk_level.upper()}",
            f"**Duration:** {result.total_duration_ms:.0f}ms",
            f"",
            f"## Summary",
            f"{result.summary}",
            f"",
            f"## Category Scores",
            f""
        ]

        for cs in sorted(result.category_scores, key=lambda x: x.score):
            status = "[OK]" if cs.score >= 70 else "[WARN]" if cs.score >= 40 else "[FAIL]"
            lines.append(f"| {status} | {cs.category:20s} | {cs.score:5.1f}/100 | Weight: {cs.weight} | {cs.duration_ms:.0f}ms |")

        lines.extend([
            f"",
            f"## Strengths",
            f""
        ])
        for s in result.strengths:
            lines.append(f"- {s}")

        lines.extend([
            f"",
            f"## Weaknesses",
            f""
        ])
        for w in result.weaknesses:
            lines.append(f"- {w}")

        # Critical/High findings
        critical_findings = []
        for cs in result.category_scores:
            for f in cs.findings:
                if f.get("severity") in ["critical", "high"]:
                    critical_findings.append((cs.category, f))

        if critical_findings:
            lines.extend([
                f"",
                f"## Critical/High Findings ({len(critical_findings)})",
                f""
            ])
            for cat, f in critical_findings[:20]:
                loc = f"{f.get('file_path', 'N/A')}:{f.get('line_start', 'N/A')}"
                lines.append(f"### [{f.get('severity', '').upper()}] {f.get('title', 'Unknown')} ({cat})")
                lines.append(f"**Location:** {loc}")
                lines.append(f"**Description:** {f.get('description', 'N/A')}")
                lines.append(f"**Recommendation:** {f.get('recommendation', 'N/A')}")
                lines.append(f"")

        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))

    def export_html(self, result: AnalysisResult, output_path: str) -> None:
        """Export HTML report with interactive elements."""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Analysis Report - {result.repository_path}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
        h1, h2, h3 {{ color: #1a1a2e; }}
        .score {{ font-size: 2.5rem; font-weight: bold; }}
        .score.critical {{ color: #e74c3c; }}
        .score.high {{ color: #e67e22; }}
        .score.medium {{ color: #f39c12; }}
        .score.low {{ color: #27ae60; }}
        .category {{ display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid #eee; }}
        .category:last-child {{ border-bottom: none; }}
        .category-score {{ font-weight: bold; }}
        .category-score.critical {{ color: #e74c3c; }}
        .category-score.high {{ color: #e67e22; }}
        .category-score.medium {{ color: #f39c12; }}
        .category-score.low {{ color: #27ae60; }}
        .finding {{ padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .finding.critical {{ background: #fdf2f2; border-left: 4px solid #e74c3c; }}
        .finding.high {{ background: #fef5e7; border-left: 4px solid #e67e22; }}
        .finding.medium {{ background: #fef9e7; border-left: 4px solid #f39c12; }}
        .finding.low {{ background: #eafaf1; border-left: 4px solid #27ae60; }}
        .metric-table {{ width: 100%; border-collapse: collapse; }}
        .metric-table th, .metric-table td {{ padding: 8px; text-align: left; border-bottom: 1px solid #eee; }}
        .badge {{ padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }}
        .badge.critical {{ background: #e74c3c; color: white; }}
        .badge.high {{ background: #e67e22; color: white; }}
        .badge.medium {{ background: #f39c12; color: white; }}
        .badge.low {{ background: #27ae60; color: white; }}
        .badge.info {{ background: #3498db; color: white; }}
    </style>
</head>
<body>
    <h1>Code Analysis Report</h1>
    <div style="display: flex; justify-content: space-between; flex-wrap: wrap; gap: 20px;">
        <div>
            <strong>Repository:</strong> {result.repository_path}<br>
            <strong>Analyzed:</strong> {result.analyzed_at}<br>
            <strong>Files:</strong> {result.files_analyzed}<br>
            <strong>Lines:</strong> {result.total_lines}
        </div>
        <div style="text-align: right;">
            <div class="score {result.risk_level}">{result.overall_score}/100</div>
            <div>Risk: <span class="badge {result.risk_level}">{result.risk_level.upper()}</span></div>
            <div style="margin-top: 10px;">Duration: {result.total_duration_ms:.0f}ms</div>
        </div>
    </div>
    
    <h2>Summary</h2>
    <p>{result.summary}</p>
    
    <h2>Category Scores</h2>
    <div class="category-table">"""
        
        for cs in sorted(result.category_scores, key=lambda x: x.score):
            status_class = "critical" if cs.score < 40 else "high" if cs.score < 70 else "low"
            html += f"""
        <div class="category">
            <span>{cs.category}</span>
            <span class="category-score {status_class}">{cs.score:.1f}/100 <span style="font-weight: normal; color: #666;">(weight: {cs.weight}, {cs.duration_ms:.0f}ms)</span></span>
        </div>"""
        
        html += """
    </div>
    
    <h2>Strengths</h2>
    <ul>"""
        for s in result.strengths:
            html += f"<li>{s}</li>"
        
        html += """
    </ul>
    
    <h2>Weaknesses</h2>
    <ul>"""
        for w in result.weaknesses:
            html += f"<li>{w}</li>"
        
        html += """
    </ul>"""
        
        # Critical findings
        critical_findings = []
        for cs in result.category_scores:
            for f in cs.findings:
                if f.get("severity") in ["critical", "high"]:
                    critical_findings.append((cs.category, f))
        
        if critical_findings:
            html += f"""
    <h2>Critical/High Findings ({len(critical_findings)})</h2>"""
            for cat, f in critical_findings[:20]:
                severity = f.get('severity', '').lower()
                html += f"""
    <div class="finding {severity}">
        <h3><span class="badge {severity}">{f.get('severity', '').upper()}</span> {f.get('title', 'Unknown')} ({cat})</h3>
        <p><strong>Location:</strong> {f.get('file_path', 'N/A')}:{f.get('line_start', 'N/A')}</p>
        <p><strong>Description:</strong> {f.get('description', 'N/A')}</p>
        <p><strong>Recommendation:</strong> {f.get('recommendation', 'N/A')}</p>
    </div>"""
        
        html += """
</body>
</html>"""
        
        with open(output_path, 'w') as f:
            f.write(html)

    def print_summary(self, result: AnalysisResult) -> None:
        """Print summary to console."""
        print(f"\n{'='*70}")
        print(f"CODE ANALYSIS REPORT")
        print(f"{'='*70}")
        print(f"Repository: {result.repository_path}")
        print(f"Overall Score: {result.overall_score}/100")
        print(f"Risk Level: {result.risk_level.upper()}")
        print(f"Files Analyzed: {result.files_analyzed}")
        print(f"Total Lines: {result.total_lines}")
        print(f"Duration: {result.total_duration_ms:.0f}ms")
        print(f"\n{result.summary}")
        print(f"\n--- Category Scores ---")
        for cs in sorted(result.category_scores, key=lambda x: x.score):
            status = "[OK]" if cs.score >= 70 else "[WARN]" if cs.score >= 40 else "[FAIL]"
            print(f"  {status} {cs.category:20s} {cs.score:5.1f}/100 (weight: {cs.weight}, {cs.duration_ms:.0f}ms)")
        
        print(f"\n--- Strengths ---")
        for s in result.strengths[:5]:
            print(f"  + {s}")
        
        print(f"\n--- Weaknesses ---")
        for w in result.weaknesses[:5]:
            print(f"  - {w}")

        # Critical findings
        critical_findings = []
        for cs in result.category_scores:
            for f in cs.findings:
                if f.get("severity") in ["critical", "high"]:
                    critical_findings.append((cs.category, f))

        if critical_findings:
            print(f"\n--- Critical/High Findings ({len(critical_findings)}) ---")
            for cat, f in critical_findings[:10]:
                loc = f"{f.get('file_path', 'N/A')}:{f.get('line_start', 'N/A')}"
                print(f"  [{f.get('severity', '').upper()}] {f.get('title', 'Unknown')} ({cat})")
                print(f"    Location: {loc}")
                print(f"    -> {f.get('recommendation', 'N/A')}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Professional Code Analysis Agent")
    parser.add_argument("repo_path", help="Path to repository to analyze")
    parser.add_argument("--config", "-c", help="Path to config YAML file")
    parser.add_argument("--output", "-o", help="Output JSON report file")
    parser.add_argument("--format", "-f", choices=["json", "sarif", "markdown", "console"], 
                       default="console", help="Output format")
    parser.add_argument("--no-cache", action="store_true", help="Disable caching")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    # Load custom config if provided
    config = None
    if args.config:
        from pro.config.loader import ConfigLoader
        config = ConfigLoader().load(args.config)

    # Override cache setting
    if args.no_cache and config:
        config.execution.cache_enabled = False

    orchestrator = ProfessionalOrchestrator(args.repo_path, config)
    result = orchestrator.run_analysis()

    if args.format == "console":
        orchestrator.print_summary(result)
    elif args.format == "json":
        if args.output:
            orchestrator.export_json(result, args.output)
        else:
            print(json.dumps(asdict(result), indent=2, default=str))
    elif args.format == "sarif":
        output = args.output or "results.sarif"
        orchestrator.export_sarif(result, output)
        print(f"SARIF report saved to {output}")
    elif args.format == "markdown":
        output = args.output or "report.md"
        orchestrator.export_markdown(result, output)
        print(f"Markdown report saved to {output}")

    # Exit code based on risk level (for CI/CD)
    if config and config.integrations.exit_on_critical and result.risk_level == "critical":
        exit(1)
    if config and config.integrations.exit_on_high and result.risk_level in ["critical", "high"]:
        exit(1)


if __name__ == "__main__":
    main()