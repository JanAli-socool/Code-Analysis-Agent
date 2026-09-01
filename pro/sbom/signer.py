"""
SBOM Signing and Verification using Sigstore/Cosign.
Supports keyless signing with OIDC and key-based signing.
"""
import json
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class SigningMode(Enum):
    KEYLESS = "keyless"  # OIDC identity (GitHub Actions, GitLab CI, etc.)
    KEY_PAIR = "key_pair"  # Cosign key pair
    LOCAL_KEY = "local_key"  # Local private key file


@dataclass
class SignResult:
    success: bool
    signature_path: Optional[str] = None
    certificate_path: Optional[str] = None
    bundle_path: Optional[str] = None
    error: Optional[str] = None


@dataclass
class VerifyResult:
    valid: bool
    signer_identity: Optional[str] = None
    certificate_subject: Optional[str] = None
    certificate_issuer: Optional[str] = None
    error: Optional[str] = None


class SBOMSigner:
    """Sign and verify SBOMs using Cosign/Sigstore."""
    
    def __init__(self, cosign_path: str = "cosign"):
        self.cosign_path = cosign_path
        self._verify_cosign()
    
    def _verify_cosign(self) -> bool:
        """Check if cosign is available."""
        try:
            result = subprocess.run(
                [self.cosign_path, "version"],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def sign_keyless(
        self,
        sbom_path: str,
        identity: Optional[str] = None,
        output_dir: Optional[str] = None
    ) -> SignResult:
        """Sign SBOM using keyless (OIDC) signing."""
        try:
            output_dir = output_dir or os.path.dirname(sbom_path)
            bundle_path = os.path.join(output_dir, f"{Path(sbom_path).stem}.sigstore.json")
            
            cmd = [
                self.cosign_path, "sign-blob",
                "--yes",
                "--bundle", bundle_path,
                sbom_path
            ]
            
            if identity:
                cmd.extend(["--identity", identity])
            
            env = os.environ.copy()
            env["COSIGN_EXPERIMENTAL"] = "1"
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                env=env
            )
            
            if result.returncode == 0 and os.path.exists(bundle_path):
                return SignResult(
                    success=True,
                    bundle_path=bundle_path
                )
            else:
                return SignResult(
                    success=False,
                    error=result.stderr or "Signing failed"
                )
        except subprocess.TimeoutExpired:
            return SignResult(success=False, error="Signing timed out")
        except Exception as e:
            return SignResult(success=False, error=str(e))
    
    def sign_with_key(
        self,
        sbom_path: str,
        private_key_path: str,
        password: Optional[str] = None,
        output_dir: Optional[str] = None
    ) -> SignResult:
        """Sign SBOM using a private key."""
        try:
            output_dir = output_dir or os.path.dirname(sbom_path)
            sig_path = os.path.join(output_dir, f"{Path(sbom_path).stem}.sig")
            cert_path = os.path.join(output_dir, f"{Path(sbom_path).stem}.pem")
            
            cmd = [
                self.cosign_path, "sign-blob",
                "--key", private_key_path,
                "--output-signature", sig_path,
                "--output-certificate", cert_path,
                sbom_path
            ]
            
            if password:
                env = os.environ.copy()
                env["COSIGN_PASSWORD"] = password
            else:
                env = os.environ.copy()
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                env=env
            )
            
            if result.returncode == 0:
                return SignResult(
                    success=True,
                    signature_path=sig_path if os.path.exists(sig_path) else None,
                    certificate_path=cert_path if os.path.exists(cert_path) else None
                )
            else:
                return SignResult(
                    success=False,
                    error=result.stderr or "Key-based signing failed"
                )
        except subprocess.TimeoutExpired:
            return SignResult(success=False, error="Signing timed out")
        except Exception as e:
            return SignResult(success=False, error=str(e))
    
    def verify_signature(
        self,
        sbom_path: str,
        bundle_path: Optional[str] = None,
        signature_path: Optional[str] = None,
        certificate_path: Optional[str] = None,
        public_key_path: Optional[str] = None,
        identity: Optional[str] = None
    ) -> VerifyResult:
        """Verify SBOM signature."""
        try:
            if bundle_path and os.path.exists(bundle_path):
                # Verify using Sigstore bundle
                cmd = [
                    self.cosign_path, "verify-blob",
                    "--bundle", bundle_path,
                    sbom_path
                ]
                if identity:
                    cmd.extend(["--identity", identity])
            elif signature_path and certificate_path:
                # Verify using signature + certificate
                cmd = [
                    self.cosign_path, "verify-blob",
                    "--signature", signature_path,
                    "--certificate", certificate_path,
                    sbom_path
                ]
            elif public_key_path:
                # Verify using public key
                cmd = [
                    self.cosign_path, "verify-blob",
                    "--key", public_key_path,
                    sbom_path
                ]
            else:
                return VerifyResult(valid=False, error="No verification method provided")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                # Parse output for signer info
                signer_identity = self._extract_signer_identity(result.stdout)
                return VerifyResult(
                    valid=True,
                    signer_identity=signer_identity
                )
            else:
                return VerifyResult(
                    valid=False,
                    error=result.stderr or "Verification failed"
                )
        except subprocess.TimeoutExpired:
            return VerifyResult(valid=False, error="Verification timed out")
        except Exception as e:
            return VerifyResult(valid=False, error=str(e))
    
    def _extract_signer_identity(self, output: str) -> Optional[str]:
        """Extract signer identity from cosign output."""
        for line in output.split('\n'):
            if 'Subject:' in line or 'Issuer:' in line:
                return line.strip()
        return None
    
    def generate_keypair(self, output_dir: str, password: Optional[str] = None) -> Tuple[str, str]:
        """Generate a new cosign key pair."""
        private_key = os.path.join(output_dir, "cosign.key")
        public_key = os.path.join(output_dir, "cosign.pub")
        
        cmd = [
            self.cosign_path, "generate-key-pair",
            "--output-key-prefix", os.path.join(output_dir, "cosign")
        ]
        
        env = os.environ.copy()
        if password:
            env["COSIGN_PASSWORD"] = password
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
        
        if result.returncode != 0:
            raise RuntimeError(f"Key generation failed: {result.stderr}")
        
        return private_key, public_key


class SBOMAttestor:
    """Create and verify SBOM attestations (in-toto/SLSA)."""
    
    def __init__(self, cosign_path: str = "cosign"):
        self.cosign_path = cosign_path
    
    def create_attestation(
        self,
        sbom_path: str,
        predicate_type: str = "https://slsa.dev/provenance/v1",
        predicate_path: Optional[str] = None,
        output_dir: Optional[str] = None
    ) -> SignResult:
        """Create an in-toto attestation for the SBOM."""
        try:
            output_dir = output_dir or os.path.dirname(sbom_path)
            attestation_path = os.path.join(output_dir, f"{Path(sbom_path).stem}.attestation.json")
            
            cmd = [
                self.cosign_path, "attest-blob",
                "--predicate-type", predicate_type,
                "--predicate", predicate_path or sbom_path,
                "--yes",
                sbom_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                return SignResult(success=True)
            else:
                return SignResult(success=False, error=result.stderr)
        except Exception as e:
            return SignResult(success=False, error=str(e))
    
    def verify_attestation(
        self,
        sbom_path: str,
        attestation_path: str,
        policy_path: Optional[str] = None
    ) -> VerifyResult:
        """Verify an in-toto attestation."""
        try:
            cmd = [
                self.cosign_path, "verify-attestation",
                "--type", "slsaprovenance",
                sbom_path
            ]
            
            if policy_path:
                cmd.extend(["--policy", policy_path])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            return VerifyResult(
                valid=result.returncode == 0,
                error=result.stderr if result.returncode != 0 else None
            )
        except Exception as e:
            return VerifyResult(valid=False, error=str(e))


def sign_sbom(
    sbom_path: str,
    mode: SigningMode = SigningMode.KEYLESS,
    **kwargs
) -> SignResult:
    """Convenience function to sign an SBOM."""
    signer = SBOMSigner()
    
    if mode == SigningMode.KEYLESS:
        return signer.sign_keyless(sbom_path, **kwargs)
    elif mode == SigningMode.KEY_PAIR:
        return signer.sign_with_key(sbom_path, **kwargs)
    else:
        return SignResult(success=False, error=f"Unsupported mode: {mode}")


def verify_sbom(sbom_path: str, **kwargs) -> VerifyResult:
    """Convenience function to verify an SBOM signature."""
    signer = SBOMSigner()
    return signer.verify_signature(sbom_path, **kwargs)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python signer.py <sign|verify> <sbom_path> [options]")
        sys.exit(1)
    
    action = sys.argv[1]
    sbom_path = sys.argv[2]
    
    if action == "sign":
        mode = SigningMode(sys.argv[3]) if len(sys.argv) > 3 else SigningMode.KEYLESS
        result = sign_sbom(sbom_path, mode=mode)
    elif action == "verify":
        result = verify_sbom(sbom_path)
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
    
    print(json.dumps({
        "success": result.success if hasattr(result, 'success') else result.valid,
        "error": getattr(result, 'error', None)
    }, indent=2))