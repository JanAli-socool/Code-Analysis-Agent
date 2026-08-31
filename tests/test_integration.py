"""Integration tests for the orchestrator and CLI."""
import json
import tempfile
from pathlib import Path

from pro.orchestrator import ProfessionalOrchestrator
from pro.config.loader import get_config


class TestOrchestrator:
    def test_analyze_good_repo(self):
        orchestrator = ProfessionalOrchestrator("test_repos/good_repo")
        result = orchestrator.run_analysis()
        
        assert result.overall_score > 70
        assert result.risk_level in ('low', 'medium', 'high', 'critical')
        assert len(result.category_scores) == 12
        assert result.files_analyzed > 0
    
    def test_analyze_bad_repo(self):
        orchestrator = ProfessionalOrchestrator("test_repos/bad_repo")
        result = orchestrator.run_analysis()
        
        assert result.overall_score < 80
        assert result.risk_level in ('medium', 'high', 'critical')
        assert len(result.category_scores) == 12
    
    def test_category_scores_present(self):
        orchestrator = ProfessionalOrchestrator("test_repos/good_repo")
        result = orchestrator.run_analysis()
        
        categories = {c.name for c in result.category_scores}
        expected = {'complexity', 'security', 'testing', 'architecture', 
                    'maintainability', 'dependencies', 'documentation', 
                    'git_history', 'javascript', 'java', 'go', 'cpp'}
        assert categories == expected
    
    def test_strengths_weaknesses(self):
        orchestrator = ProfessionalOrchestrator("test_repos/bad_repo")
        result = orchestrator.run_analysis()
        
        assert isinstance(result.strengths, list)
        assert isinstance(result.weaknesses, list)
    
    def test_config_weights_applied(self):
        config = get_config()
        config.analysis.weights['security'] = 10.0  # Very high weight
        
        orchestrator = ProfessionalOrchestrator("test_repos/bad_repo", config)
        result = orchestrator.run_analysis()
        
        # Security should heavily influence score
        sec_cat = next(c for c in result.category_scores if c.name == 'security')
        assert sec_cat.weight == 10.0


class TestLanguageDetection:
    def test_detects_python(self):
        orchestrator = ProfessionalOrchestrator("test_repos/good_repo")
        orchestrator.load_repository()
        
        langs = orchestrator.language_detector.detect_repository_languages(orchestrator.repo_path, orchestrator.file_contents)
        assert 'python' in str(langs).lower()
    
    def test_detects_javascript(self):
        orchestrator = ProfessionalOrchestrator("test_repos/js_repo")
        orchestrator.load_repository()
        
        langs = orchestrator.language_detector.detect_repository_languages(orchestrator.repo_path, orchestrator.file_contents)
        assert 'javascript' in str(langs).lower()


class TestIncrementalAnalysis:
    def test_incremental_analyzer_creation(self):
        from pro.execution.incremental import IncrementalAnalyzer
        
        analyzer = IncrementalAnalyzer("test_repos/good_repo")
        assert analyzer.repo_path.exists()


class TestComparison:
    def test_comparison_engine(self):
        from pro.comparison.diff import ComparisonEngine
        
        engine = ComparisonEngine()
        # Basic test - just verify it initializes
        assert engine is not None


class TestRulesEngine:
    def test_rules_engine_creation(self):
        from pro.rules.engine import RuleEngine
        
        engine = RuleEngine()
        assert engine is not None
    
    def test_default_rules_created(self):
        from pro.rules.engine import RuleEngine
        
        engine = RuleEngine()
        engine.create_default_rules()
        
        rules = engine.list_rules()
        assert len(rules) > 0
        
        # Check for security-related rules
        sec_rules = [r for r in rules if 'password' in r.id or 'sql' in r.id or 'eval' in r.id]
        assert len(sec_rules) > 0


class TestBenchmarking:
    def test_benchmark_runner(self):
        from pro.benchmarks.runner import BenchmarkRunner
        
        runner = BenchmarkRunner()
        assert runner is not None


class TestAPIModels:
    def test_analysis_request(self):
        from pro.api.main import AnalysisRequest
        
        req = AnalysisRequest(repo_path="test_repos/good_repo")
        assert req.repo_path == "test_repos/good_repo"
    
    def test_analysis_response(self):
        from pro.api.main import AnalysisResponse
        
        resp = AnalysisResponse(
            job_id="test-123",
            status="completed",
            result={"overall_score": 85.0},
            created_at="2024-01-01T00:00:00Z"
        )
        assert resp.job_id == "test-123"


class TestConfigLoader:
    def test_config_loaded(self):
        config = get_config()
        
        assert config.analysis.weights is not None
        assert 'complexity' in config.analysis.weights
        assert config.execution.cache_enabled is not None
        assert config.output.formats is not None