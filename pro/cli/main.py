"""
Professional CLI with subcommands for code analysis.
"""
import asyncio
import json
import sys
import os
from pathlib import Path
from typing import Optional, List
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

from pro.orchestrator import ProfessionalOrchestrator
from pro.config.loader import get_config, ConfigLoader
from pro.cache.manager import AnalysisCache
from pro.benchmarks.runner import BenchmarkRunner
from pro.benchmarks.regression import RegressionDetector
from pro.execution.incremental import IncrementalAnalyzer
from pro.sbom.generator import SBOMGenerator, SBOMFormat
from pro.rules.engine import RuleEngine
from pro.comparison.diff import ComparisonEngine

console = Console()


@click.group()
@click.version_option(version="1.0.0", prog_name="code-analysis")
@click.option('--config', '-c', type=click.Path(exists=True), help='Config file path')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.pass_context
def cli(ctx, config, verbose):
    """Code Analysis Agent - Professional Edition"""
    ctx.ensure_object(dict)
    ctx.obj['config_path'] = config
    ctx.obj['verbose'] = verbose
    
    if verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--format', '-f', type=click.Choice(['console', 'json', 'sarif', 'markdown', 'html']), 
              default='console', help='Output format')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--no-cache', is_flag=True, help='Disable caching')
@click.option('--parallel/--sequential', default=True, help='Parallel execution')
@click.option('--fail-on', type=click.Choice(['critical', 'high', 'medium', 'low', 'none']), 
              default='critical', help='Exit code threshold')
@click.pass_context
def analyze(ctx, repo_path, format, output, no_cache, parallel, fail_on):
    """Analyze a repository for code quality."""
    config_path = ctx.obj['config_path']
    config = None
    if config_path:
        config = ConfigLoader().load(config_path)
    
    if no_cache and config:
        config.execution.cache_enabled = False
    if not parallel and config:
        config.execution.parallel = False
    
    orchestrator = ProfessionalOrchestrator(repo_path, config)
    
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing repository...", total=None)
        result = orchestrator.run_analysis()
        progress.update(task, completed=True)
    
    # Output based on format
    if format == 'console':
        orchestrator.print_summary(result)
    elif format == 'json':
        output_path = output or f"{Path(repo_path).name}_analysis.json"
        orchestrator.export_json(result, output_path)
        console.print(f"[green]JSON report saved to {output_path}[/green]")
    elif format == 'sarif':
        output_path = output or f"{Path(repo_path).name}.sarif"
        orchestrator.export_sarif(result, output_path)
        console.print(f"[green]SARIF report saved to {output_path}[/green]")
    elif format == 'markdown':
        output_path = output or f"{Path(repo_path).name}_report.md"
        orchestrator.export_markdown(result, output_path)
        console.print(f"[green]Markdown report saved to {output_path}[/green]")
    elif format == 'html':
        output_path = output or f"{Path(repo_path).name}_report.html"
        orchestrator.export_html(result, output_path)
        console.print(f"[green]HTML report saved to {output_path}[/green]")
    
    # Exit code based on risk level
    risk_levels = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'none': -1}
    threshold = risk_levels.get(fail_on, 0)
    current = risk_levels.get(result.risk_level, 4)
    
    if current <= threshold:
        console.print(f"[red]Risk level {result.risk_level} exceeds threshold {fail_on}[/red]")
        sys.exit(1)
    else:
        console.print(f"[green]Risk level {result.risk_level} within threshold {fail_on}[/green]")
        sys.exit(0)


@cli.command()
@click.argument('repo_paths', nargs=-1, type=click.Path(exists=True, file_okay=False, dir_okay=True), required=True)
@click.option('--baseline', '-b', type=click.Path(), help='Baseline results file for comparison')
@click.option('--output', '-o', type=click.Path(), help='Output benchmark file')
@click.option('--iterations', '-i', default=3, help='Number of iterations per repo')
@click.pass_context
def benchmark(ctx, repo_paths, baseline, output, iterations):
    """Run performance benchmarks on repositories."""
    config_path = ctx.obj['config_path']
    config = None
    if config_path:
        config = ConfigLoader().load(config_path)
    
    runner = BenchmarkRunner(config)
    
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Benchmarking {len(repo_paths)} repositories...", total=len(repo_paths) * iterations)
        
        results = runner.run_benchmarks(list(repo_paths), iterations, progress, task)
    
    output_path = output or "benchmark_results.json"
    runner.save_results(results, output_path)
    
    # Display summary
    table = Table(title="Benchmark Results")
    table.add_column("Repository")
    table.add_column("Avg Time (ms)")
    table.add_column("Min Time (ms)")
    table.add_column("Max Time (ms)")
    table.add_column("Std Dev (ms)")
    table.add_column("Cache Hit Rate")
    
    for r in results:
        table.add_row(
            r['repo_name'],
            f"{r['avg_time_ms']:.1f}",
            f"{r['min_time_ms']:.1f}",
            f"{r['max_time_ms']:.1f}",
            f"{r['std_dev_ms']:.1f}",
            f"{r['cache_hit_rate']:.1%}"
        )
    
    console.print(table)
    console.print(f"[green]Results saved to {output_path}[/green]")


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--baseline', '-b', type=click.Path(exists=True), required=True, help='Baseline results file')
@click.option('--output', '-o', type=click.Path(), help='Output regression report')
@click.option('--threshold', '-t', default=5.0, help='Regression threshold (points)')
@click.pass_context
def regress(ctx, repo_path, baseline, output, threshold):
    """Detect regressions against a baseline."""
    config_path = ctx.obj['config_path']
    config = None
    if config_path:
        config = ConfigLoader().load(config_path)
    
    detector = RegressionDetector(config, threshold)
    
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Running analysis...", total=None)
        result = detector.analyze_and_compare(repo_path, baseline)
        progress.update(task, completed=True)
    
    # Display results
    if result['has_regression']:
        console.print(Panel(
            f"[red]REGRESSION DETECTED[/red]\n"
            f"Overall score dropped by {result['score_delta']:.1f} points\n"
            f"Threshold: {threshold} points",
            title="Regression Alert",
            border_style="red"
        ))
    else:
        console.print(Panel(
            f"[green]No regression detected[/green]\n"
            f"Score change: {result['score_delta']:.1f} points\n"
            f"Threshold: {threshold} points",
            title="Regression Check",
            border_style="green"
        ))
    
    # Category breakdown
    table = Table(title="Category Changes")
    table.add_column("Category")
    table.add_column("Baseline")
    table.add_column("Current")
    table.add_column("Delta")
    table.add_column("Status")
    
    for cat in result['categories']:
        status = "[red]REGRESSION[/red]" if cat['regression'] else "[green]OK[/green]"
        table.add_row(
            cat['name'],
            f"{cat['baseline']:.1f}",
            f"{cat['current']:.1f}",
            f"{cat['delta']:+.1f}",
            status
        )
    
    console.print(table)
    
    if output:
        with open(output, 'w') as f:
            json.dump(result, f, indent=2)
        console.print(f"[green]Report saved to {output}[/green]")
    
    if result['has_regression']:
        sys.exit(1)
    else:
        sys.exit(0)


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--skill', '-s', multiple=True, help='Run specific skill(s) only')
@click.pass_context
def skills(ctx, repo_path, skill):
    """List or run individual skills."""
    config_path = ctx.obj['config_path']
    config = None
    if config_path:
        config = ConfigLoader().load(config_path)
    
    orchestrator = ProfessionalOrchestrator(repo_path, config)
    orchestrator.load_repository()
    
    if not skill:
        # List available skills
        table = Table(title="Available Skills")
        table.add_column("Name")
        table.add_column("Category")
        table.add_column("Weight")
        table.add_column("Description")
        
        skill_descriptions = {
            'complexity': 'Cyclomatic, cognitive, Halstead, nesting complexity',
            'security': 'Bandit + custom patterns + AST semantic analysis',
            'testing': 'Coverage, mutation testing, test quality',
            'architecture': 'Import graph, cycles, layering, patterns',
            'maintainability': 'Function/class metrics, SOLID violations',
            'dependencies': 'Vulnerabilities, licenses, outdated packages, SBOM',
            'documentation': 'Docstring quality, README, license files',
            'git_history': 'Bus factor, churn, fix ratio, team patterns'
        }
        
        for name, _, weight in orchestrator.skills:
            if skill and name not in skill:
                continue
            table.add_row(name, name, str(weight), skill_descriptions.get(name, ''))
        
        console.print(table)
    else:
        # Run specific skills
        orchestrator.skills = [(n, s, w) for n, s, w in orchestrator.skills if n in skill]
        result = orchestrator.run_analysis()
        orchestrator.print_summary(result)


@cli.command()
@click.option('--cache-dir', type=click.Path(), help='Cache directory to clear')
@click.pass_context
def clear_cache(ctx, cache_dir):
    """Clear analysis cache."""
    config_path = ctx.obj['config_path']
    config = None
    if config_path:
        config = ConfigLoader().load(config_path)
    
    if cache_dir:
        cache = AnalysisCache(cache_dir)
    elif config:
        cache = AnalysisCache(config.execution.cache_dir)
    else:
        cache = AnalysisCache(".code_analysis_cache")
    
    count = cache.clear()
    console.print(f"[green]Cleared {count} cache entries[/green]")


@cli.command()
@click.option('--cache-dir', type=click.Path(), help='Cache directory to inspect')
@click.pass_context
def cache_stats(ctx, cache_dir):
    """Show cache statistics."""
    config_path = ctx.obj['config_path']
    config = None
    if config_path:
        config = ConfigLoader().load(config_path)
    
    if cache_dir:
        cache = AnalysisCache(cache_dir)
    elif config:
        cache = AnalysisCache(config.execution.cache_dir)
    else:
        cache = AnalysisCache(".code_analysis_cache")
    
    stats = cache.stats()
    
    table = Table(title="Cache Statistics")
    table.add_column("Metric")
    table.add_column("Value")
    
    for key, value in stats.items():
        table.add_row(key.replace('_', ' ').title(), str(value))
    
    console.print(table)


@cli.command()
@click.pass_context
def config_show(ctx):
    """Show current configuration."""
    config_path = ctx.obj['config_path']
    config = ConfigLoader().load(config_path) if config_path else get_config()
    
    console.print_json(json.dumps(config.__dict__, indent=2, default=str))


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--base', default='HEAD~1', help='Base git ref')
@click.option('--target', default='HEAD', help='Target git ref')
@click.option('--force-full', is_flag=True, help='Force full analysis')
@click.option('--output', '-o', type=click.Path(), help='Output file')
@click.pass_context
def incremental(ctx, repo_path, base, target, force_full, output):
    """Run incremental analysis (only changed files)."""
    analyzer = IncrementalAnalyzer(repo_path)
    result = analyzer.run_incremental(base, target, force_full)
    
    output_data = {
        "full_analysis": result.full_analysis,
        "changed_files": result.changed_files,
        "affected_modules": list(result.affected_modules),
        "analysis_time_ms": result.analysis_time_ms,
        "cache_hits": result.cache_hits,
        "cache_misses": result.cache_misses
    }
    
    if output:
        with open(output, 'w') as f:
            json.dump(output_data, f, indent=2)
        console.print(f"[green]Results saved to {output}[/green]")
    else:
        console.print_json(json.dumps(output_data, indent=2))


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--format', '-f', type=click.Choice(['cyclonedx-json', 'spdx-json']),
              default='cyclonedx-json', help='SBOM format')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.pass_context
def sbom(ctx, repo_path, format, output):
    """Generate Software Bill of Materials (SBOM)."""
    generator = SBOMGenerator(repo_path)
    fmt = SBOMFormat(format)
    sbom_data = generator.generate(fmt)
    
    if output:
        generator.save(output, fmt)
        console.print(f"[green]SBOM saved to {output}[/green]")
    else:
        console.print_json(json.dumps(sbom_data, indent=2))


@cli.command()
@click.argument('rules_file', type=click.Path(exists=True))
@click.argument('repo_path', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--output', '-o', type=click.Path(), help='Output file')
@click.pass_context
def rules_apply(ctx, rules_file, repo_path, output):
    """Apply custom rules to repository."""
    engine = RuleEngine()
    engine.load_rules(rules_file)
    
    # Load repository
    file_contents = {}
    for path in Path(repo_path).rglob('*.py'):
        rel = path.relative_to(repo_path)
        file_contents[str(rel)] = path.read_text()
    
    results = engine.analyze_repository(file_contents)
    
    # Format output
    all_matches = []
    for file_path, matches in results.items():
        for m in matches:
            all_matches.append({
                'rule_id': m.rule_id,
                'file': file_path,
                'line': m.line_start,
                'severity': m.severity.value,
                'message': m.message,
                'code': m.code_snippet
            })
    
    if output:
        with open(output, 'w') as f:
            json.dump(all_matches, f, indent=2)
        console.print(f"[green]Results saved to {output}[/green]")
    else:
        console.print_json(json.dumps(all_matches, indent=2))


@cli.command()
@click.argument('output', type=click.Path())
def rules_create_defaults(output):
    """Create default rules file."""
    engine = RuleEngine()
    engine.create_default_rules()
    engine.export_rules(output)
    console.print(f"[green]Default rules exported to {output}[/green]")


@cli.command()
@click.argument('rules_file', type=click.Path(exists=True))
def rules_list(rules_file):
    """List rules in file."""
    engine = RuleEngine()
    engine.load_rules(rules_file)
    
    table = Table(title="Custom Rules")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Severity")
    table.add_column("Tags")
    
    for rule in engine.list_rules():
        table.add_row(
            rule.id,
            rule.name,
            rule.type.value,
            rule.severity.value,
            ", ".join(rule.tags)
        )
    
    console.print(table)


@cli.command()
@click.argument('baseline', type=click.Path(exists=True))
@click.argument('current', type=click.Path(exists=True))
@click.option('--format', '-f', type=click.Choice(['console', 'markdown', 'json']),
              default='console', help='Output format')
@click.option('--output', '-o', type=click.Path(), help='Output file')
@click.option('--threshold', '-t', default=1.0, help='Score change threshold')
@click.pass_context
def compare(ctx, baseline, current, format, output, threshold):
    """Compare two analysis results."""
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


if __name__ == '__main__':
    cli()