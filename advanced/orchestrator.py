"""
Main Orchestrator - Coordinates all skills and produces final analysis
"""
import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from advanced.models import AgentContext, RepositoryAnalysis, CategoryScore, AnalysisCategory
from advanced.skills.complexity import ComplexitySkill
from advanced.skills.security import SecuritySkill
from advanced.skills.maintainability import MaintainabilitySkill
from advanced.skills.testing import TestingSkill
from advanced.skills.dependencies import DependenciesSkill
from advanced.skills.architecture import ArchitectureSkill
from advanced.skills.documentation import DocumentationSkill
from advanced.skills.git_history import GitHistorySkill


class CodeAnalysisOrchestrator:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
        self.context = AgentContext(repository_path=str(self.repo_path))
        self.skills = [
            ComplexitySkill(),
            SecuritySkill(),
            MaintainabilitySkill(),
            TestingSkill(),
            DependenciesSkill(),
            ArchitectureSkill(),
            DocumentationSkill(),
            GitHistorySkill()
        ]
        # Adjust weights: security, complexity, testing, architecture are most important
        self.skills[0].weight = 2.0  # complexity
        self.skills[1].weight = 3.0  # security
        self.skills[2].weight = 1.5  # maintainability
        self.skills[3].weight = 2.0  # testing
        self.skills[4].weight = 1.0  # dependencies
        self.skills[5].weight = 2.0  # architecture
        self.skills[6].weight = 0.5  # documentation (reduced)
        self.skills[7].weight = 0.5  # git_history (reduced)

    def load_repository(self):
        """Load all Python files and relevant config files into context."""
        extensions = {'.py', '.txt', '.toml', '.cfg', '.ini', '.yml', '.yaml', '.json', '.md', '.rst'}
        for file_path in self.repo_path.rglob('*'):
            if file_path.is_file() and file_path.suffix in extensions:
                try:
                    relative = file_path.relative_to(self.repo_path)
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    self.context.file_contents[str(relative)] = content
                except Exception:
                    pass

    def run_analysis(self) -> RepositoryAnalysis:
        """Run all skills and aggregate results."""
        self.load_repository()
        
        category_scores = []
        for skill in self.skills:
            try:
                score = skill.analyze(self.context)
                category_scores.append(score)
            except Exception as e:
                print(f"Skill {skill.name} failed: {e}")

        overall_score = self._calculate_overall_score(category_scores)
        risk_level = self._determine_risk_level(overall_score, category_scores)
        summary, strengths, weaknesses = self._generate_summary(category_scores)

        analysis = RepositoryAnalysis(
            repository_path=str(self.repo_path),
            overall_score=overall_score,
            category_scores=category_scores,
            summary=summary,
            strengths=strengths,
            weaknesses=weaknesses,
            risk_level=risk_level,
            files_analyzed=len([f for f in self.context.file_contents if f.endswith('.py')]),
            total_lines=sum(len(c.split('\n')) for c in self.context.file_contents.values())
        )

        self.context.analysis = analysis
        return analysis

    def _calculate_overall_score(self, category_scores: List[CategoryScore]) -> float:
        total_weight = sum(cs.weight for cs in category_scores)
        if total_weight == 0:
            return 0.0
        weighted_sum = sum(cs.score * cs.weight for cs in category_scores)
        return round(weighted_sum / total_weight, 1)

    def _determine_risk_level(self, overall_score: float, category_scores: List[CategoryScore]) -> str:
        critical_categories = [cs for cs in category_scores 
                              if cs.category in [AnalysisCategory.SECURITY, AnalysisCategory.ARCHITECTURE] 
                              and cs.score < 40]
        high_categories = [cs for cs in category_scores if cs.score < 30]

        if critical_categories or overall_score < 35:
            return "critical"
        elif overall_score < 55 or high_categories:
            return "high"
        elif overall_score < 75:
            return "medium"
        else:
            return "low"

    def _generate_summary(self, category_scores: List[CategoryScore]) -> tuple:
        sorted_scores = sorted(category_scores, key=lambda x: x.score)
        
        strengths = []
        weaknesses = []
        
        for cs in category_scores:
            if cs.score >= 80:
                strengths.append(f"Strong {cs.category.value}: {cs.score}/100")
            elif cs.score < 50:
                weaknesses.append(f"Weak {cs.category.value}: {cs.score}/100")

        summary = f"Overall Score: {self._calculate_overall_score(category_scores)}/100. "
        summary += f"Analyzed {len(category_scores)} categories. "
        summary += f"Top strengths: {', '.join(s[:50] for s in strengths[:3])}. "
        summary += f"Main weaknesses: {', '.join(w[:50] for w in weaknesses[:3])}."

        return summary, strengths, weaknesses

    def export_report(self, analysis: RepositoryAnalysis, output_path: str):
        """Export detailed report as JSON."""
        report = {
            "repository": analysis.repository_path,
            "analyzed_at": analysis.analyzed_at.isoformat(),
            "overall_score": analysis.overall_score,
            "risk_level": analysis.risk_level,
            "summary": analysis.summary,
            "strengths": analysis.strengths,
            "weaknesses": analysis.weaknesses,
            "files_analyzed": analysis.files_analyzed,
            "total_lines": analysis.total_lines,
            "categories": []
        }

        for cs in analysis.category_scores:
            cat_report = {
                "category": cs.category.value,
                "score": cs.score,
                "weight": cs.weight,
                "findings": [
                    {
                        "id": f.id,
                        "severity": f.severity.value,
                        "title": f.title,
                        "description": f.description,
                        "file_path": f.file_path,
                        "line_number": f.line_number,
                        "recommendation": f.recommendation
                    }
                    for f in cs.findings
                ],
                "metrics": [
                    {
                        "name": m.name,
                        "value": m.value,
                        "threshold": m.threshold,
                        "status": m.status,
                        "details": m.details
                    }
                    for m in cs.metrics
                ]
            }
            report["categories"].append(cat_report)

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

    def print_summary(self, analysis: RepositoryAnalysis):
        """Print human-readable summary."""
        print(f"\n{'='*60}")
        print(f"REPOSITORY ANALYSIS REPORT")
        print(f"{'='*60}")
        print(f"Repository: {analysis.repository_path}")
        print(f"Overall Score: {analysis.overall_score}/100")
        print(f"Risk Level: {analysis.risk_level.upper()}")
        print(f"Files Analyzed: {analysis.files_analyzed}")
        print(f"Total Lines: {analysis.total_lines}")
        print(f"\n{analysis.summary}")
        print(f"\n--- Category Scores ---")
        for cs in sorted(analysis.category_scores, key=lambda x: x.score):
            status = "[OK]" if cs.score >= 70 else "[WARN]" if cs.score >= 40 else "[FAIL]"
            print(f"  {status} {cs.category.value:20s} {cs.score:5.1f}/100 (weight: {cs.weight})")
        
        print(f"\n--- Strengths ---")
        for s in analysis.strengths[:5]:
            print(f"  + {s}")
        
        print(f"\n--- Weaknesses ---")
        for w in analysis.weaknesses[:5]:
            print(f"  - {w}")

        critical_findings = []
        for cs in analysis.category_scores:
            for f in cs.findings:
                if f.severity.value in ['critical', 'high']:
                    critical_findings.append(f)

        if critical_findings:
            print(f"\n--- Critical/High Findings ({len(critical_findings)}) ---")
            for f in critical_findings[:10]:
                loc = f"{f.file_path}:{f.line_number}" if f.file_path else "N/A"
                print(f"  [{f.severity.value.upper()}] {f.title} ({loc})")
                print(f"    -> {f.recommendation}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Advanced Repository Analyzer")
    parser.add_argument("repo_path", help="Path to repository to analyze")
    parser.add_argument("--output", "-o", help="Output JSON report file")
    parser.add_argument("--json", action="store_true", help="Output JSON to stdout")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    orchestrator = CodeAnalysisOrchestrator(args.repo_path)
    analysis = orchestrator.run_analysis()
    
    if args.json:
        import json
        from datetime import datetime
        report = {
            "repository": analysis.repository_path,
            "analyzed_at": analysis.analyzed_at.isoformat() if hasattr(analysis.analyzed_at, 'isoformat') else str(analysis.analyzed_at),
            "overall_score": analysis.overall_score,
            "risk_level": analysis.risk_level,
            "summary": analysis.summary,
            "strengths": analysis.strengths,
            "weaknesses": analysis.weaknesses,
            "files_analyzed": analysis.files_analyzed,
            "total_lines": analysis.total_lines,
            "categories": []
        }
        for cs in analysis.category_scores:
            cat_report = {
                "category": cs.category.value,
                "score": cs.score,
                "weight": cs.weight,
                "findings": [
                    {
                        "id": f.id,
                        "severity": f.severity.value,
                        "title": f.title,
                        "description": f.description,
                        "file_path": f.file_path,
                        "line_number": f.line_number,
                        "recommendation": f.recommendation
                    }
                    for f in cs.findings
                ],
                "metrics": [
                    {
                        "name": m.name,
                        "value": m.value,
                        "threshold": m.threshold,
                        "status": m.status,
                        "details": m.details
                    }
                    for m in cs.metrics
                ]
            }
            report["categories"].append(cat_report)
        print(json.dumps(report, indent=2))
    else:
        orchestrator.print_summary(analysis)
    
    if args.output:
        orchestrator.export_report(analysis, args.output)
        print(f"\nReport saved to: {args.output}")


if __name__ == "__main__":
    main()