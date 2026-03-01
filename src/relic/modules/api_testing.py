"""
API security testing modules — REST/GraphQL fuzzing, JWT analysis,
authentication bypass, IDOR, rate-limiting, and schema enumeration.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from relic.modules.base import BaseModule, ModuleResult

if TYPE_CHECKING:
    from relic.core.engine import Engine


class RESTFuzzModule(BaseModule):
    """Fuzz REST API endpoints for unexpected behaviour."""

    name = "rest-fuzz"
    description = "REST API fuzzing with various HTTP methods and payloads"
    category = "api"

    def get_commands(self, target: str = "", **kwargs: Any) -> list[dict[str, str]]:
        url = target if target.startswith("http") else f"https://{target}"
        return [
            {"command": f"ffuf -u {url}/FUZZ -w /usr/share/seclists/Discovery/Web-Content/api/api-endpoints.txt -mc all -fc 404 -t 10",
             "description": f"Fuzz API endpoints on {url}"},
            {"command": f"curl -s -X OPTIONS {url} -D - -o /dev/null",
             "description": f"Check allowed HTTP methods via OPTIONS"},
            {"command": f"for m in GET POST PUT PATCH DELETE HEAD; do echo \"=== $m ===\"; curl -s -o /dev/null -w '%{{http_code}}' -X $m {url}; echo; done",
             "description": f"Test all HTTP methods against {url}"},
        ]

    async def run(self, engine: "Engine", target: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(target=target, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = []
        for method in ("PUT", "DELETE", "PATCH"):
            if f"=== {method} ===" in combined and "200" in combined:
                findings.append({"type": "http_method", "title": f"{method} Method Allowed", "severity": "medium"})
        return ModuleResult(module=self.name, output=combined, findings=findings)


class JWTAnalysisModule(BaseModule):
    """JWT token analysis — decode, crack, and test for vulnerabilities."""

    name = "jwt-analysis"
    description = "JWT token decoding, algorithm confusion, and secret cracking"
    category = "api"

    def get_commands(self, token: str = "", target: str = "", **kwargs: Any) -> list[dict[str, str]]:
        cmds = []
        if token:
            cmds.extend([
                {"command": f"echo '{token}' | jwt_tool -",
                 "description": "Decode JWT token"},
                {"command": f"echo '{token}' | jwt_tool - -M at -t {target} -rc 'status_code != 401' 2>/dev/null",
                 "description": "JWT algorithm confusion / none attack"},
                {"command": f"jwt_tool '{token}' -C -d /usr/share/wordlists/rockyou.txt 2>/dev/null | head -10",
                 "description": "JWT secret brute-force"},
            ])
        return cmds or [
            {"command": f"curl -s {target} -D - -o /dev/null | grep -i 'authorization\\|set-cookie\\|jwt'",
             "description": "Search for JWT in response headers"},
        ]

    async def run(self, engine: "Engine", token: str = "", target: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(token=token, target=target, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = []
        if "none" in combined.lower() and "accepted" in combined.lower():
            findings.append({"type": "jwt_none", "title": "JWT 'none' Algorithm Accepted", "severity": "critical"})
        if "secret" in combined.lower() and "found" in combined.lower():
            findings.append({"type": "jwt_weak_secret", "title": "JWT Weak Secret Found", "severity": "critical"})
        return ModuleResult(module=self.name, output=combined, findings=findings)


class AuthBypassModule(BaseModule):
    """Test for authentication and authorization bypass vulnerabilities."""

    name = "auth-bypass"
    description = "Test for auth bypass via header manipulation, path traversal, verb tampering"
    category = "api"

    def get_commands(self, target: str = "", **kwargs: Any) -> list[dict[str, str]]:
        url = target if target.startswith("http") else f"https://{target}"
        return [
            {"command": f"curl -s -o /dev/null -w '%{{http_code}}' {url}",
             "description": f"Baseline response code for {url}"},
            {"command": f"curl -s -o /dev/null -w '%{{http_code}}' -H 'X-Forwarded-For: 127.0.0.1' {url}",
             "description": "Auth bypass via X-Forwarded-For"},
            {"command": f"curl -s -o /dev/null -w '%{{http_code}}' -H 'X-Original-URL: /admin' {url}",
             "description": "Auth bypass via X-Original-URL"},
            {"command": f"curl -s -o /dev/null -w '%{{http_code}}' -H 'X-Rewrite-URL: /admin' {url}",
             "description": "Auth bypass via X-Rewrite-URL"},
            {"command": f"curl -s -o /dev/null -w '%{{http_code}}' -H 'X-Custom-IP-Authorization: 127.0.0.1' {url}",
             "description": "Auth bypass via X-Custom-IP-Authorization"},
            {"command": f"curl -s -o /dev/null -w '%{{http_code}}' {url}/%2e/admin 2>/dev/null",
             "description": "Auth bypass via path traversal encoding"},
        ]

    async def run(self, engine: "Engine", target: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(target=target, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = []
        # If any bypass attempt returns 200 while baseline is 401/403
        codes = [o.strip() for o in outputs]
        baseline = codes[0] if codes else "000"
        if baseline in ("401", "403"):
            for i, code in enumerate(codes[1:], 1):
                if code == "200":
                    findings.append({
                        "type": "auth_bypass",
                        "title": f"Auth Bypass via {commands[i]['description']}",
                        "severity": "critical",
                    })
        return ModuleResult(module=self.name, output=combined, findings=findings)


class IDORModule(BaseModule):
    """Test for Insecure Direct Object Reference (IDOR) vulnerabilities."""

    name = "idor"
    description = "Test for IDOR by enumerating sequential/predictable identifiers"
    category = "api"

    def get_commands(self, target: str = "", param: str = "id", **kwargs: Any) -> list[dict[str, str]]:
        url = target if target.startswith("http") else f"https://{target}"
        return [
            {"command": f"for i in $(seq 1 20); do echo \"ID=$i: $(curl -s -o /dev/null -w '%{{http_code}}' '{url}?{param}=$i')\"; done",
             "description": f"Enumerate {param} parameter (1-20)"},
            {"command": f"wfuzz -z range,1-100 -u '{url}?{param}=FUZZ' --hc 404 -t 10 2>/dev/null | head -30",
             "description": f"Wfuzz IDOR test on {param}"},
        ]

    async def run(self, engine: "Engine", target: str = "", param: str = "id", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(target=target, param=param, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        return ModuleResult(module=self.name, output="\n".join(outputs))


class RateLimitModule(BaseModule):
    """Test API rate limiting and brute-force protections."""

    name = "rate-limit"
    description = "Test rate limiting and account lockout policies"
    category = "api"

    def get_commands(self, target: str = "", **kwargs: Any) -> list[dict[str, str]]:
        url = target if target.startswith("http") else f"https://{target}"
        return [
            {"command": f"for i in $(seq 1 50); do curl -s -o /dev/null -w '%{{http_code}} ' {url}; done; echo",
             "description": f"Send 50 rapid requests to test rate limiting on {url}"},
        ]

    async def run(self, engine: "Engine", target: str = "", **kwargs: Any) -> ModuleResult:
        output = await engine.run_single_command(self.get_commands(target=target)[0]["command"])
        findings = []
        if "429" not in output:
            findings.append({"type": "no_rate_limit", "title": "No Rate Limiting Detected", "severity": "medium"})
        return ModuleResult(module=self.name, output=output, findings=findings)


class APISchemaModule(BaseModule):
    """Discover and enumerate API schemas (OpenAPI, Swagger, GraphQL introspection)."""

    name = "api-schema"
    description = "Discover OpenAPI/Swagger/GraphQL schema endpoints"
    category = "api"

    def get_commands(self, target: str = "", **kwargs: Any) -> list[dict[str, str]]:
        url = target if target.startswith("http") else f"https://{target}"
        base = url.rstrip("/")
        paths = [
            "/swagger.json", "/swagger/v1/swagger.json", "/api-docs",
            "/openapi.json", "/openapi.yaml", "/v2/api-docs", "/v3/api-docs",
            "/api/swagger.json", "/docs", "/redoc",
            "/graphql", "/.well-known/openapi.json",
        ]
        return [
            {"command": f"for p in {' '.join(paths)}; do code=$(curl -s -o /dev/null -w '%{{http_code}}' {base}$p); [ \"$code\" != \"404\" ] && echo \"$code $p\"; done",
             "description": f"Probe common API schema endpoints on {base}"},
        ]

    async def run(self, engine: "Engine", target: str = "", **kwargs: Any) -> ModuleResult:
        output = await engine.run_single_command(self.get_commands(target=target)[0]["command"])
        findings = []
        for line in output.splitlines():
            if line.strip().startswith("200"):
                findings.append({"type": "api_schema_exposed", "detail": line.strip(), "severity": "medium"})
        return ModuleResult(module=self.name, output=output, findings=findings)


class SSRFProbeModule(BaseModule):
    """Test for Server-Side Request Forgery in API parameters."""

    name = "ssrf-api"
    description = "Test API parameters for SSRF vulnerabilities"
    category = "api"

    def get_commands(self, target: str = "", param: str = "url", **kwargs: Any) -> list[dict[str, str]]:
        url = target if target.startswith("http") else f"https://{target}"
        payloads = [
            "http://127.0.0.1",
            "http://localhost",
            "http://[::1]",
            "http://169.254.169.254/latest/meta-data/",
            "http://metadata.google.internal/computeMetadata/v1/",
            "http://0x7f000001",
        ]
        return [
            {"command": f"for p in {' '.join(payloads)}; do echo \"=== $p ===\"; curl -s -o /dev/null -w '%{{http_code}}' '{url}?{param}=$p'; echo; done",
             "description": f"SSRF probe via {param} parameter"},
        ]

    async def run(self, engine: "Engine", target: str = "", param: str = "url", **kwargs: Any) -> ModuleResult:
        output = await engine.run_single_command(self.get_commands(target=target, param=param)[0]["command"])
        findings = []
        if "200" in output and "169.254" in output:
            findings.append({"type": "ssrf", "title": "SSRF to Cloud Metadata Endpoint", "severity": "critical"})
        return ModuleResult(module=self.name, output=output, findings=findings)


class CORSAPIModule(BaseModule):
    """Test CORS configuration on API endpoints."""

    name = "cors-api"
    description = "Test API CORS policy for misconfiguration"
    category = "api"

    def get_commands(self, target: str = "", **kwargs: Any) -> list[dict[str, str]]:
        url = target if target.startswith("http") else f"https://{target}"
        return [
            {"command": f"curl -s -D - -o /dev/null -H 'Origin: https://evil.com' {url} | grep -i 'access-control'",
             "description": f"CORS test with evil origin on {url}"},
            {"command": f"curl -s -D - -o /dev/null -H 'Origin: null' {url} | grep -i 'access-control'",
             "description": f"CORS null origin test on {url}"},
        ]

    async def run(self, engine: "Engine", target: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(target=target, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = []
        if "evil.com" in combined.lower():
            findings.append({"type": "cors_miscfg", "title": "CORS Reflects Arbitrary Origin", "severity": "high"})
        if "null" in combined.lower() and "access-control-allow-origin: null" in combined.lower():
            findings.append({"type": "cors_null", "title": "CORS Allows Null Origin", "severity": "high"})
        return ModuleResult(module=self.name, output=combined, findings=findings)


# ═══════════════════════════════════════════════════════════════════
# Registry
# ═══════════════════════════════════════════════════════════════════

API_MODULES: dict[str, type[BaseModule]] = {
    "rest-fuzz": RESTFuzzModule,
    "jwt-analysis": JWTAnalysisModule,
    "auth-bypass": AuthBypassModule,
    "idor": IDORModule,
    "rate-limit": RateLimitModule,
    "api-schema": APISchemaModule,
    "ssrf-api": SSRFProbeModule,
    "cors-api": CORSAPIModule,
}
