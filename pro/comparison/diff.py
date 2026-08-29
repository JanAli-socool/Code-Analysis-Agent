"""
Comparison/Diff View - Compare two analysis results.
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class ChangeType(Enum):
    IMPROVED = "improved"
    REGRESSED = "regressed"
    NEW_FINDING = "new_finding"
    FIXED_FINDING = "fixed_finding"
    UNCHANGED = "unchanged"
    NEW_CATEGORY = "new_category"
    REMOVED_CATEGORY = "removed_category"


@dataclass
class FindingDiff:
    rule_id: str
    file_path: Optional[str]
    line_start: Optional[int]
    severity_before: Optional[str]
    severity_after: Optional[str]
    change_type: ChangeType
    message_before: Optional[str]
    message_after: Optional[str]


@dataclass
class CategoryDiff:
    category: str
    score_before: float
    score_after: float
    delta: float
    change_type: ChangeType
    findings_diff: List[FindingDiff]
    metrics_diff: Dict[str, Tuple[Optional[float], Optional[float]]]


@dataclass
class ComparisonResult:
    overall_score_before: float
    overall_score_after: float
    overall_delta: float
    risk_level_before: str
    risk_level_after: str
    categories: List[CategoryDiff]
    summary: Dict[str, int]  # counts by change type
    new_strengths: List[str]
    new_weaknesses: List[str]


class ComparisonEngine:
    def __init__(self, threshold: float = 1.0):
        self.threshold = threshold
    
    def compare(self, baseline: Dict[str, Any], current: Dict[str, Any]) -> ComparisonResult:
        """Compare two analysis results."""
        # Extract category scores
        baseline_cats = {c['category']: c for c in baseline.get('categories', [])}
        current_cats = {c['category']: c for c in current.get('categories', [])}
        
        all_categories = set(baseline_cats.keys()) | set(current_cats.keys())
        categories_diff = []
        
        summary = defaultdict(int)
        
        for cat_name in sorted(all_categories):
            base_cat = baseline_cats.get(cat_name)
            curr_cat = current_cats.get(cat_name)
            
            if base_cat and curr_cat:
                cat_diff = self._compare_category(cat_name, base_cat, curr_cat)
            elif base_cat and not curr_cat:
                cat_diff = CategoryDiff(
                    category=cat_name,
                    score_before=base_cat['score'],
                    score_after=0.0,
                    delta=-base_cat['score'],
                    change_type=ChangeType.REMOVED_CATEGORY,
                    findings_diff=[],
                    metrics_diff={}
                )
                summary[ChangeType.REMOVED_CATEGORY.value] += 1
            elif not base_cat and curr_cat:
                cat_diff = CategoryDiff(
                    category=cat_name,
                    score_before=0.0,
                    score_after=curr_cat['score'],
                    delta=curr_cat['score'],
                    change_type=ChangeType.NEW_CATEGORY,
                    findings_diff=[],
                    metrics_diff={}
                )
                summary[ChangeType.NEW_CATEGORY.value] += 1
            else:
                continue
            
            categories_diff.append(cat_diff)
            summary[cat_diff.change_type.value] += 1
        
        overall_before = baseline.get('overall_score', 0)
        overall_after = current.get('overall_score', 0)
        
        return ComparisonResult(
            overall_score_before=overall_before,
            overall_score_after=overall_after,
            overall_delta=overall_after - overall_before,
            risk_level_before=baseline.get('risk_level', 'unknown'),
            risk_level_after=current.get('risk_level', 'unknown'),
            categories=categories_diff,
            summary=dict(summary),
            new_strengths=self._find_new_strengths(baseline, current),
            new_weaknesses=self._find_new_weaknesses(baseline, current)
        )
    
    def _compare_category(self, name: str, base: Dict, curr: Dict) -> CategoryDiff:
        score_before = base.get('score', 0)
        score_after = curr.get('score', 0)
        delta = score_after - score_before
        
        # Determine change type
        if abs(delta) < self.threshold:
            change_type = ChangeType.UNCHANGED
        elif delta > 0:
            change_type = ChangeType.IMPROVED
        else:
            change_type = ChangeType.REGRESSED
        
        # Compare findings
        findings_diff = self._compare_findings(
            base.get('findings', []),
            curr.get('findings', [])
        )
        
        # Update summary for findings
        for fd in findings_diff:
            if fd.change_type != ChangeType.UNCHANGED:
                # We'll track this in the overall summary
                pass
        
        # Compare metrics
        metrics_diff = self._compare_metrics(
            base.get('metrics', []),
            curr.get('metrics', [])
        )
        
        return CategoryDiff(
            category=name,
            score_before=score_before,
            score_after=score_after,
            delta=round(delta, 1),
            change_type=change_type,
            findings_diff=findings_diff,
            metrics_diff=metrics_diff
        )
    
    def _compare_findings(self, base_findings: List[Dict], curr_findings: List[Dict]) -> List[FindingDiff]:
        """Compare findings between two analyses."""
        # Create lookup keys for findings
        def make_key(f: Dict) -> str:
            parts = [
                f.get('id', ''),
                f.get('file_path', ''),
                str(f.get('line_start', '')),
                f.get('severity', ''),
                f.get('message', '')[:50]
            ]
            return '|'.join(str(p) for p in parts)
        
        base_map = {make_key(f): f for f in base_findings}
        curr_map = {make_key(f): f for f in curr_findings}
        
        all_keys = set(base_map.keys()) | set(curr_map.keys())
        diffs = []
        
        for key in all_keys:
            base_f = base_map.get(key)
            curr_f = curr_map.get(key)
            
            if base_f and curr_f:
                # Both exist - check severity change
                sev_before = base_f.get('severity')
                sev_after = curr_f.get('severity')
                
                if sev_before == sev_after:
                    change_type = ChangeType.UNCHANGED
                else:
                    # Map severity to numeric for comparison
                    sev_order = {'critical': 5, 'high': 4, 'medium': 3, 'low': 2, 'info': 1}
                    before_val = sev_order.get(sev_before, 0)
                    after_val = sev_order.get(sev_after, 0)
                    
                    if after_val > before_val:
                        change_type = ChangeType.REGRESSED
                    elif after_val < before_val:
                        change_type = ChangeType.IMPROVED
                    else:
                        change_type = ChangeType.UNCHANGED
                
                diffs.append(FindingDiff(
                    rule_id=base_f.get('id', curr_f.get('id', '')),
                    file_path=base_f.get('file_path') or curr_f.get('file_path'),
                    line_start=base_f.get('line_start') or curr_f.get('line_start'),
                    severity_before=sev_before,
                    severity_after=sev_after,
                    change_type=change_type,
                    message_before=base_f.get('message'),
                    message_after=curr_f.get('message')
                ))
            
            elif base_f and not curr_f:
                diffs.append(FindingDiff(
                    rule_id=base_f.get('id', ''),
                    file_path=base_f.get('file_path'),
                    line_start=base_f.get('line_start'),
                    severity_before=base_f.get('severity'),
                    severity_after=None,
                    change_type=ChangeType.FIXED_FINDING,
                    message_before=base_f.get('message'),
                    message_after=None
                ))
            
            elif not base_f and curr_f:
                diffs.append(FindingDiff(
                    rule_id=curr_f.get('id', ''),
                    file_path=curr_f.get('file_path'),
                    line_start=curr_f.get('line_start'),
                    severity_before=None,
                    severity_after=curr_f.get('severity'),
                    change_type=ChangeType.NEW_FINDING,
                    message_before=None,
                    message_after=curr_f.get('message')
                ))
        
        return diffs
    
    def _compare_metrics(self, base_metrics: List[Dict], curr_metrics: List[Dict]) -> Dict[str, Tuple[Optional[float], Optional[float]]]:
        base_map = {m['name']: m['value'] for m in base_metrics}
        curr_map = {m['name']: m['value'] for m in curr_metrics}
        
        all_names = set(base_map.keys()) | set(curr_map.keys())
        diffs = {}
        
        for name in all_names:
            before = base_map.get(name)
            after = curr_map.get(name)
            diffs[name] = (before, after)
        
        return diffs
    
    def _find_new_strengths(self, baseline: Dict, current: Dict) -> List[str]:
        """Find newly appearing strengths."""
        base_strengths = set(baseline.get('strengths', []))
        curr_strengths = set(current.get('strengths', []))
        return list(curr_strengths - base_strengths)
    
    def _find_new_weaknesses(self, baseline: Dict, current: Dict) -> List[str]:
        """Find newly appearing weaknesses."""
        base_weaknesses = set(baseline.get('weaknesses', []))
        curr_weaknesses = set(current.get('weaknesses', []))
        return list(curr_weaknesses - base_weaknesses)
    
    def generate_report(self, result: ComparisonResult, format: str = 'console') -> str:
        """Generate human-readable comparison report."""
        if format == 'console':
            return self._generate_console_report(result)
        elif format == 'markdown':
            return self._generate_markdown_report(result)
        elif format == 'json':
            return json.dumps({
                'overall_score_before': result.overall_score_before,
                'overall_score_after': result.overall_score_after,
                'overall_delta': result.overall_delta,
                'risk_level_before': result.risk_level_before,
                'risk_level_after': result.risk_level_after,
                'summary': result.summary,
                'categories': [
                    {
                        'category': c.category,
                        'score_before': c.score_before,
                        'score_after': c.score_after,
                        'delta': c.delta,
                        'change_type': c.change_type.value,
                        'findings_changes': [
                            {
                                'rule_id': f.rule_id,
                                'file': f.file_path,
                                'line': f.line_start,
                                'change': f.change_type.value,
                                'severity_before': f.severity_before,
                                'severity_after': f.severity_after
                            }
                            for f in c.findings_diff
                        ]
                    }
                    for c in result.categories
                ],
                'new_strengths': result.new_strengths,
                'new_weaknesses': result.new_weaknesses
            }, indent=2)
        return ""
    
    def _generate_console_report(self, result: ComparisonResult) -> str:
        lines = [
            "=" * 70,
            "CODE ANALYSIS COMPARISON REPORT",
            "=" * 70,
            f"",
            f"Overall Score: {result.overall_score_before:.1f} -> {result.overall_score_after:.1f} ({result.overall_delta:+.1f})",
            f"Risk Level: {result.risk_level_before} -> {result.risk_level_after}",
            f"",
            f"Summary:",
        ]
        
        for change_type, count in result.summary.items():
            if count > 0:
                lines.append(f"  {change_type}: {count}")
        
        lines.extend(["", "Category Changes:", "-" * 70])
        
        for cat in sorted(result.categories, key=lambda x: x.delta):
            if cat.change_type == ChangeType.UNCHANGED and abs(cat.delta) < 0.1:
                continue
            
            icon = {
                ChangeType.IMPROVED: "[+]",
                ChangeType.REGRESSED: "[-]",
                ChangeType.NEW_CATEGORY: "[+]",
                ChangeType.REMOVED_CATEGORY: "[-]",
                ChangeType.UNCHANGED: "[=]"
            }.get(cat.change_type, "[?]")
            
            lines.append(f"  {icon} {cat.category:20s} {cat.score_before:5.1f} -> {cat.score_after:5.1f} ({cat.delta:+.1f})")
            
            # Show significant finding changes
            for fd in cat.findings_diff:
                if fd.change_type in (ChangeType.NEW_FINDING, ChangeType.FIXED_FINDING, ChangeType.REGRESSED, ChangeType.IMPROVED):
                    loc = f"{fd.file_path}:{fd.line_start}" if fd.file_path else "N/A"
                    sev_change = f"{fd.severity_before} -> {fd.severity_after}" if fd.severity_before and fd.severity_after else fd.severity_after or fd.severity_before
                    lines.append(f"    {fd.change_type.value}: {fd.rule_id} ({loc}) [{sev_change}]")
        
        if result.new_strengths:
            lines.extend(["", "New Strengths:"])
            for s in result.new_strengths:
                lines.append(f"  + {s}")
        
        if result.new_weaknesses:
            lines.extend(["", "New Weaknesses:"])
            for w in result.new_weaknesses:
                lines.append(f"  - {w}")
        
        return "\n".join(lines)
    
    def _generate_markdown_report(self, result: ComparisonResult) -> str:
        lines = [
            "# Code Analysis Comparison Report",
            "",
            f"**Overall Score:** {result.overall_score_before:.1f} -> {result.overall_score_after:.1f} ({result.overall_delta:+.1f})",
            f"**Risk Level:** {result.risk_level_before} -> {result.risk_level_after}",
            "",
            "## Summary",
            ""
        ]
        
        for change_type, count in result.summary.items():
            if count > 0:
                lines.append(f"- **{change_type.replace('_', ' ').title()}:** {count}")
        
        lines.extend(["", "## Category Changes", ""])
        
        for cat in sorted(result.categories, key=lambda x: x.delta):
            if cat.change_type == ChangeType.UNCHANGED and abs(cat.delta) < 0.1:
                continue
            
            icon = {
                ChangeType.IMPROVED: "[+]",
                ChangeType.REGRESSED: "[-]",
                ChangeType.NEW_CATEGORY: "[+]",
                ChangeType.REMOVED_CATEGORY: "[-]",
                ChangeType.UNCHANGED: "[=]"
            }.get(cat.change_type, "[?]")
            
            lines.append(f"### {icon} {cat.category}")
            lines.append(f"- **Score:** {cat.score_before:.1f} -> {cat.score_after:.1f} ({cat.delta:+.1f})")
            lines.append(f"- **Change:** {cat.change_type.value}")
            
            if cat.findings_diff:
                lines.append("- **Finding Changes:**")
                for fd in cat.findings_diff:
                    if fd.change_type != ChangeType.UNCHANGED:
                        loc = f"`{fd.file_path}:{fd.line_start}`" if fd.file_path else "N/A"
                        lines.append(f"  - {fd.change_type.value}: `{fd.rule_id}` at {loc}")
        
        if result.new_strengths:
            lines.extend(["", "## New Strengths", ""])
            for s in result.new_strengths:
                lines.append(f"- {s}")
        
        if result.new_weaknesses:
            lines.extend(["", "## New Weaknesses", ""])
            for w in result.new_weaknesses:
                lines.append(f"- {w}")
        
        return "\n".join(lines)


def create_comparison_cli():
    """CLI for comparison."""
    import click
    
    @click.command()
    @click.argument('baseline', type=click.Path(exists=True))
    @click.argument('current', type=click.Path(exists=True))
    @click.option('--format', '-f', type=click.Choice(['console', 'markdown', 'json']),
                  default='console', help='Output format')
    @click.option('--output', '-o', type=click.Path(), help='Output file')
    @click.option('--threshold', '-t', default=1.0, help='Score change threshold')
    def compare(baseline, current, format, output, threshold):
        with open(baseline) as f:
            base = json.load(f)
        with open(current) as f:
            curr = json.load(f)
        
        engine = ComparisonEngine(threshold)
        result = engine.compare(base, curr)
        report = engine.generate_report(result, format)
        
        if output:
            with open(output, 'w') as f:
                f.write(report)
            console.print(f"[green]Report saved to {output}[/green]")
        else:
            console.print(report)
    
    return compare


if __name__ == "__main__":
    import json
    from rich.console import Console
    console = Console()
    create_comparison_cli()