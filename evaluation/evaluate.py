#!/usr/bin/env python3
"""
Evaluation Framework - Compare baseline vs advanced solution on test repositories
"""
import json
import subprocess
import sys
import os
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, asdict


@dataclass
class TestCase:
    name: str
    repo_path: str
    expected_quality: str  # "high", "medium", "low"
    description: str


@dataclass
class EvaluationResult:
    test_case: str
    baseline_score: float
    advanced_score: float
    baseline_risk: str
    advanced_risk: str
    baseline_findings: int
    advanced_findings: int
    improvement: float


class Evaluator:
    def __init__(self):
        self.test_cases = [
            TestCase(
                name="good_repo",
                repo_path="test_repos/good_repo",
                expected_quality="high",
                description="Well-structured code with tests, docs, type hints"
            ),
            TestCase(
                name="medium_repo",
                repo_path="test_repos/medium_repo",
                expected_quality="medium",
                description="Moderate quality, some tests, basic structure"
            ),
            TestCase(
                name="bad_repo",
                repo_path="test_repos/bad_repo",
                expected_quality="low",
                description="Security issues, high complexity, no tests, hardcoded secrets"
            ),
            TestCase(
                name="legacy_repo",
                repo_path="test_repos/legacy_repo",
                expected_quality="low",
                description="SQL injection, outdated patterns, mixed concerns"
            ),
            TestCase(
                name="microservice_repo",
                repo_path="test_repos/microservice_repo",
                expected_quality="high",
                description="Clean architecture, dependency injection, good test coverage"
            )
        ]

    def run_baseline(self, repo_path: str) -> Dict[str, Any]:
        """Run baseline analyzer on repository."""
        result = subprocess.run(
            [sys.executable, "baseline/analyze.py", repo_path],
            capture_output=True, text=True, cwd=os.getcwd()
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        return {"score": 0, "error": result.stderr}

    def run_advanced(self, repo_path: str) -> Dict[str, Any]:
        """Run advanced analyzer on repository."""
        result = subprocess.run(
            [sys.executable, "-m", "advanced.orchestrator", repo_path, "--json"],
            capture_output=True, text=True, cwd=os.getcwd()
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        return {"overall_score": 0, "error": result.stderr}

    def evaluate(self) -> List[EvaluationResult]:
        """Run evaluation on all test cases."""
        results = []
        
        for tc in self.test_cases:
            print(f"\nEvaluating {tc.name}...")
            print(f"  Description: {tc.description}")
            
            baseline_result = self.run_baseline(tc.repo_path)
            advanced_result = self.run_advanced(tc.repo_path)
            
            baseline_score = baseline_result.get("score", 0)
            advanced_score = advanced_result.get("overall_score", 0)
            
            eval_result = EvaluationResult(
                test_case=tc.name,
                baseline_score=baseline_score,
                advanced_score=advanced_score,
                baseline_risk=self._score_to_risk(baseline_score),
                advanced_risk=advanced_result.get("risk_level", "unknown"),
                baseline_findings=len(baseline_result.get("issues", [])),
                advanced_findings=sum(len(cs.get("findings", [])) for cs in advanced_result.get("categories", [])),
                improvement=advanced_score - baseline_score
            )
            results.append(eval_result)
            
            print(f"  Baseline: {baseline_score}/100 ({eval_result.baseline_risk})")
            print(f"  Advanced: {advanced_score}/100 ({eval_result.advanced_risk})")
            print(f"  Improvement: {eval_result.improvement:+.1f}")
        
        return results

    def _score_to_risk(self, score: float) -> str:
        if score >= 80:
            return "low"
        elif score >= 60:
            return "medium"
        elif score >= 40:
            return "high"
        else:
            return "critical"

    def print_summary(self, results: List[EvaluationResult]):
        print("\n" + "="*80)
        print("EVALUATION SUMMARY")
        print("="*80)
        print(f"{'Test Case':<20} {'Baseline':>10} {'Advanced':>10} {'Improvement':>12} {'Baseline Risk':<12} {'Advanced Risk':<12}")
        print("-"*80)
        
        total_baseline = 0
        total_advanced = 0
        
        for r in results:
            print(f"{r.test_case:<20} {r.baseline_score:>10.1f} {r.advanced_score:>10.1f} {r.improvement:>+11.1f} {r.baseline_risk:<12} {r.advanced_risk:<12}")
            total_baseline += r.baseline_score
            total_advanced += r.advanced_score
        
        print("-"*80)
        avg_baseline = total_baseline / len(results)
        avg_advanced = total_advanced / len(results)
        print(f"{'AVERAGE':<20} {avg_baseline:>10.1f} {avg_advanced:>10.1f} {avg_advanced - avg_baseline:>+11.1f}")
        
        print("\n" + "="*80)
        print("DETAILED METRICS")
        print("="*80)
        print(f"Average Baseline Score: {avg_baseline:.1f}/100")
        print(f"Average Advanced Score: {avg_advanced:.1f}/100")
        print(f"Overall Improvement: {avg_advanced - avg_baseline:+.1f} points")
        print(f"Relative Improvement: {((avg_advanced - avg_baseline) / max(avg_baseline, 1)) * 100:+.1f}%")
        
        correct_rankings = sum(1 for r in results 
                              if (r.baseline_score < 50 and r.advanced_score < 50) or
                                 (r.baseline_score >= 50 and r.advanced_score >= 50))
        print(f"Correct Quality Classification: {correct_rankings}/{len(results)}")

    def save_results(self, results: List[EvaluationResult], output_path: str):
        data = {
            "test_cases": [asdict(r) for r in results],
            "summary": {
                "avg_baseline": sum(r.baseline_score for r in results) / len(results),
                "avg_advanced": sum(r.advanced_score for r in results) / len(results),
                "avg_improvement": sum(r.improvement for r in results) / len(results)
            }
        }
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\nResults saved to {output_path}")


def main():
    evaluator = Evaluator()
    results = evaluator.evaluate()
    evaluator.print_summary(results)
    evaluator.save_results(results, "evaluation/results.json")


if __name__ == "__main__":
    main()