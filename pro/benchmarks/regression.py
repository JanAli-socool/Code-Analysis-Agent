"""
Regression detection for code quality scores.
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from pro.orchestrator import ProfessionalOrchestrator
from pro.config.loader import get_config, ConfigLoader


@dataclass
class CategoryComparison:
    name: str
    baseline: float
    current: float
    delta: float
    regression: bool


@dataclass
class RegressionResult:
    has_regression: bool
    score_delta: float
    threshold: float
    categories: List[CategoryComparison]
    baseline_overall: float
    current_overall: float
    risk_level_baseline: str
    risk_level_current: str


class RegressionDetector:
    def __init__(self, config=None, threshold: float = 5.0):
        self.config = config or get_config()
        self.threshold = threshold
    
    def analyze_and_compare(self, repo_path: str, baseline_path: str) -> Dict[str, Any]:
        """Analyze current repo and compare with baseline."""
        # Load baseline
        with open(baseline_path) as f:
            baseline = json.load(f)
        
        # Run current analysis
        orchestrator = ProfessionalOrchestrator(repo_path, self.config)
        current = orchestrator.run_analysis()
        
        # Compare
        return self._compare(baseline, current)
    
    def _compare(self, baseline: Dict, current) -> Dict[str, Any]:
        """Compare baseline and current results."""
        baseline_overall = baseline.get('overall_score', 0)
        current_overall = current.overall_score
        score_delta = current_overall - baseline_overall
        
        # Compare categories
        categories = []
        baseline_cats = {c['category']: c for c in baseline.get('categories', [])}
        current_cats = {c.category: c for c in current.category_scores}
        
        all_categories = set(baseline_cats.keys()) | set(current_cats.keys())
        
        for cat_name in all_categories:
            base_cat = baseline_cats.get(cat_name)
            curr_cat = current_cats.get(cat_name)
            
            baseline_score = base_cat['score'] if base_cat else 0
            current_score = curr_cat.score if curr_cat else 0
            delta = current_score - baseline_score
            regression = delta < -self.threshold
            
            categories.append(CategoryComparison(
                name=cat_name,
                baseline=baseline_score,
                current=current_score,
                delta=delta,
                regression=regression
            ))
        
        has_regression = any(c.regression for c in categories) or score_delta < -self.threshold
        
        result = RegressionResult(
            has_regression=has_regression,
            score_delta=score_delta,
            threshold=self.threshold,
            categories=categories,
            baseline_overall=baseline_overall,
            current_overall=current_overall,
            risk_level_baseline=baseline.get('risk_level', 'unknown'),
            risk_level_current=current.risk_level
        )
        
        return asdict(result)
    
    def save_baseline(self, repo_path: str, output_path: str) -> None:
        """Create a new baseline from current analysis."""
        orchestrator = ProfessionalOrchestrator(repo_path, self.config)
        result = orchestrator.run_analysis()
        
        # Export in format expected by compare
        baseline_data = {
            'overall_score': result.overall_score,
            'risk_level': result.risk_level,
            'categories': [
                {
                    'category': cs.category,
                    'score': cs.score,
                    'weight': cs.weight,
                    'findings': cs.findings,
                    'metrics': cs.metrics
                }
                for cs in result.category_scores
            ]
        }
        
        with open(output_path, 'w') as f:
            json.dump(baseline_data, f, indent=2)
        
        return baseline_data
    
    def check_pr(self, repo_path: str, baseline_path: str, 
                output_path: Optional[str] = None) -> Dict[str, Any]:
        """Check for regressions in a PR context."""
        result = self.analyze_and_compare(repo_path, baseline_path)
        
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(result, f, indent=2)
        
        return result
    
    def generate_report(self, result: Dict[str, Any]) -> str:
        """Generate human-readable regression report."""
        lines = [
            "=" * 60,
            "REGRESSION DETECTION REPORT",
            "=" * 60,
            f"Overall Score: {result['baseline_overall']:.1f} -> {result['current_overall']:.1f} ({result['score_delta']:+.1f})",
            f"Threshold: {result['threshold']}",
            f"Baseline Risk: {result['risk_level_baseline']}",
            f"Current Risk: {result['risk_level_current']}",
            f"Regression: {'YES' if result['has_regression'] else 'NO'}",
            "",
            "Category Breakdown:",
            "-" * 60,
        ]
        
        for cat in result['categories']:
            status = "⚠️ REGRESSION" if cat['regression'] else "✓ OK"
            lines.append(
                f"  {cat['name']:20s} {cat['baseline']:6.1f} -> {cat['current']:6.1f} "
                f"({cat['delta']:+6.1f}) {status}"
            )
        
        return "\n".join(lines)