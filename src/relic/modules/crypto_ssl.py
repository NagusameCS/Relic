"""
Cryptography & SSL/TLS testing modules — certificate analysis,
cipher-suite auditing, protocol checks, and key strength evaluation.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from relic.modules.base import BaseModule, ModuleResult

if TYPE_CHECKING:
    from relic.core.engine import Engine


class SSLyzeModule(BaseModule):
    """SSLyze — fast SSL/TLS scanner."""

    name = "sslyze"
    description = "SSL/TLS configuration analysis with SSLyze"
    category = "crypto"

    def get_commands(self, target: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"sslyze --regular {target}",
             "description": f"SSLyze regular scan on {target}"},
        ]

    async def run(self, engine: "Engine", target: str = "", **kwargs: Any) -> ModuleResult:
        output = await engine.run_single_command(f"sslyze --regular {target}")
        findings = []
        low = output.lower()
        if "sslv2" in low or "sslv3" in low:
            findings.append({"type": "deprecated_protocol", "title": "SSLv2/SSLv3 Supported", "severity": "high"})
        if "rc4" in low:
            findings.append({"type": "weak_cipher", "title": "RC4 Cipher Suite Enabled", "severity": "high"})
        if "sha1" in low and "signature" in low:
            findings.append({"type": "weak_hash", "title": "SHA-1 Certificate Signature", "severity": "medium"})
        if "expired" in low:
            findings.append({"type": "expired_cert", "title": "Expired Certificate", "severity": "high"})
        if "self-signed" in low or "self signed" in low:
            findings.append({"type": "self_signed", "title": "Self-Signed Certificate", "severity": "medium"})
        return ModuleResult(module=self.name, output=output, findings=findings)


class TestSSLModule(BaseModule):
    """testssl.sh — comprehensive TLS/SSL testing."""

    name = "testssl"
    description = "Comprehensive TLS/SSL testing with testssl.sh"
    category = "crypto"

    def get_commands(self, target: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"testssl --severity HIGH --color 0 {target}",
             "description": f"testssl.sh scan on {target} (HIGH+ severity)"},
            {"command": f"testssl --headers --color 0 {target}",
             "description": f"testssl.sh HTTP header check on {target}"},
        ]

    async def run(self, engine: "Engine", target: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(target=target, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = []
        for keyword, title, sev in [
            ("vulnerable", "TLS Vulnerability Detected", "high"),
            ("heartbleed", "Heartbleed Vulnerable", "critical"),
            ("ccs injection", "CCS Injection Vulnerable", "critical"),
            ("ticketbleed", "Ticketbleed Vulnerable", "critical"),
            ("crime", "CRIME Attack Possible", "high"),
            ("breach", "BREACH Attack Possible", "medium"),
            ("poodle", "POODLE Attack Possible", "high"),
            ("sweet32", "SWEET32 Attack Possible", "medium"),
            ("freak", "FREAK Attack Possible", "high"),
            ("logjam", "Logjam Attack Possible", "high"),
            ("robot", "ROBOT Attack Possible", "high"),
        ]:
            if keyword in combined.lower():
                findings.append({"type": "tls_vuln", "title": title, "severity": sev})
        return ModuleResult(module=self.name, output=combined, findings=findings)


class SSLScanModule(BaseModule):
    """sslscan — fast SSL cipher enumeration."""

    name = "sslscan"
    description = "SSL cipher suite and protocol enumeration"
    category = "crypto"

    def get_commands(self, target: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"sslscan --no-colour {target}",
             "description": f"sslscan on {target}"},
        ]

    async def run(self, engine: "Engine", target: str = "", **kwargs: Any) -> ModuleResult:
        output = await engine.run_single_command(f"sslscan --no-colour {target}")
        findings = []
        if "accepted" in output.lower() and ("sslv" in output.lower() or "tlsv1.0" in output.lower()):
            findings.append({"type": "weak_protocol", "title": "Weak TLS/SSL Protocol Accepted", "severity": "high"})
        return ModuleResult(module=self.name, output=output, findings=findings)


class CertAnalysisModule(BaseModule):
    """OpenSSL certificate inspection and chain validation."""

    name = "cert-analysis"
    description = "X.509 certificate inspection, chain validation, and expiry check"
    category = "crypto"

    def get_commands(self, target: str = "", port: str = "443", **kwargs: Any) -> list[dict[str, str]]:
        host = target.split("/")[0] if "/" in target else target
        return [
            {"command": f"echo | openssl s_client -connect {host}:{port} -servername {host} 2>/dev/null | openssl x509 -noout -text",
             "description": f"Full certificate text for {host}:{port}"},
            {"command": f"echo | openssl s_client -connect {host}:{port} -servername {host} 2>/dev/null | openssl x509 -noout -dates -subject -issuer -ext subjectAltName",
             "description": f"Certificate dates, subject, issuer, SANs for {host}:{port}"},
            {"command": f"echo | openssl s_client -connect {host}:{port} -servername {host} -showcerts 2>/dev/null",
             "description": f"Full certificate chain for {host}:{port}"},
        ]

    async def run(self, engine: "Engine", target: str = "", port: str = "443", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(target=target, port=port, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = []
        if "expired" in combined.lower():
            findings.append({"type": "expired_cert", "title": "Certificate Expired", "severity": "high"})
        if "self-signed" in combined.lower() or "self signed" in combined.lower():
            findings.append({"type": "self_signed", "title": "Self-Signed Certificate", "severity": "medium"})
        return ModuleResult(module=self.name, output=combined, findings=findings)


class CipherSuiteModule(BaseModule):
    """Enumerate supported cipher suites via nmap."""

    name = "cipher-enum"
    description = "Enumerate supported cipher suites and key exchange methods"
    category = "crypto"

    def get_commands(self, target: str = "", port: str = "443", **kwargs: Any) -> list[dict[str, str]]:
        host = target.split("/")[0] if "/" in target else target
        return [
            {"command": f"nmap --script ssl-enum-ciphers -p {port} {host}",
             "description": f"Enumerate cipher suites on {host}:{port}"},
        ]

    async def run(self, engine: "Engine", target: str = "", port: str = "443", **kwargs: Any) -> ModuleResult:
        host = target.split("/")[0] if "/" in target else target
        output = await engine.run_single_command(f"nmap --script ssl-enum-ciphers -p {port} {host}")
        findings = []
        if "grade: f" in output.lower() or "grade: d" in output.lower():
            findings.append({"type": "weak_cipher_grade", "title": "Weak Cipher Grade (D/F)", "severity": "high"})
        return ModuleResult(module=self.name, output=output, findings=findings)


class TLSVersionModule(BaseModule):
    """Test for specific TLS protocol version support."""

    name = "tls-version"
    description = "Probe individual TLS protocol versions (1.0, 1.1, 1.2, 1.3)"
    category = "crypto"

    def get_commands(self, target: str = "", port: str = "443", **kwargs: Any) -> list[dict[str, str]]:
        host = target.split("/")[0] if "/" in target else target
        return [
            {"command": f"echo | openssl s_client -connect {host}:{port} -tls1 2>&1 | head -5",
             "description": f"Test TLS 1.0 on {host}:{port}"},
            {"command": f"echo | openssl s_client -connect {host}:{port} -tls1_1 2>&1 | head -5",
             "description": f"Test TLS 1.1 on {host}:{port}"},
            {"command": f"echo | openssl s_client -connect {host}:{port} -tls1_2 2>&1 | head -5",
             "description": f"Test TLS 1.2 on {host}:{port}"},
            {"command": f"echo | openssl s_client -connect {host}:{port} -tls1_3 2>&1 | head -5",
             "description": f"Test TLS 1.3 on {host}:{port}"},
        ]

    async def run(self, engine: "Engine", target: str = "", port: str = "443", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(target=target, port=port, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = []
        for i, label in enumerate(["TLS 1.0", "TLS 1.1", "TLS 1.2", "TLS 1.3"]):
            if i < len(outputs) and "connected" in outputs[i].lower() and "error" not in outputs[i].lower():
                severity = "high" if label in ("TLS 1.0", "TLS 1.1") else "info"
                findings.append({"type": "tls_version", "title": f"{label} Supported", "severity": severity})
        return ModuleResult(module=self.name, output=combined, findings=findings)


# ═══════════════════════════════════════════════════════════════════
# Registry
# ═══════════════════════════════════════════════════════════════════

CRYPTO_MODULES: dict[str, type[BaseModule]] = {
    "sslyze": SSLyzeModule,
    "testssl": TestSSLModule,
    "sslscan": SSLScanModule,
    "cert-analysis": CertAnalysisModule,
    "cipher-enum": CipherSuiteModule,
    "tls-version": TLSVersionModule,
}
