"""
Custom Rule Engine - DSL for defining custom analysis rules.
"""
import ast
import re
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod


class RuleSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class RuleType(Enum):
    AST_PATTERN = "ast_pattern"      # Match AST nodes
    REGEX_PATTERN = "regex_pattern"  # Match source code with regex
    METRIC_THRESHOLD = "metric_threshold"  # Check metric values
    COMPOSITE = "composite"           # Combine multiple rules


@dataclass
class RuleMatch:
    rule_id: str
    file_path: str
    line_start: int
    line_end: int
    column_start: int
    column_end: int
    message: str
    severity: RuleSeverity
    code_snippet: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Rule:
    id: str
    name: str
    description: str
    type: RuleType
    severity: RuleSeverity
    enabled: bool = True
    tags: List[str] = field(default_factory=list)
    # For AST_PATTERN
    ast_pattern: Optional[str] = None  # AST node type to match
    ast_condition: Optional[str] = None  # Python expression to evaluate
    # For REGEX_PATTERN
    regex_pattern: Optional[str] = None
    regex_flags: int = 0
    # For METRIC_THRESHOLD
    metric_name: Optional[str] = None
    threshold: Optional[float] = None
    comparison: str = "gt"  # gt, lt, gte, lte, eq, ne
    # For COMPOSITE
    sub_rules: List[str] = field(default_factory=list)  # Rule IDs
    composite_logic: str = "all"  # all, any, none
    # Metadata
    references: List[str] = field(default_factory=list)
    recommendation: str = ""


class RuleEngine:
    def __init__(self):
        self.rules: Dict[str, Rule] = {}
        self._compiled_patterns: Dict[str, re.Pattern] = {}
        self._ast_visitors: Dict[str, Callable] = {}
    
    def load_rules(self, rules_path: str):
        """Load rules from YAML/JSON file."""
        path = Path(rules_path)
        if not path.exists():
            raise FileNotFoundError(f"Rules file not found: {rules_path}")
        
        content = path.read_text()
        if path.suffix in ('.yaml', '.yml'):
            data = yaml.safe_load(content)
        else:
            data = json.loads(content)
        
        for rule_data in data.get('rules', []):
            rule = self._parse_rule(rule_data)
            self.rules[rule.id] = rule
    
    def _parse_rule(self, data: Dict) -> Rule:
        return Rule(
            id=data['id'],
            name=data['name'],
            description=data.get('description', ''),
            type=RuleType(data['type']),
            severity=RuleSeverity(data.get('severity', 'medium')),
            enabled=data.get('enabled', True),
            tags=data.get('tags', []),
            ast_pattern=data.get('ast_pattern'),
            ast_condition=data.get('ast_condition'),
            regex_pattern=data.get('regex_pattern'),
            regex_flags=data.get('regex_flags', 0),
            metric_name=data.get('metric_name'),
            threshold=data.get('threshold'),
            comparison=data.get('comparison', 'gt'),
            sub_rules=data.get('sub_rules', []),
            composite_logic=data.get('composite_logic', 'all'),
            references=data.get('references', []),
            recommendation=data.get('recommendation', '')
        )
    
    def add_rule(self, rule: Rule):
        """Add a rule programmatically."""
        self.rules[rule.id] = rule
    
    def remove_rule(self, rule_id: str):
        """Remove a rule."""
        self.rules.pop(rule_id, None)
    
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        return self.rules.get(rule_id)
    
    def list_rules(self, tag: Optional[str] = None, enabled_only: bool = True) -> List[Rule]:
        rules = list(self.rules.values())
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        if tag:
            rules = [r for r in rules if tag in r.tags]
        return rules
    
    def analyze_file(self, file_path: str, content: str) -> List[RuleMatch]:
        """Analyze a single file with all enabled rules."""
        matches = []
        
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            
            rule_matches = self._apply_rule(rule, file_path, content)
            matches.extend(rule_matches)
        
        return matches
    
    def analyze_repository(self, file_contents: Dict[str, str]) -> Dict[str, List[RuleMatch]]:
        """Analyze all files in repository."""
        results = {}
        for file_path, content in file_contents.items():
            if file_path.endswith('.py'):
                matches = self.analyze_file(file_path, content)
                if matches:
                    results[file_path] = matches
        return results
    
    def _apply_rule(self, rule: Rule, file_path: str, content: str) -> List[RuleMatch]:
        if rule.type == RuleType.AST_PATTERN:
            return self._apply_ast_rule(rule, file_path, content)
        elif rule.type == RuleType.REGEX_PATTERN:
            return self._apply_regex_rule(rule, file_path, content)
        elif rule.type == RuleType.METRIC_THRESHOLD:
            return self._apply_metric_rule(rule, file_path, content)
        elif rule.type == RuleType.COMPOSITE:
            return self._apply_composite_rule(rule, file_path, content)
        return []
    
    def _apply_ast_rule(self, rule: Rule, file_path: str, content: str) -> List[RuleMatch]:
        matches = []
        if not rule.ast_pattern:
            return matches
        
        try:
            tree = ast.parse(content)
            
            # Create visitor for this rule
            visitor = self._create_ast_visitor(rule)
            visitor.visit(tree)
            
            for match in visitor.matches:
                matches.append(RuleMatch(
                    rule_id=rule.id,
                    file_path=file_path,
                    line_start=match['line_start'],
                    line_end=match['line_end'],
                    column_start=match['column_start'],
                    column_end=match['column_end'],
                    message=match['message'] or rule.description,
                    severity=rule.severity,
                    code_snippet=match['code_snippet'],
                    metadata=match.get('metadata', {})
                ))
        except SyntaxError:
            pass
        
        return matches
    
    def _create_ast_visitor(self, rule: Rule):
        """Create AST visitor for rule."""
        pattern = rule.ast_pattern
        condition = rule.ast_condition
        
        class RuleVisitor(ast.NodeVisitor):
            def __init__(self):
                self.matches = []
            
            def visit(self, node):
                if node.__class__.__name__ == pattern:
                    # Evaluate condition if provided
                    should_match = True
                    if condition:
                        try:
                            # Create context with node attributes
                            ctx = {
                                'node': node,
                                'name': getattr(node, 'name', None),
                                'lineno': getattr(node, 'lineno', 0),
                                'end_lineno': getattr(node, 'end_lineno', 0),
                                'col_offset': getattr(node, 'col_offset', 0),
                                'end_col_offset': getattr(node, 'end_col_offset', 0),
                            }
                            should_match = eval(condition, {"__builtins__": {}}, ctx)
                        except Exception:
                            should_match = False
                    
                    if should_match:
                        lines = content.split('\n')
                        code_snippet = lines[node.lineno - 1] if node.lineno <= len(lines) else ''
                        self.matches.append({
                            'line_start': node.lineno,
                            'line_end': getattr(node, 'end_lineno', node.lineno),
                            'column_start': node.col_offset,
                            'column_end': getattr(node, 'end_col_offset', node.col_offset + len(code_snippet)),
                            'message': None,
                            'code_snippet': code_snippet.strip(),
                            'metadata': {'node_type': pattern}
                        })
                
                self.generic_visit(node)
        
        return RuleVisitor()
    
    def _apply_regex_rule(self, rule: Rule, file_path: str, content: str) -> List[RuleMatch]:
        matches = []
        if not rule.regex_pattern:
            return matches
        
        # Compile pattern if not cached
        cache_key = f"{rule.id}:{rule.regex_flags}"
        if cache_key not in self._compiled_patterns:
            self._compiled_patterns[cache_key] = re.compile(rule.regex_pattern, rule.regex_flags)
        
        pattern = self._compiled_patterns[cache_key]
        lines = content.split('\n')
        
        for match in pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            line_content = lines[line_num - 1] if line_num <= len(lines) else ''
            
            matches.append(RuleMatch(
                rule_id=rule.id,
                file_path=file_path,
                line_start=line_num,
                line_end=line_num,
                column_start=match.start() - content.rfind('\n', 0, match.start()),
                column_end=match.end() - content.rfind('\n', 0, match.start()),
                message=rule.description,
                severity=rule.severity,
                code_snippet=line_content.strip(),
                metadata={'match': match.group(0)}
            ))
        
        return matches
    
    def _apply_metric_rule(self, rule: Rule, file_path: str, content: str) -> List[RuleMatch]:
        # This would need metric computation - simplified for now
        return []
    
    def _apply_composite_rule(self, rule: Rule, file_path: str, content: str) -> List[RuleMatch]:
        matches = []
        if not rule.sub_rules:
            return matches
        
        sub_results = {}
        for sub_id in rule.sub_rules:
            sub_rule = self.rules.get(sub_id)
            if sub_rule:
                sub_results[sub_id] = self._apply_rule(sub_rule, file_path, content)
        
        if rule.composite_logic == "all":
            # All sub-rules must match
            if all(sub_results.values()):
                # Create a combined match
                matches.append(RuleMatch(
                    rule_id=rule.id,
                    file_path=file_path,
                    line_start=1,
                    line_end=1,
                    column_start=1,
                    column_end=1,
                    message=f"Composite rule matched: {rule.description}",
                    severity=rule.severity,
                    code_snippet="",
                    metadata={'sub_matches': {k: len(v) for k, v in sub_results.items()}}
                ))
        elif rule.composite_logic == "any":
            # At least one sub-rule matches
            if any(sub_results.values()):
                matches.append(RuleMatch(
                    rule_id=rule.id,
                    file_path=file_path,
                    line_start=1,
                    line_end=1,
                    column_start=1,
                    column_end=1,
                    message=f"Composite rule matched: {rule.description}",
                    severity=rule.severity,
                    code_snippet="",
                    metadata={'sub_matches': {k: len(v) for k, v in sub_results.items()}}
                ))
        elif rule.composite_logic == "none":
            # No sub-rules match
            if not any(sub_results.values()):
                matches.append(RuleMatch(
                    rule_id=rule.id,
                    file_path=file_path,
                    line_start=1,
                    line_end=1,
                    column_start=1,
                    column_end=1,
                    message=f"Composite rule matched (none): {rule.description}",
                    severity=rule.severity,
                    code_snippet="",
                    metadata={}
                ))
        
        return matches
    
    def export_rules(self, output_path: str):
        """Export rules to YAML."""
        data = {
            'rules': [
                {
                    'id': r.id,
                    'name': r.name,
                    'description': r.description,
                    'type': r.type.value,
                    'severity': r.severity.value,
                    'enabled': r.enabled,
                    'tags': r.tags,
                    'ast_pattern': r.ast_pattern,
                    'ast_condition': r.ast_condition,
                    'regex_pattern': r.regex_pattern,
                    'regex_flags': int(r.regex_flags) if r.regex_flags else 0,
                    'metric_name': r.metric_name,
                    'threshold': r.threshold,
                    'comparison': r.comparison,
                    'sub_rules': r.sub_rules,
                    'composite_logic': r.composite_logic,
                    'references': r.references,
                    'recommendation': r.recommendation
                }
                for r in self.rules.values()
            ]
        }
        
        with open(output_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    def create_default_rules(self):
        """Create a set of default useful rules."""
        defaults = [
            Rule(
                id="no-print-statements",
                name="No Print Statements in Production Code",
                description="Print statements should be replaced with proper logging",
                type=RuleType.AST_PATTERN,
                severity=RuleSeverity.LOW,
                ast_pattern="Call",
                ast_condition="isinstance(node.func, ast.Name) and node.func.id == 'print'",
                recommendation="Use logging module instead of print"
            ),
            Rule(
                id="no-bare-except",
                name="No Bare Except Clauses",
                description="Bare except clauses catch all exceptions including system exits",
                type=RuleType.AST_PATTERN,
                severity=RuleSeverity.MEDIUM,
                ast_pattern="ExceptHandler",
                ast_condition="node.type is None",
                recommendation="Specify exception types to catch"
            ),
            Rule(
                id="hardcoded-password",
                name="Hardcoded Password/Secret",
                description="Detect hardcoded passwords, secrets, or API keys",
                type=RuleType.REGEX_PATTERN,
                severity=RuleSeverity.HIGH,
                regex_pattern=r'(password|secret|api_key|token|private_key)\s*=\s*["\'][^"\']+["\']',
                regex_flags=re.IGNORECASE,
                recommendation="Use environment variables or secret management"
            ),
            Rule(
                id="sql-injection-risk",
                name="SQL Injection Risk",
                description="String formatting in SQL queries",
                type=RuleType.REGEX_PATTERN,
                severity=RuleSeverity.HIGH,
                regex_pattern=r'(execute|query|cursor)\s*\(\s*f["\'].*\{.*\}.*["\']',
                regex_flags=re.IGNORECASE,
                recommendation="Use parameterized queries"
            ),
            Rule(
                id="eval-usage",
                name="Eval Usage",
                description="Use of eval() function",
                type=RuleType.AST_PATTERN,
                severity=RuleSeverity.HIGH,
                ast_pattern="Call",
                ast_condition="isinstance(node.func, ast.Name) and node.func.id == 'eval'",
                recommendation="Use ast.literal_eval or safe alternatives"
            ),
            Rule(
                id="todo-comments",
                name="TODO/FIXME Comments",
                description="Track TODO and FIXME comments",
                type=RuleType.REGEX_PATTERN,
                severity=RuleSeverity.INFO,
                regex_pattern=r'#\s*(TODO|FIXME|HACK|BUG):',
                regex_flags=re.IGNORECASE,
                recommendation="Create issue tracker tickets for these"
            ),
            Rule(
                id="long-function-composite",
                name="Long Function with High Complexity",
                description="Function is both long and complex",
                type=RuleType.COMPOSITE,
                severity=RuleSeverity.MEDIUM,
                sub_rules=["long-function", "high-complexity"],
                composite_logic="all",
                recommendation="Refactor into smaller, focused functions"
            )
        ]
        
        for rule in defaults:
            self.add_rule(rule)


def create_rules_cli():
    """CLI for rule management."""
    import click
    
    @click.group()
    def rules():
        """Custom rule management."""
        pass
    
    @rules.command()
    @click.argument('rules_file', type=click.Path(exists=True))
    @click.argument('repo_path', type=click.Path(exists=True))
    @click.option('--output', '-o', type=click.Path(), help='Output file')
    def apply(rules_file, repo_path, output):
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
        else:
            console.print_json(json.dumps(all_matches, indent=2))
    
    @rules.command()
    @click.argument('output', type=click.Path())
    def create_defaults(output):
        """Create default rules file."""
        engine = RuleEngine()
        engine.create_default_rules()
        engine.export_rules(output)
        console.print(f"[green]Default rules exported to {output}[/green]")
    
    @rules.command()
    @click.argument('rules_file', type=click.Path(exists=True))
    def list_rules(rules_file):
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
    
    return rules


if __name__ == "__main__":
    import json
    import re
    from rich.console import Console
    from rich.table import Table
    console = Console()
    create_rules_cli()