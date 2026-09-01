"""
Policy-as-Code Engine using OPA/Rego.
Enables custom policy enforcement for code analysis results.
"""
import json
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class PolicyDecision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"


@dataclass
class PolicyResult:
    decision: PolicyDecision
    policy_id: str
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    violations: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class PolicyEvaluation:
    overall_decision: PolicyDecision
    policy_results: List[PolicyResult]
    passed: int
    failed: int
    warnings: int
    evaluated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class OPAEngine:
    """Policy evaluation engine using OPA (Open Policy Agent)."""
    
    def __init__(self, opa_path: str = "opa"):
        self.opa_path = opa_path
        self.policies_dir: Optional[str] = None
        self._verify_opa()
    
    def _verify_opa(self) -> bool:
        """Check if OPA is available."""
        try:
            result = subprocess.run(
                [self.opa_path, "version"],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def load_policies(self, policies_dir: str) -> None:
        """Load policies from a directory."""
        self.policies_dir = policies_dir
        Path(policies_dir).mkdir(parents=True, exist_ok=True)
    
    def add_policy(self, policy_id: str, rego_content: str) -> None:
        """Add a policy from Rego content."""
        if not self.policies_dir:
            raise ValueError("Policies directory not set. Call load_policies() first.")
        
        policy_path = Path(self.policies_dir) / f"{policy_id}.rego"
        policy_path.write_text(rego_content)
    
    def remove_policy(self, policy_id: str) -> bool:
        """Remove a policy."""
        if not self.policies_dir:
            return False
        
        policy_path = Path(self.policies_dir) / f"{policy_id}.rego"
        if policy_path.exists():
            policy_path.unlink()
            return True
        return False
    
    def list_policies(self) -> List[str]:
        """List all loaded policy IDs."""
        if not self.policies_dir:
            return []
        
        return [p.stem for p in Path(self.policies_dir).glob("*.rego")]
    
    def evaluate(
        self,
        input_data: Dict[str, Any],
        policy_ids: Optional[List[str]] = None
    ) -> PolicyEvaluation:
        """Evaluate input data against policies."""
        if not self.policies_dir:
            raise ValueError("Policies directory not set")
        
        policies_to_eval = policy_ids or self.list_policies()
        
        if not policies_to_eval:
            return PolicyEvaluation(
                overall_decision=PolicyDecision.ALLOW,
                policy_results=[],
                passed=0,
                failed=0,
                warnings=0
            )
        
        # Write input data to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(input_data, f)
            input_file = f.name
        
        try:
            results = []
            for policy_id in policies_to_eval:
                policy_path = Path(self.policies_dir) / f"{policy_id}.rego"
                if not policy_path.exists():
                    results.append(PolicyResult(
                        decision=PolicyDecision.WARN,
                        policy_id=policy_id,
                        message=f"Policy file not found: {policy_path}",
                        violations=[{"error": "Policy file not found"}]
                    ))
                    continue
                
                result = self._eval_single_policy(input_file, str(policy_path), policy_id)
                results.append(result)
            
            # Calculate overall decision
            overall = self._calculate_overall_decision(results)
            
            return PolicyEvaluation(
                overall_decision=overall,
                policy_results=results,
                passed=sum(1 for r in results if r.decision == PolicyDecision.ALLOW),
                failed=sum(1 for r in results if r.decision == PolicyDecision.DENY),
                warnings=sum(1 for r in results if r.decision == PolicyDecision.WARN)
            )
        finally:
            os.unlink(input_file)
    
    def _eval_single_policy(
        self,
        input_file: str,
        policy_path: str,
        policy_id: str
    ) -> PolicyResult:
        """Evaluate a single policy."""
        try:
            # Run opa eval
            result = subprocess.run([
                self.opa_path, "eval",
                "-i", input_file,
                "-d", policy_path,
                "data.codeanalysis.result",
                "--format", "json"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return PolicyResult(
                    decision=PolicyDecision.WARN,
                    policy_id=policy_id,
                    message=f"OPA evaluation failed: {result.stderr}",
                    violations=[{"error": result.stderr}]
                )
            
            # Parse OPA output
            opa_output = json.loads(result.stdout)
            decisions = self._extract_decisions(opa_output)
            
            if not decisions:
                return PolicyResult(
                    decision=PolicyDecision.ALLOW,
                    policy_id=policy_id,
                    message="No violations found",
                    violations=[]
                )
            
            # Determine overall decision for this policy
            has_deny = any(d.get("decision") == "deny" for d in decisions)
            has_warn = any(d.get("decision") == "warn" for d in decisions)
            
            if has_deny:
                decision = PolicyDecision.DENY
            elif has_warn:
                decision = PolicyDecision.WARN
            else:
                decision = PolicyDecision.ALLOW
            
            violations = [d for d in decisions if d.get("decision") in ("deny", "warn")]
            
            return PolicyResult(
                decision=decision,
                policy_id=policy_id,
                message=f"Found {len(violations)} violation(s)",
                violations=violations
            )
        except subprocess.TimeoutExpired:
            return PolicyResult(
                decision=PolicyDecision.WARN,
                policy_id=policy_id,
                message="Policy evaluation timed out",
                violations=[{"error": "Timeout"}]
            )
        except Exception as e:
            return PolicyResult(
                decision=PolicyDecision.WARN,
                policy_id=policy_id,
                message=f"Evaluation error: {str(e)}",
                violations=[{"error": str(e)}]
            )
    
    def _extract_decisions(self, opa_output: Dict) -> List[Dict]:
        """Extract decisions from OPA output."""
        decisions = []
        try:
            for result in opa_output.get("result", []):
                for expr in result.get("expressions", []):
                    value = expr.get("value", {})
                    if isinstance(value, list):
                        decisions.extend(value)
                    elif isinstance(value, dict) and "decision" in value:
                        decisions.append(value)
        except Exception:
            pass
        return decisions
    
    def _calculate_overall_decision(self, results: List[PolicyResult]) -> PolicyDecision:
        """Calculate overall decision from individual policy results."""
        if any(r.decision == PolicyDecision.DENY for r in results):
            return PolicyDecision.DENY
        if any(r.decision == PolicyDecision.WARN for r in results):
            return PolicyDecision.WARN
        return PolicyDecision.ALLOW


class RegoPolicyTemplates:
    """Built-in Rego policy templates for common code analysis policies."""
    
    @staticmethod
    def critical_vulnerabilities() -> str:
        return '''
package codeanalysis

# Deny if critical vulnerabilities found
result := {
    "decision": "deny",
    "policy": "critical-vulnerabilities",
    "message": sprintf("Found %d critical vulnerabilities", [count(input.findings[_] | input.findings[_].severity == "critical")]),
    "count": count(input.findings[_] | input.findings[_].severity == "critical"),
    "details": [f | f := input.findings[_]; f.severity == "critical"]
}
'''
    
    @staticmethod
    def high_vulnerabilities_threshold(max_high: int = 5) -> str:
        return f'''
package codeanalysis

# Warn if high vulnerabilities exceed threshold
high_count := count(input.findings[_] | input.findings[_].severity == "high")

result := {{
    "decision": "warn",
    "policy": "high-vulnerabilities-threshold",
    "message": sprintf("Found %d high vulnerabilities (threshold: {max_high})", [high_count]),
    "count": high_count,
    "threshold": {max_high},
    "details": [f | f := input.findings[_]; f.severity == "high"]
}} if high_count > {max_high}
'''
    
    @staticmethod
    def license_compliance_blocked(licenses: List[str]) -> str:
        licenses_str = json.dumps(licenses)
        return f'''
package codeanalysis

# Deny if blocked licenses detected
blocked_licenses := {licenses_str}

blocked := [f | f := input.sbom_components[_];
    f.licenses[_].license.id in blocked_licenses]

result := {{
    "decision": "deny",
    "policy": "license-compliance-blocked",
    "message": sprintf("Found %d components with blocked licenses", [count(blocked)]),
    "count": count(blocked),
    "details": blocked
}} if count(blocked) > 0
'''
    
    @staticmethod
    def min_test_coverage(min_percent: int = 80) -> str:
        return f'''
package codeanalysis

# Warn if test coverage below threshold
coverage := input.metrics.test_coverage_percent

result := {{
    "decision": "warn",
    "policy": "min-test-coverage",
    "message": sprintf("Test coverage %d%% below threshold {min_percent}%%", [coverage]),
    "coverage": coverage,
    "threshold": {min_percent}
}} if coverage < {min_percent}
'''
    
    @staticmethod
    def max_complexity_threshold(max_cc: int = 15) -> str:
        return f'''
package codeanalysis

# Deny if cyclomatic complexity exceeds threshold
max_complexity := max([f.metric_value | f := input.findings[_]; f.category == "complexity"; f.metric_value > {max_cc}], default=0)

result := {{
    "decision": "deny",
    "policy": "max-complexity-threshold",
    "message": sprintf("Maximum cyclomatic complexity %d exceeds threshold {max_cc}", [max_complexity]),
    "max_complexity": max_complexity,
    "threshold": {max_cc},
    "details": [f | f := input.findings[_]; f.category == "complexity"; f.metric_value > {max_cc}]
}} if max_complexity > {max_cc}
'''
    
    @staticmethod
    def supply_chain_risks() -> str:
        return '''
package codeanalysis

# Deny if supply chain risks detected
supply_chain := [f | f := input.findings[_]; f.category == "supply_chain"]

result := {
    "decision": "deny",
    "policy": "supply-chain-risks",
    "message": sprintf("Found %d supply chain risks", [count(supply_chain)]),
    "count": count(supply_chain),
    "details": supply_chain
} if count(supply_chain) > 0
'''
    
    @staticmethod
    def outdated_dependencies_threshold(max_outdated: int = 10) -> str:
        return f'''
package codeanalysis

# Warn if too many outdated dependencies
outdated_count := input.metrics.outdated_dependencies

result := {{
    "decision": "warn",
    "policy": "outdated-dependencies-threshold",
    "message": sprintf("Found %d outdated dependencies (threshold: {max_outdated})", [outdated_count]),
    "count": outdated_count,
    "threshold": {max_outdated}
}} if outdated_count > {max_outdated}
'''
    
    @staticmethod
    def secret_detection() -> str:
        return '''
package codeanalysis

# Deny if secrets detected
secrets := [f | f := input.findings[_]; 
    f.category == "security"; 
    contains(f.message, "secret") or contains(f.message, "password") or contains(f.message, "api_key")]

result := {
    "decision": "deny",
    "policy": "secret-detection",
    "message": sprintf("Found %d potential secrets", [count(secrets)]),
    "count": count(secrets),
    "details": secrets
} if count(secrets) > 0
'''


class PolicyManager:
    """High-level policy management."""
    
    def __init__(self, policies_dir: str = "policies"):
        self.engine = OPAEngine()
        self.engine.load_policies(policies_dir)
        self._load_builtin_policies()
    
    def _load_builtin_policies(self) -> None:
        """Load built-in policy templates."""
        templates = RegoPolicyTemplates()
        
        builtins = {
            "critical-vulnerabilities": templates.critical_vulnerabilities(),
            "high-vulnerabilities": templates.high_vulnerabilities_threshold(5),
            "license-compliance": templates.license_compliance_blocked(["GPL-3.0", "AGPL-3.0", "LGPL-3.0"]),
            "min-test-coverage": templates.min_test_coverage(80),
            "max-complexity": templates.max_complexity_threshold(15),
            "supply-chain-risks": templates.supply_chain_risks(),
            "outdated-dependencies": templates.outdated_dependencies_threshold(10),
            "secret-detection": templates.secret_detection(),
        }
        
        for policy_id, rego in builtins.items():
            try:
                self.engine.add_policy(policy_id, rego)
            except Exception:
                pass  # Ignore if already exists
    
    def evaluate_analysis(self, analysis_result: Dict[str, Any]) -> PolicyEvaluation:
        """Evaluate analysis result against all policies."""
        # Prepare input for OPA
        input_data = self._prepare_input(analysis_result)
        return self.engine.evaluate(input_data)
    
    def _prepare_input(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare analysis result for policy evaluation."""
        findings = []
        for cat in analysis_result.get("category_scores", []):
            for finding in cat.get("findings", []):
                finding_copy = finding.copy()
                finding_copy["category"] = cat.get("name", "unknown")
                findings.append(finding_copy)
        
        # Extract metrics
        metrics = {}
        for m in analysis_result.get("metrics", []):
            if isinstance(m, dict) and "name" in m:
                metrics[m["name"]] = m.get("value", 0)
        
        # Extract SBOM components
        sbom_components = []
        for cat in analysis_result.get("category_scores", []):
            if cat.get("name") == "dependencies":
                sbom_components = cat.get("metrics", [])
                break
        
        return {
            "findings": findings,
            "metrics": metrics,
            "sbom_components": sbom_components,
            "overall_score": analysis_result.get("overall_score", 0),
            "risk_level": analysis_result.get("risk_level", "unknown")
        }
    
    def add_custom_policy(self, policy_id: str, rego_content: str) -> None:
        """Add a custom policy."""
        self.engine.add_policy(policy_id, rego_content)
    
    def get_policy(self, policy_id: str) -> Optional[str]:
        """Get policy Rego content."""
        if not self.engine.policies_dir:
            return None
        
        policy_path = Path(self.engine.policies_dir) / f"{policy_id}.rego"
        if policy_path.exists():
            return policy_path.read_text()
        return None
    
    def export_policies(self, output_dir: str) -> None:
        """Export all policies to directory."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for policy_id in self.engine.list_policies():
            content = self.get_policy(policy_id)
            if content:
                (output_path / f"{policy_id}.rego").write_text(content)


def create_policy_evaluation(
    analysis_result: Dict[str, Any],
    policies_dir: str = "policies"
) -> PolicyEvaluation:
    """Convenience function to evaluate analysis against policies."""
    manager = PolicyManager(policies_dir)
    return manager.evaluate_analysis(analysis_result)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python engine.py <policies_dir> <input_json>")
        sys.exit(1)
    
    policies_dir = sys.argv[1]
    input_file = sys.argv[2]
    
    with open(input_file) as f:
        input_data = json.load(f)
    
    manager = PolicyManager(policies_dir)
    result = manager.evaluate_analysis(input_data)
    
    print(json.dumps({
        "overall_decision": result.overall_decision.value,
        "passed": result.passed,
        "failed": result.failed,
        "warnings": result.warnings,
        "policies": [
            {
                "policy_id": r.policy_id,
                "decision": r.decision.value,
                "message": r.message,
                "violations": r.violations
            }
            for r in result.policy_results
        ]
    }, indent=2))