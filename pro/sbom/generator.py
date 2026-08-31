"""
SBOM Generation - CycloneDX and SPDX formats.
"""
import json
import subprocess
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class SBOMFormat(Enum):
    CYCLONEDX_JSON = "cyclonedx-json"
    CYCLONEDX_XML = "cyclonedx-xml"
    SPDX_JSON = "spdx-json"
    SPDX_TAG_VALUE = "spdx-tag-value"


@dataclass
class Component:
    name: str
    version: str
    purl: Optional[str] = None
    description: Optional[str] = None
    licenses: List[Dict[str, str]] = field(default_factory=list)
    hashes: List[Dict[str, str]] = field(default_factory=list)
    external_refs: List[Dict[str, str]] = field(default_factory=list)
    scope: str = "required"  # required, optional, excluded


class SBOMGenerator:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
    
    def get_dependencies(self) -> List[Dict[str, Any]]:
        """Get all dependencies from various sources."""
        deps = []
        
        # 1. Python dependencies (requirements, pyproject, poetry, pipfile)
        deps.extend(self._get_python_deps())
        
        # 2. Node.js dependencies
        deps.extend(self._get_node_deps())
        
        # 3. System packages (if in container)
        deps.extend(self._get_system_deps())
        
        return deps
    
    def _get_python_deps(self) -> List[Dict[str, Any]]:
        deps = []
        
        # Try pip list --format=json first (installed packages)
        try:
            result = subprocess.run(
                ['python', '-m', 'pip', 'list', '--format=json'],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                for pkg in json.loads(result.stdout):
                    deps.append({
                        'name': pkg['name'],
                        'version': pkg['version'],
                        'type': 'pypi',
                        'purl': f"pkg:pypi/{pkg['name'].lower()}@{pkg['version']}"
                    })
        except Exception:
            pass
        
        # Parse requirement files
        req_files = [
            'requirements.txt', 'requirements-dev.txt', 'requirements-test.txt',
            'setup.py', 'pyproject.toml', 'poetry.lock', 'Pipfile', 'Pipfile.lock'
        ]
        
        for req_file in req_files:
            path = self.repo_path / req_file
            if path.exists():
                deps.extend(self._parse_req_file(path))
        
        return deps
    
    def _parse_req_file(self, path: Path) -> List[Dict[str, Any]]:
        deps = []
        name = path.name.lower()
        
        try:
            content = path.read_text()
            
            if name == 'pyproject.toml':
                deps.extend(self._parse_pyproject(content))
            elif name == 'poetry.lock':
                deps.extend(self._parse_poetry_lock(content))
            elif name in ('pipfile', 'pipfile.lock'):
                deps.extend(self._parse_pipfile(content))
            elif name == 'setup.py':
                deps.extend(self._parse_setup_py(content))
            else:
                # requirements.txt format
                deps.extend(self._parse_requirements(content))
        except Exception:
            pass
        
        return deps
    
    def _parse_requirements(self, content: str) -> List[Dict[str, Any]]:
        deps = []
        import re
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                # Handle: package==1.0.0, package>=1.0, package~=1.0, package[extra]==1.0
                match = re.match(r'^([a-zA-Z0-9_\-\.]+)(\[[^\]]+\])?([=<>!~]+.*)?', line)
                if match:
                    name = match.group(1).lower()
                    extras = match.group(2) or ''
                    specifier = match.group(3) or ''
                    version = specifier.lstrip('=<>!~') if specifier else 'unknown'
                    deps.append({
                        'name': name + extras,
                        'version': version,
                        'type': 'pypi',
                        'purl': f"pkg:pypi/{name}{extras}@{version}"
                    })
        return deps
    
    def _parse_pyproject(self, content: str) -> List[Dict[str, Any]]:
        deps = []
        try:
            import tomllib
            data = tomllib.loads(content)
            
            # [project] dependencies
            if 'project' in data:
                for dep in data['project'].get('dependencies', []):
                    deps.append(self._parse_req_line(dep))
                for extra_name, extra_deps in data['project'].get('optional-dependencies', {}).items():
                    for dep in extra_deps:
                        d = self._parse_req_line(dep)
                        d['extras'] = [extra_name]
                        deps.append(d)
            
            # [tool.poetry] dependencies
            if 'tool' in data and 'poetry' in data['tool']:
                poetry = data['tool']['poetry']
                for name, spec in poetry.get('dependencies', {}).items():
                    if name != 'python':
                        deps.append(self._parse_poetry_dep(name, spec))
                for group_name, group_deps in poetry.get('group', {}).items():
                    for name, spec in group_deps.get('dependencies', {}).items():
                        d = self._parse_poetry_dep(name, spec)
                        d['extras'] = [group_name]
                        deps.append(d)
        except Exception:
            pass
        return deps
    
    def _parse_poetry_dep(self, name: str, spec: Any) -> Dict[str, Any]:
        if isinstance(spec, str):
            version = spec
        elif isinstance(spec, dict):
            version = spec.get('version', 'unknown')
        else:
            version = 'unknown'
        return {
            'name': name.lower(),
            'version': version.lstrip('^~>=<'),
            'type': 'pypi',
            'purl': f"pkg:pypi/{name.lower()}@{version.lstrip('^~>=<')}"
        }
    
    def _parse_poetry_lock(self, content: str) -> List[Dict[str, Any]]:
        deps = []
        try:
            data = json.loads(content)
            for pkg in data.get('package', []):
                deps.append({
                    'name': pkg['name'].lower(),
                    'version': pkg['version'],
                    'type': 'pypi',
                    'purl': f"pkg:pypi/{pkg['name'].lower()}@{pkg['version']}"
                })
        except Exception:
            pass
        return deps
    
    def _parse_pipfile(self, content: str) -> List[Dict[str, Any]]:
        deps = []
        try:
            import tomllib
            data = tomllib.loads(content)
            for section in ['packages', 'dev-packages']:
                for name, spec in data.get(section, {}).items():
                    if isinstance(spec, str):
                        version = spec
                    elif isinstance(spec, dict):
                        version = spec.get('version', 'unknown')
                    else:
                        version = 'unknown'
                    deps.append({
                        'name': name.lower(),
                        'version': version.lstrip('^~>=<') if isinstance(spec, str) else 'unknown',
                        'type': 'pypi',
                        'purl': f"pkg:pypi/{name.lower()}@{version.lstrip('^~>=<') if isinstance(spec, str) else 'unknown'}"
                    })
        except Exception:
            pass
        return deps
    
    def _parse_setup_py(self, content: str) -> List[Dict[str, Any]]:
        deps = []
        import re
        # Find install_requires
        match = re.search(r'install_requires\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if match:
            reqs = match.group(1)
            for line in reqs.split(','):
                line = line.strip().strip('\'"')
                if line:
                    deps.append(self._parse_req_line(line))
        return deps
    
    def _parse_req_line(self, line: str) -> Dict[str, Any]:
        import re
        match = re.match(r'^([a-zA-Z0-9_\-\.]+)([=<>!~]+.*)?', line.strip())
        if match:
            name = match.group(1).lower()
            version = match.group(2).lstrip('=<>!~') if match.group(2) else 'unknown'
        else:
            name = line.strip().lower()
            version = 'unknown'
        return {
            'name': name,
            'version': version,
            'type': 'pypi',
            'purl': f"pkg:pypi/{name}@{version}"
        }
    
    def _get_node_deps(self) -> List[Dict[str, Any]]:
        deps = []
        package_json = self.repo_path / 'package.json'
        if package_json.exists():
            try:
                data = json.loads(package_json.read_text())
                for name, version in {**data.get('dependencies', {}), **data.get('devDependencies', {})}.items():
                    deps.append({
                        'name': name,
                        'version': version.lstrip('^~>=<'),
                        'type': 'npm',
                        'purl': f"pkg:npm/{name}@{version.lstrip('^~>=<')}"
                    })
            except Exception:
                pass
        return deps
    
    def _get_system_deps(self) -> List[Dict[str, Any]]:
        deps = []
        # Check for common system package files
        for fname in ['Dockerfile', 'dockerfile', 'Dockerfile.*']:
            for path in self.repo_path.glob(fname):
                try:
                    content = path.read_text()
                    import re
                    # Find apt-get install, apk add, yum install
                    for match in re.finditer(r'(apt-get install|apk add|yum install)\s+([^\n&|;]+)', content):
                        pkgs = match.group(2).split()
                        for pkg in pkgs:
                            pkg = pkg.strip()
                            if pkg and not pkg.startswith('-'):
                                deps.append({
                                    'name': pkg,
                                    'version': 'system',
                                    'type': 'system',
                                    'purl': f"pkg:generic/{pkg}"
                                })
                except Exception:
                    pass
        return deps
    
    def _detect_license(self, component: Dict) -> List[Dict[str, str]]:
        """Detect license for a component using multiple sources."""
        licenses = []
        name = component.get('name', '')
        ptype = component.get('type', '')
        
        try:
            if ptype in ('pypi', 'npm'):
                # Try to get license from package manager
                if ptype == 'pypi':
                    result = subprocess.run(
                        ['python', '-m', 'pip', 'show', component['name']],
                        capture_output=True, text=True, timeout=10
                    )
                else:
                    result = subprocess.run(
                        ['npm', 'view', component['name'], 'license'],
                        capture_output=True, text=True, timeout=10
                    )
                
                for line in result.stdout.split('\n'):
                    if line.startswith('License:'):
                        license_str = line.split(':', 1)[1].strip()
                        licenses.append({
                            "license": {
                                "id": self._normalize_spdx_license(license_str),
                                "name": license_str
                            }
                        })
                        break
        except Exception:
            pass
        
        # If no license found, use NOASSERTION
        if not licenses:
            licenses.append({
                "license": {
                    "id": "NOASSERTION",
                    "name": "No license information available"
                }
            })
        
        return licenses
    
    def _normalize_spdx_license(self, license_str: str) -> str:
        """Normalize license string to SPDX identifier."""
        license_mapping = {
            'mit': 'MIT',
            'apache 2.0': 'Apache-2.0',
            'apache-2.0': 'Apache-2.0',
            'apache license 2.0': 'Apache-2.0',
            'bsd 3-clause': 'BSD-3-Clause',
            'bsd 2-clause': 'BSD-2-Clause',
            'bsd-3-clause': 'BSD-3-Clause',
            'bsd-2-clause': 'BSD-2-Clause',
            'gpl 3.0': 'GPL-3.0-only',
            'gpl-3.0': 'GPL-3.0-only',
            'gpl 2.0': 'GPL-2.0-only',
            'gpl-2.0': 'GPL-2.0-only',
            'lgpl 3.0': 'LGPL-3.0-only',
            'lgpl-3.0': 'LGPL-3.0-only',
            'lgpl 2.1': 'LGPL-2.1-only',
            'lgpl-2.1': 'LGPL-2.1-only',
            'agpl 3.0': 'AGPL-3.0-only',
            'agpl-3.0': 'AGPL-3.0-only',
            'mpl 2.0': 'MPL-2.0',
            'mpl-2.0': 'MPL-2.0',
            'apache': 'Apache-2.0',
            'bsd': 'BSD-3-Clause',
            'gpl': 'GPL-3.0-only',
            'lgpl': 'LGPL-3.0-only',
            'mpl': 'MPL-2.0',
            'isc': 'ISC',
            'unlicense': 'Unlicense',
            'public domain': 'Unlicense',
        }
        
        license_lower = license_str.lower().strip()
        return license_mapping.get(license_lower, license_str.upper())
    
    def generate_cyclonedx_json(self, components: List[Dict]) -> Dict:
        """Generate CycloneDX JSON format SBOM with license compliance."""
        components_list = []
        for comp in components:
            licenses = self._detect_license(comp)
            component = {
                "type": "library",
                "name": comp['name'],
                "version": comp['version'],
                "purl": comp.get('purl', ''),
                "licenses": licenses,
                "externalReferences": [{
                    "type": "distribution",
                    "url": f"https://pypi.org/project/{comp['name']}/" if comp.get('type') == 'pypi' else f"https://www.npmjs.com/package/{comp['name']}"
                }] if comp.get('type') in ('pypi', 'npm') else []
            }
            components_list.append(component)
        
        return {
            "bomFormat": "CycloneDX",
            "specVersion": "1.5",
            "serialNumber": f"urn:uuid:{uuid.uuid4()}",
            "version": 1,
            "metadata": {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "tools": [{
                    "vendor": "Code Analysis Agent",
                    "name": "Code Analysis Agent",
                    "version": "1.0.0"
                }],
                "component": {
                    "type": "application",
                    "name": self.repo_path.name,
                    "version": "1.0.0"
                }
            },
            "components": components_list
        }
    
    def generate_spdx_json(self, components: List[Dict]) -> Dict:
        """Generate SPDX JSON format SBOM."""
        spdx_id = f"SPDXRef-DOCUMENT-{uuid.uuid4().hex[:8]}"
        
        packages = []
        for i, comp in enumerate(components):
            pkg_id = f"SPDXRef-Package-{i}"
            packages.append({
                "SPDXID": pkg_id,
                "name": comp['name'],
                "versionInfo": comp['version'],
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": "NOASSERTION",
                "copyrightText": "NOASSERTION",
                "externalRefs": [{
                    "referenceCategory": "PACKAGE-MANAGER",
                    "referenceType": "purl",
                    "referenceLocator": comp.get('purl', '')
                }] if comp.get('purl') else []
            })
        
        return {
            "spdxVersion": "SPDX-2.3",
            "dataLicense": "CC0-1.0",
            "SPDXID": spdx_id,
            "name": self.repo_path.name,
            "documentNamespace": f"https://code-analysis-agent/{self.repo_path.name}/{uuid.uuid4()}",
            "creationInfo": {
                "created": datetime.utcnow().isoformat() + "Z",
                "creators": ["Tool: Code Analysis Agent 1.0.0"]
            },
            "packages": packages
        }
    
    def generate(self, format: SBOMFormat = SBOMFormat.CYCLONEDX_JSON) -> Dict:
        """Generate SBOM in specified format."""
        components = self.get_dependencies()
        
        if format == SBOMFormat.CYCLONEDX_JSON:
            return self.generate_cyclonedx_json(components)
        elif format == SBOMFormat.SPDX_JSON:
            return self.generate_spdx_json(components)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def save(self, output_path: str, format: SBOMFormat = SBOMFormat.CYCLONEDX_JSON):
        """Generate and save SBOM to file."""
        sbom = self.generate(format)
        
        if format in (SBOMFormat.CYCLONEDX_JSON, SBOMFormat.SPDX_JSON):
            with open(output_path, 'w') as f:
                json.dump(sbom, f, indent=2)
        else:
            raise ValueError(f"Format {format} not implemented for saving")
        
        return sbom


def create_sbom_cli():
    """CLI entry point for SBOM generation."""
    import click
    import json
    from rich.console import Console
    
    console = Console()
    
    @click.command()
    @click.argument('repo_path', type=click.Path(exists=True))
    @click.option('--format', '-f', type=click.Choice(['cyclonedx-json', 'spdx-json']),
                  default='cyclonedx-json', help='SBOM format')
    @click.option('--output', '-o', type=click.Path(), help='Output file path')
    def sbom(repo_path, format, output):
        generator = SBOMGenerator(repo_path)
        fmt = SBOMFormat(format)
        sbom_data = generator.generate(fmt)
        
        if output:
            generator.save(output, fmt)
            console.print(f"[green]SBOM saved to {output}[/green]")
        else:
            console.print_json(json.dumps(sbom_data, indent=2))
        
    return sbom


if __name__ == "__main__":
    import json
    from rich.console import Console
    console = Console()
    create_sbom_cli()()