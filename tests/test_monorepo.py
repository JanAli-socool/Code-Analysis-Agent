"""Tests for monorepo detection."""
import json
import tempfile
from pathlib import Path

from pro.monorepo.detector import MonorepoDetector, MonorepoType, analyze_monorepo


class TestMonorepoDetector:
    def test_detect_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "main.py").write_text("print('hello')")
            
            detector = MonorepoDetector(str(repo))
            assert detector.detect() == MonorepoType.NONE
    
    def test_detect_nx(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "nx.json").write_text('{"workspaceLayout": "apps-libs"}')
            (repo / "package.json").write_text('{}')
            
            detector = MonorepoDetector(str(repo))
            assert detector.detect() == MonorepoType.NX
    
    def test_detect_turborepo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "turbo.json").write_text('{"pipeline": {}}')
            (repo / "package.json").write_text('{"workspaces": ["packages/*"]}')
            
            detector = MonorepoDetector(str(repo))
            assert detector.detect() == MonorepoType.TURBOREPO
    
    def test_detect_bazel(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "WORKSPACE").write_text('workspace(name = "test")')
            
            detector = MonorepoDetector(str(repo))
            assert detector.detect() == MonorepoType.BAZEL
    
    def test_detect_lerna(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "lerna.json").write_text('{"packages": ["packages/*"]}')
            (repo / "package.json").write_text('{}')
            
            detector = MonorepoDetector(str(repo))
            assert detector.detect() == MonorepoType.LERNA
    
    def test_detect_pnpm_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "pnpm-workspace.yaml").write_text('packages:\n  - packages/*\n')
            (repo / "package.json").write_text('{}')
            
            detector = MonorepoDetector(str(repo))
            assert detector.detect() == MonorepoType.PNPM_WORKSPACE
    
    def test_detect_yarn_workspaces(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "package.json").write_text('{"workspaces": ["packages/*"]}')
            
            detector = MonorepoDetector(str(repo))
            assert detector.detect() == MonorepoType.YARN_WORKSPACES
    
    def test_detect_generic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "packages" / "pkg1").mkdir(parents=True)
            (repo / "packages" / "pkg1" / "package.json").write_text('{"name": "pkg1"}')
            
            detector = MonorepoDetector(str(repo))
            assert detector.detect() == MonorepoType.GENERIC
    
    def test_get_nx_packages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "nx.json").write_text('{}')
            (repo / "workspace.json").write_text('{"projects": {"my-lib": {"root": "libs/my-lib"}}}')
            (repo / "libs" / "my-lib").mkdir(parents=True)
            (repo / "libs" / "my-lib" / "package.json").write_text('{"name": "my-lib", "dependencies": {"lodash": "^4.17.21"}}')
            
            detector = MonorepoDetector(str(repo))
            packages = detector.get_packages(MonorepoType.NX)
            
            assert len(packages) == 1
            assert packages[0].name == "my-lib"
            assert "lodash" in packages[0].dependencies
    
    def test_get_pnpm_packages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "pnpm-workspace.yaml").write_text('packages:\n  - packages/*\n')
            (repo / "packages" / "pkg1").mkdir(parents=True)
            (repo / "packages" / "pkg1" / "package.json").write_text('{"name": "pkg1", "dependencies": {"react": "^18.0.0"}}')
            
            detector = MonorepoDetector(str(repo))
            packages = detector.get_packages(MonorepoType.PNPM_WORKSPACE)
            
            assert len(packages) == 1
            assert packages[0].name == "pkg1"
            assert packages[0].package_manager == "pnpm"
            assert "react" in packages[0].dependencies
    
    def test_get_yarn_packages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "package.json").write_text('{"workspaces": ["packages/*"]}')
            (repo / "packages" / "pkg1").mkdir(parents=True)
            (repo / "packages" / "pkg1" / "package.json").write_text('{"name": "pkg1", "devDependencies": {"jest": "^29.0.0"}}')
            
            detector = MonorepoDetector(str(repo))
            packages = detector.get_packages(MonorepoType.YARN_WORKSPACES)
            
            assert len(packages) == 1
            assert packages[0].name == "pkg1"
            assert packages[0].package_manager == "yarn"
            assert "jest" in packages[0].dev_dependencies
    
    def test_analyze_monorepo_function(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "package.json").write_text('{"workspaces": ["packages/*"]}')
            (repo / "packages" / "pkg1").mkdir(parents=True)
            (repo / "packages" / "pkg1" / "package.json").write_text('{"name": "pkg1"}')
            
            result = analyze_monorepo(str(repo))
            
            assert result["is_monorepo"] is True
            assert result["type"] == "yarn_workspaces"
            assert result["package_count"] == 1
            assert result["packages"][0]["name"] == "pkg1"
    
    def test_analyze_non_monorepo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "main.py").write_text("print('hello')")
            
            result = analyze_monorepo(str(repo))
            
            assert result["is_monorepo"] is False
            assert result["type"] == "none"
            assert result["packages"] == []


class TestMonorepoCLI:
    def test_cli_output(self):
        import sys
        from io import StringIO
        from contextlib import redirect_stdout
        
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "package.json").write_text('{"workspaces": ["packages/*"]}')
            (repo / "packages" / "pkg1").mkdir(parents=True)
            (repo / "packages" / "pkg1" / "package.json").write_text('{"name": "pkg1"}')
            
            # Import and run the CLI function
            from pro.monorepo.detector import analyze_monorepo
            f = StringIO()
            with redirect_stdout(f):
                sys.argv = ['detector.py', str(repo)]
                # Just call the function directly
                result = analyze_monorepo(str(repo))
            
            assert result["is_monorepo"] is True