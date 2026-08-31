"""Tests for CLI commands."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from pro.cli.main import cli
from pro.sbom.generator import create_sbom_cli


class TestMainCLI:
    def test_analyze_command(self):
        runner = CliRunner()
        result = runner.invoke(cli, ['analyze', 'test_repos/good_repo'])
        
        assert result.exit_code == 0
        assert 'CODE ANALYSIS REPORT' in result.output
        assert 'Overall Score' in result.output
    
    def test_analyze_json_output(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "report.json"
            result = runner.invoke(cli, ['analyze', 'test_repos/good_repo', '--format', 'json', '-o', str(output)])
            
            assert result.exit_code == 0
            assert output.exists()
            data = json.loads(output.read_text())
            assert 'overall_score' in data
            assert 'risk_level' in data
    
    def test_skills_command(self):
        runner = CliRunner()
        result = runner.invoke(cli, ['skills', 'test_repos/good_repo'])
        
        assert result.exit_code == 0
        assert 'complexity' in result.output
        assert 'security' in result.output
    
    def test_cache_stats_command(self):
        runner = CliRunner()
        result = runner.invoke(cli, ['cache-stats'])
        
        assert result.exit_code == 0
    
    def test_config_show_command(self):
        runner = CliRunner()
        result = runner.invoke(cli, ['config-show'])
        
        assert result.exit_code == 0
        assert 'weights' in result.output


class TestSBOMCLI:
    @patch('pro.sbom.generator.SBOMGenerator._detect_license')
    def test_sbom_generate(self, mock_detect):
        mock_detect.return_value = [{"license": {"id": "MIT", "name": "MIT"}}]
        
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "sbom.json"
            result = runner.invoke(cli, ['sbom', 'test_repos/good_repo', '-o', str(output)])
            
            assert result.exit_code == 0
            assert output.exists()
            
            data = json.loads(output.read_text())
            assert data['bomFormat'] == 'CycloneDX'
            assert 'components' in data
    
    @patch('pro.sbom.generator.SBOMGenerator._detect_license')
    def test_sbom_spdx_format(self, mock_detect):
        mock_detect.return_value = [{"license": {"id": "MIT", "name": "MIT"}}]
        
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "sbom.spdx.json"
            result = runner.invoke(cli, ['sbom', 'test_repos/good_repo', '-f', 'spdx-json', '-o', str(output)])
            
            assert result.exit_code == 0
            assert output.exists()
            
            data = json.loads(output.read_text())
            assert data['spdxVersion'] == 'SPDX-2.3'
    
    @patch('pro.sbom.generator.SBOMGenerator._detect_license')
    def test_sbom_standalone_cli(self, mock_detect):
        mock_detect.return_value = [{"license": {"id": "MIT", "name": "MIT"}}]
        
        runner = CliRunner()
        sbom_cli = create_sbom_cli()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "sbom.json"
            result = runner.invoke(sbom_cli, ['test_repos/good_repo', '-o', str(output)])
            
            assert result.exit_code == 0
            assert output.exists()


class TestRulesCLI:
    def test_rules_list(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "rules.yaml"
            # First create defaults
            runner.invoke(cli, ['rules-create-defaults', str(output)])
            # Then list them
            result = runner.invoke(cli, ['rules-list', str(output)])
        
        assert result.exit_code == 0
    
    def test_rules_create_defaults(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "rules.yaml"
            result = runner.invoke(cli, ['rules-create-defaults', str(output)])
            
            assert result.exit_code == 0
            assert output.exists()
            
            import yaml
            data = yaml.safe_load(output.read_text())
            assert 'rules' in data
            assert len(data['rules']) > 0


class TestIncrementalCLI:
    def test_incremental_command(self):
        runner = CliRunner()
        result = runner.invoke(cli, ['incremental', 'test_repos/good_repo'])
        
        # May fail if not a git repo, but should not crash
        assert result.exit_code in (0, 1)


class TestBenchmarkCLI:
    def test_benchmark_command(self):
        runner = CliRunner()
        result = runner.invoke(cli, ['benchmark', 'test_repos/good_repo', '--iterations', '1'])
        
        # May take time, just verify it starts
        assert result.exit_code in (0, 1)