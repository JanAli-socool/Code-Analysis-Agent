"""Monorepo detection and support for Nx, Turborepo, Bazel, and generic monorepos."""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class MonorepoType(Enum):
    NX = "nx"
    TURBOREPO = "turborepo"
    BAZEL = "bazel"
    LERNA = "lerna"
    PNPM_WORKSPACE = "pnpm_workspace"
    YARN_WORKSPACES = "yarn_workspaces"
    GENERIC = "generic"
    NONE = "none"


@dataclass
class MonorepoPackage:
    name: str
    path: str
    package_manager: str
    dependencies: List[str]
    dev_dependencies: List[str]
    scripts: Dict[str, str]


class MonorepoDetector:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
    
    def detect(self) -> MonorepoType:
        """Detect monorepo type."""
        # Check for Nx
        if (self.repo_path / "nx.json").exists() or (self.repo_path / "workspace.json").exists():
            return MonorepoType.NX
        
        # Check for Turborepo
        if (self.repo_path / "turbo.json").exists() or (self.repo_path / "turbo.jsonc").exists():
            return MonorepoType.TURBOREPO
        
        # Check for Bazel
        if (self.repo_path / "WORKSPACE").exists() or (self.repo_path / "WORKSPACE.bazel").exists():
            return MonorepoType.BAZEL
        
        # Check for Lerna
        if (self.repo_path / "lerna.json").exists():
            return MonorepoType.LERNA
        
        # Check for pnpm workspace
        if (self.repo_path / "pnpm-workspace.yaml").exists():
            return MonorepoType.PNPM_WORKSPACE
        
        # Check for Yarn workspaces
        if (self.repo_path / "package.json").exists():
            try:
                pkg = json.loads((self.repo_path / "package.json").read_text())
                if pkg.get("workspaces"):
                    return MonorepoType.YARN_WORKSPACES
            except:
                pass
        
        # Check for generic monorepo (packages/ or apps/ directories with package.json)
        if self._has_generic_monorepo_structure():
            return MonorepoType.GENERIC
        
        return MonorepoType.NONE
    
    def _has_generic_monorepo_structure(self) -> bool:
        """Check for generic monorepo structure."""
        for dir_name in ["packages", "apps", "libs", "services", "modules"]:
            dir_path = self.repo_path / dir_name
            if dir_path.exists() and dir_path.is_dir():
                # Check if it contains package.json files
                for pkg_json in dir_path.rglob("package.json"):
                    if pkg_json.is_file():
                        return True
        return False
    
    def get_packages(self, monorepo_type: MonorepoType) -> List[MonorepoPackage]:
        """Extract all packages from monorepo."""
        if monorepo_type == MonorepoType.NX:
            return self._get_nx_packages()
        elif monorepo_type == MonorepoType.TURBOREPO:
            return self._get_turborepo_packages()
        elif monorepo_type == MonorepoType.PNPM_WORKSPACE:
            return self._get_pnpm_packages()
        elif monorepo_type == MonorepoType.YARN_WORKSPACES:
            return self._get_yarn_packages()
        elif monorepo_type == MonorepoType.LERNA:
            return self._get_lerna_packages()
        elif monorepo_type == MonorepoType.GENERIC:
            return self._get_generic_packages()
        return []
    
    def _get_nx_packages(self) -> List[MonorepoPackage]:
        packages = []
        # Nx uses workspace.json or package.json workspaces
        workspace_json = self.repo_path / "workspace.json"
        if workspace_json.exists():
            try:
                data = json.loads(workspace_json.read_text())
                projects = data.get("projects", {})
                for name, config in projects.items():
                    root = config.get("root", "")
                    pkg_path = self.repo_path / root / "package.json"
                    if pkg_path.exists():
                        packages.append(self._parse_package_json(pkg_path, "npm"))
            except:
                pass
        return packages
    
    def _get_turborepo_packages(self) -> List[MonorepoPackage]:
        packages = []
        turbo_json = self.repo_path / "turbo.json"
        if not turbo_json.exists():
            turbo_json = self.repo_path / "turbo.jsonc"
        
        if turbo_json.exists():
            try:
                data = json.loads(turbo_json.read_text())
                # Turborepo typically uses package.json workspaces
                pkg_json = self.repo_path / "package.json"
                if pkg_json.exists():
                    pkg_data = json.loads(pkg_json.read_text())
                    workspaces = pkg_data.get("workspaces", [])
                    for ws in workspaces:
                        for pkg_path in self.repo_path.glob(ws + "/package.json"):
                            packages.append(self._parse_package_json(pkg_path, "npm"))
            except:
                pass
        return packages
    
    def _get_pnpm_packages(self) -> List[MonorepoPackage]:
        packages = []
        import yaml
        ws_file = self.repo_path / "pnpm-workspace.yaml"
        if ws_file.exists():
            try:
                data = yaml.safe_load(ws_file.read_text())
                packages_globs = data.get("packages", [])
                for glob_pattern in packages_globs:
                    for pkg_path in self.repo_path.glob(glob_pattern + "/package.json"):
                        packages.append(self._parse_package_json(pkg_path, "pnpm"))
            except:
                pass
        return packages
    
    def _get_yarn_packages(self) -> List[MonorepoPackage]:
        packages = []
        pkg_json = self.repo_path / "package.json"
        if pkg_json.exists():
            try:
                data = json.loads(pkg_json.read_text())
                workspaces = data.get("workspaces", [])
                for ws in workspaces:
                    for pkg_path in self.repo_path.glob(ws + "/package.json"):
                        packages.append(self._parse_package_json(pkg_path, "yarn"))
            except:
                pass
        return packages
    
    def _get_lerna_packages(self) -> List[MonorepoPackage]:
        packages = []
        lerna_json = self.repo_path / "lerna.json"
        if lerna_json.exists():
            try:
                data = json.loads(lerna_json.read_text())
                packages_globs = data.get("packages", [])
                for glob_pattern in packages_globs:
                    for pkg_path in self.repo_path.glob(glob_pattern + "/package.json"):
                        packages.append(self._parse_package_json(pkg_path, "npm"))
            except:
                pass
        return packages
    
    def _get_generic_packages(self) -> List[MonorepoPackage]:
        packages = []
        for dir_name in ["packages", "apps", "libs", "services", "modules"]:
            dir_path = self.repo_path / dir_name
            if dir_path.exists() and dir_path.is_dir():
                for pkg_json in dir_path.rglob("package.json"):
                    if pkg_json.is_file():
                        packages.append(self._parse_package_json(pkg_json, "generic"))
        return packages
    
    def _parse_package_json(self, pkg_path: Path, pm: str) -> MonorepoPackage:
        try:
            data = json.loads(pkg_path.read_text())
            return MonorepoPackage(
                name=data.get("name", pkg_path.parent.name),
                path=str(pkg_path.parent.relative_to(self.repo_path)),
                package_manager=pm,
                dependencies=list(data.get("dependencies", {}).keys()),
                dev_dependencies=list(data.get("devDependencies", {}).keys()),
                scripts=data.get("scripts", {})
            )
        except:
            return MonorepoPackage(
                name=pkg_path.parent.name,
                path=str(pkg_path.parent.relative_to(self.repo_path)),
                package_manager=pm,
                dependencies=[],
                dev_dependencies=[],
                scripts={}
            )


def analyze_monorepo(repo_path: str) -> Dict[str, Any]:
    """Main entry point for monorepo analysis."""
    detector = MonorepoDetector(repo_path)
    monorepo_type = detector.detect()
    
    if monorepo_type == MonorepoType.NONE:
        return {
            "is_monorepo": False,
            "type": "none",
            "packages": []
        }
    
    packages = detector.get_packages(monorepo_type)
    
    return {
        "is_monorepo": True,
        "type": monorepo_type.value,
        "package_count": len(packages),
        "packages": [
            {
                "name": p.name,
                "path": p.path,
                "package_manager": p.package_manager,
                "dependencies": p.dependencies,
                "dev_dependencies": p.dev_dependencies,
                "scripts": p.scripts
            }
            for p in packages
        ]
    }


if __name__ == "__main__":
    import sys
    result = analyze_monorepo(sys.argv[1] if len(sys.argv) > 1 else ".")
    print(json.dumps(result, indent=2))