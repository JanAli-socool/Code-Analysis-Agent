"""Tests for SBOM Generator."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from pro.sbom.generator import SBOMGenerator, SBOMFormat


class TestSBOMGenerator:
    def test_get_dependencies_python(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "requirements.txt").write_text("requests==2.25.1\nflask>=1.0\n")
            (repo / "pyproject.toml").write_text("""
[project]
dependencies = ["pydantic==2.0", "httpx>=0.24"]
""")
            
            gen = SBOMGenerator(str(repo))
            deps = gen.get_dependencies()
            
            assert len(deps) >= 3
            names = {d['name'] for d in deps}
            assert 'requests' in names
            assert 'flask' in names
            assert 'pydantic' in names
            assert 'httpx' in names

    def test_get_dependencies_nodejs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "package.json").write_text(json.dumps({
                "name": "test",
                "dependencies": {"express": "^4.18.0", "lodash": "4.17.21"},
                "devDependencies": {"jest": "^29.0.0"}
            }))
            
            gen = SBOMGenerator(str(repo))
            deps = gen.get_dependencies()
            
            names = {d['name'] for d in deps}
            assert 'express' in names
            assert 'lodash' in names
            assert 'jest' in names

    @patch('pro.sbom.generator.SBOMGenerator._detect_license')
    def test_generate_cyclonedx_json(self, mock_detect):
        mock_detect.return_value = [{"license": {"id": "MIT", "name": "MIT"}}]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "requirements.txt").write_text("requests==2.25.1\n")
            
            gen = SBOMGenerator(str(repo))
            deps = gen.get_dependencies()
            sbom = gen.generate_cyclonedx_json(deps)
            
            assert sbom['bomFormat'] == 'CycloneDX'
            assert sbom['specVersion'] == '1.5'
            assert 'components' in sbom
            assert len(sbom['components']) >= 1
            
            comp = sbom['components'][0]
            assert 'name' in comp
            assert 'version' in comp
            assert 'licenses' in comp
            assert 'purl' in comp

    @patch('pro.sbom.generator.SBOMGenerator._detect_license')
    def test_generate_spdx_json(self, mock_detect):
        mock_detect.return_value = [{"license": {"id": "MIT", "name": "MIT"}}]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "requirements.txt").write_text("requests==2.25.1\n")
            
            gen = SBOMGenerator(str(repo))
            deps = gen.get_dependencies()
            sbom = gen.generate_spdx_json(deps)
            
            assert sbom['spdxVersion'] == 'SPDX-2.3'
            assert 'packages' in sbom
            assert len(sbom['packages']) >= 1

    @patch('pro.sbom.generator.SBOMGenerator._detect_license')
    def test_save_cyclonedx(self, mock_detect):
        mock_detect.return_value = [{"license": {"id": "MIT", "name": "MIT"}}]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "requirements.txt").write_text("requests==2.25.1\n")
            output = Path(tmpdir) / "sbom.json"
            
            gen = SBOMGenerator(str(repo))
            gen.save(str(output), SBOMFormat.CYCLONEDX_JSON)
            
            assert output.exists()
            data = json.loads(output.read_text())
            assert data['bomFormat'] == 'CycloneDX'

    @patch('pro.sbom.generator.SBOMGenerator._detect_license')
    def test_license_detection_in_cyclonedx(self, mock_detect):
        mock_detect.return_value = [{"license": {"id": "Apache-2.0", "name": "Apache-2.0"}}]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "requirements.txt").write_text("requests==2.25.1\n")
            
            gen = SBOMGenerator(str(repo))
            deps = gen.get_dependencies()
            sbom = gen.generate_cyclonedx_json(deps)
            
            for comp in sbom['components']:
                assert 'licenses' in comp
                assert isinstance(comp['licenses'], list)
                if comp['licenses']:
                    lic = comp['licenses'][0]
                    assert 'license' in lic
                    assert 'id' in lic['license']

    def test_parse_pyproject_poetry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "pyproject.toml").write_text("""
[tool.poetry]
name = "test"
dependencies = { "requests" = "^2.25", "pydantic" = {version = "^2.0", extras = ["email"]} }
""")
            
            gen = SBOMGenerator(str(repo))
            deps = gen.get_dependencies()
            
            names = {d['name'] for d in deps}
            assert 'requests' in names
            assert 'pydantic' in names

    def test_parse_pipfile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "Pipfile").write_text("""
[packages]
requests = "==2.25.1"
flask = "*"

[dev-packages]
pytest = ">=6.0"
""")
            
            gen = SBOMGenerator(str(repo))
            deps = gen.get_dependencies()
            
            names = {d['name'] for d in deps}
            assert 'requests' in names
            assert 'flask' in names
            assert 'pytest' in names


class TestLicenseNormalization:
    def test_normalize_common_licenses(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            gen = SBOMGenerator(str(repo))
            
            assert gen._normalize_spdx_license('MIT') == 'MIT'
            assert gen._normalize_spdx_license('Apache-2.0') == 'Apache-2.0'
            assert gen._normalize_spdx_license('apache 2.0') == 'Apache-2.0'
            assert gen._normalize_spdx_license('BSD-3-Clause') == 'BSD-3-Clause'
            # GPL variants get uppercased since not in mapping
            assert gen._normalize_spdx_license('GPL-3.0-only') == 'GPL-3.0-ONLY'
            assert gen._normalize_spdx_license('unknown-license') == 'UNKNOWN-LICENSE'