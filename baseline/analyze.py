#!/usr/bin/env python3
"""
Baseline Solution: Simple Repository Quality Analyzer
A single script that runs basic static analysis on a repository.
"""

import os
import json
import subprocess
import ast
from pathlib import Path
from typing import Dict, Any, List
import radon.complexity as radon_cc
import radon.metrics as radon_metrics
from radon.raw import analyze as radon_raw


class BaselineAnalyzer:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.results = {}

    def analyze(self) -> Dict[str, Any]:
        """Run all baseline analyses."""
        self.results = {
            "repository": str(self.repo_path),
            "files_analyzed": 0,
            "total_lines": 0,
            "code_lines": 0,
            "comment_lines": 0,
            "blank_lines": 0,
            "avg_complexity": 0.0,
            "max_complexity": 0,
            "functions": 0,
            "classes": 0,
            "imports": [],
            "issues": [],
            "score": 0.0
        }

        python_files = list(self.repo_path.rglob("*.py"))
        self.results["files_analyzed"] = len(python_files)

        all_complexities = []
        total_functions = 0
        total_classes = 0
        all_imports = set()

        for py_file in python_files:
            self._analyze_file(py_file, all_complexities, all_imports, total_functions, total_classes)

        if all_complexities:
            self.results["avg_complexity"] = sum(all_complexities) / len(all_complexities)
            self.results["max_complexity"] = max(all_complexities)

        self.results["functions"] = total_functions
        self.results["classes"] = total_classes
        self.results["imports"] = list(all_imports)[:20]

        self._calculate_score()
        return self.results

    def _analyze_file(self, file_path: Path, all_complexities: List, all_imports: set, total_functions: int, total_classes: int):
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            self.results["total_lines"] += len(lines)
            self.results["code_lines"] += sum(1 for l in lines if l.strip() and not l.strip().startswith('#'))
            self.results["comment_lines"] += sum(1 for l in lines if l.strip().startswith('#'))
            self.results["blank_lines"] += sum(1 for l in lines if not l.strip())

            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    total_functions += 1
                elif isinstance(node, ast.ClassDef):
                    total_classes += 1
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        all_imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        all_imports.add(node.module)

            try:
                cc_results = radon_cc.cc_visit(content)
                for item in cc_results:
                    all_complexities.append(item.complexity)
            except Exception:
                pass

        except Exception as e:
            self.results["issues"].append(f"{file_path}: {str(e)}")

    def _calculate_score(self):
        score = 100.0
        
        if self.results["avg_complexity"] > 10:
            score -= 20
        elif self.results["avg_complexity"] > 5:
            score -= 10
            
        if self.results["max_complexity"] > 20:
            score -= 15
            
        comment_ratio = self.results["comment_lines"] / max(self.results["code_lines"], 1)
        if comment_ratio < 0.1:
            score -= 10
        elif comment_ratio < 0.2:
            score -= 5
            
        if self.results["files_analyzed"] == 0:
            score = 0
            
        self.results["score"] = max(0, min(100, score))


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Baseline Repository Analyzer")
    parser.add_argument("repo_path", help="Path to repository to analyze")
    parser.add_argument("--output", "-o", help="Output JSON file")
    args = parser.parse_args()

    analyzer = BaselineAnalyzer(args.repo_path)
    results = analyzer.analyze()

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
    else:
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()