"""
Enhanced Documentation Skill with comprehensive docstring analysis and README quality.
"""
import ast
import os
import re
from typing import List, Dict, Any
from dataclasses import dataclass
from pathlib import Path

from pro.config.loader import get_config
from pro.cache.manager import AnalysisCache


@dataclass
class DocumentationFinding:
    id: str
    category: str
    severity: str
    title: str
    description: str
    file_path: str
    line_start: int
    line_end: int
    metric_value: float
    threshold: float
    recommendation: str


class DocumentationSkill:
    def __init__(self, cache: AnalysisCache = None):
        self.cache = cache
        self.config = get_config().analysis.documentation

    def analyze(self, repo_path: str, file_contents: Dict[str, str]) -> Dict[str, Any]:
        config = self.config
        cache_key = "documentation_skill"

        if self.cache:
            cached = self.cache.get(repo_path, cache_key, config, file_contents)
            if cached:
                return cached

        findings = []
        metrics = {}

        py_files = {k: v for k, v in file_contents.items() if k.endswith('.py')}

        # Module-level docstrings
        module_docs = 0
        total_modules = 0

        # Function/class docstrings
        total_functions = 0
        documented_functions = 0
        total_classes = 0
        documented_classes = 0

        # Type hints
        typed_functions = 0

        # Docstring quality
        docstring_quality_scores = []

        for file_path, content in py_files.items():
            file_findings, file_metrics = self._analyze_file(file_path, content, config)
            findings.extend(file_findings)
            
            total_modules += 1
            if file_metrics.get('module_docstring'):
                module_docs += 1
                docstring_quality_scores.append(file_metrics.get('docstring_quality', 0))

            total_functions += file_metrics.get('total_functions', 0)
            documented_functions += file_metrics.get('documented_functions', 0)
            typed_functions += file_metrics.get('typed_functions', 0)

            total_classes += file_metrics.get('total_classes', 0)
            documented_classes += file_metrics.get('documented_classes', 0)

        # README analysis
        readme_findings, readme_metrics = self._analyze_readme(file_contents, config)
        findings.extend(readme_findings)
        metrics.update(readme_metrics)

        # License file
        license_findings = self._check_license_file(file_contents, config)
        findings.extend(license_findings)

        # Aggregate metrics
        metrics.update({
            "total_modules": total_modules,
            "documented_modules": module_docs,
            "module_doc_coverage": round(module_docs / max(total_modules, 1) * 100, 1),
            "total_functions": total_functions,
            "documented_functions": documented_functions,
            "function_doc_coverage": round(documented_functions / max(total_functions, 1) * 100, 1),
            "total_classes": total_classes,
            "documented_classes": documented_classes,
            "class_doc_coverage": round(documented_classes / max(total_classes, 1) * 100, 1),
            "typed_functions": typed_functions,
            "type_hint_coverage": round(typed_functions / max(total_functions, 1) * 100, 1),
            "avg_docstring_quality": round(sum(docstring_quality_scores) / max(len(docstring_quality_scores), 1), 1)
        })

        result = {
            "findings": [f.__dict__ for f in findings],
            "metrics": [{"name": k, "value": v} for k, v in metrics.items()],
            "score": self._calculate_score(findings, metrics)
        }

        if self.cache:
            self.cache.set(repo_path, cache_key, config, file_contents, result)

        return result

    def _analyze_file(self, file_path: str, content: str, config: Dict) -> tuple:
        findings = []
        metrics = {}

        try:
            tree = ast.parse(content)
            
            # Module docstring
            module_doc = ast.get_docstring(tree)
            metrics['module_docstring'] = module_doc is not None
            metrics['docstring_quality'] = self._score_docstring(module_doc) if module_doc else 0

            func_count = 0
            doc_func_count = 0
            typed_func_count = 0
            class_count = 0
            doc_class_count = 0

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_count += 1
                    docstring = ast.get_docstring(node)
                    if docstring:
                        doc_func_count += 1
                    else:
                        findings.append(DocumentationFinding(
                            id=f"missing_func_doc_{file_path}_{node.name}",
                            category="function_docstring",
                            severity="medium" if not node.name.startswith('_') else "low",
                            title=f"Missing function docstring: {node.name}",
                            description=f"Public function lacks docstring",
                            file_path=file_path,
                            line_start=node.lineno,
                            line_end=node.end_lineno or node.lineno,
                            metric_value=0,
                            threshold=1,
                            recommendation="Add docstring describing purpose, args, returns, and exceptions"
                        ))

                    # Type hints
                    if node.returns or any(arg.annotation for arg in node.args.args):
                        typed_func_count += 1

                elif isinstance(node, ast.ClassDef):
                    class_count += 1
                    docstring = ast.get_docstring(node)
                    if docstring:
                        doc_class_count += 1
                    else:
                        findings.append(DocumentationFinding(
                            id=f"missing_class_doc_{file_path}_{node.name}",
                            category="class_docstring",
                            severity="medium",
                            title=f"Missing class docstring: {node.name}",
                            description=f"Class lacks docstring",
                            file_path=file_path,
                            line_start=node.lineno,
                            line_end=node.end_lineno or node.lineno,
                            metric_value=0,
                            threshold=1,
                            recommendation="Add class docstring describing purpose and usage"
                        ))

            metrics.update({
                'total_functions': func_count,
                'documented_functions': doc_func_count,
                'typed_functions': typed_func_count,
                'total_classes': class_count,
                'documented_classes': doc_class_count
            })

        except Exception as e:
            metrics['error'] = str(e)

        return findings, metrics

    def _score_docstring(self, docstring: str) -> float:
        if not docstring:
            return 0.0
        
        score = 0.0
        lines = docstring.strip().split('\n')
        
        # Has summary line
        if lines and lines[0].strip():
            score += 20
        
        # Has blank line after summary
        if len(lines) > 1 and not lines[1].strip():
            score += 10
        
        # Has parameter docs
        if any(':param' in line or ':arg' in line for line in lines):
            score += 20
        
        # Has return doc
        if any(':return' in line or ':rtype' in line for line in lines):
            score += 20
        
        # Has raises doc
        if any(':raises' in line or ':exception' in line for line in lines):
            score += 10
        
        # Has examples
        if any('example' in line.lower() or '>>>' in line for line in lines):
            score += 10
        
        # Length
        if len(docstring) > 100:
            score += 10
        
        return min(100.0, score)

    def _analyze_readme(self, file_contents: Dict[str, str], config: Dict) -> tuple:
        findings = []
        metrics = {}

        readme_files = [f for f in file_contents.keys() 
                       if Path(f).name.lower().startswith('readme')]

        metrics['has_readme'] = len(readme_files) > 0

        if not readme_files:
            if config.get('require_readme', True):
                findings.append(DocumentationFinding(
                    id="missing_readme",
                    category="readme",
                    severity="high",
                    title="Missing README file",
                    description="Repository lacks a README.md",
                    file_path=".",
                    line_start=1,
                    line_end=1,
                    metric_value=0,
                    threshold=1,
                    recommendation="Add README with project overview, installation, usage, and contributing"
                ))
            return findings, metrics

        readme_path = readme_files[0]
        content = file_contents[readme_path]
        
        # Quality scoring
        quality_score = 0
        sections_found = []

        required_sections = config.get('readme_min_sections', 5)
        section_patterns = {
            'description': r'(description|overview|about)',
            'installation': r'(install|setup|getting started)',
            'usage': r'(usage|example|how to)',
            'api': r'(api|reference|documentation)',
            'contributing': r'(contribut|develop)',
            'license': r'(license|legal)',
            'authors': r'(author|maintainer|credit)',
            'changelog': r'(changelog|history|releases)'
        }

        content_lower = content.lower()
        for section, pattern in section_patterns.items():
            if re.search(pattern, content_lower):
                sections_found.append(section)
                quality_score += 10

        # Code examples
        if '```' in content:
            quality_score += 10
            sections_found.append('code_examples')

        # Badges
        if re.search(r'!\[.*\]\(.*\)', content):
            quality_score += 5
            sections_found.append('badges')

        # Length
        if len(content) > 500:
            quality_score += 10
        elif len(content) > 200:
            quality_score += 5

        metrics.update({
            'readme_file': readme_path,
            'readme_length': len(content),
            'readme_sections': sections_found,
            'readme_section_count': len(sections_found),
            'readme_quality_score': min(100, quality_score)
        })

        if len(sections_found) < required_sections:
            findings.append(DocumentationFinding(
                id=f"readme_incomplete_{readme_path}",
                category="readme",
                severity="medium",
                title="Incomplete README",
                description=f"README missing recommended sections (found {len(sections_found)}/{required_sections})",
                file_path=readme_path,
                line_start=1,
                line_end=1,
                metric_value=len(sections_found),
                threshold=required_sections,
                recommendation=f"Add missing sections: {set(section_patterns.keys()) - set(sections_found)}"
            ))

        return findings, metrics

    def _check_license_file(self, file_contents: Dict[str, str], config: Dict) -> List[DocumentationFinding]:
        findings = []
        license_files = [f for f in file_contents.keys() 
                        if Path(f).name.lower() in ('license', 'license.txt', 'license.md', 'copying')]
        
        if not license_files:
            findings.append(DocumentationFinding(
                id="missing_license",
                category="license",
                severity="medium",
                title="Missing LICENSE file",
                description="Repository does not have a license file",
                file_path=".",
                line_start=1,
                line_end=1,
                metric_value=0,
                threshold=1,
                recommendation="Add LICENSE file with appropriate open source license"
            ))
        
        return findings

    def _calculate_score(self, findings: List[DocumentationFinding], metrics: Dict) -> float:
        score = 0.0

        # README (30 points)
        if metrics.get('has_readme'):
            score += 15
            quality = metrics.get('readme_quality_score', 0)
            score += min(15, quality * 0.3)

        # Module docs (15 points)
        score += min(15, metrics.get('module_doc_coverage', 0) * 0.15)

        # Function docs (25 points)
        score += min(25, metrics.get('function_doc_coverage', 0) * 0.25)

        # Class docs (15 points)
        score += min(15, metrics.get('class_doc_coverage', 0) * 0.15)

        # Type hints (15 points)
        score += min(15, metrics.get('type_hint_coverage', 0) * 0.15)

        # Penalties for findings
        for f in findings:
            if f.severity == "high":
                score -= 10
            elif f.severity == "medium":
                score -= 5
            elif f.severity == "low":
                score -= 2

        return max(0, min(100, round(score, 1)))