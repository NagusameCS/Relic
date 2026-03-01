"""
Reconnaissance module — automated enumeration and information gathering.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from relic.modules.base import BaseModule, ModuleResult

if TYPE_CHECKING:
    from relic.core.engine import Engine


class PortScanModule(BaseModule):
    """Nmap-based port scanning."""

    name = "port-scan"
    description = "Scan target for open ports and service versions"
    category = "recon"

    def get_commands(self, target: str = "", ports: str = "-", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {
                "command": f"nmap -sV -sC -O -oN /tmp/relic_nmap.txt {target}",
                "description": f"Full service/version scan with OS detection on {target}",
            },
            {
                "command": "cat /tmp/relic_nmap.txt",
                "description": "Read nmap results",
            },
        ]

    async def run(self, engine: "Engine", target: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(target=target, **kwargs)
        all_output = []
        for cmd in commands:
            output = await engine.run_single_command(cmd["command"])
            all_output.append(output)

        combined = "\n".join(all_output)
        return ModuleResult(
            module=self.name,
            output=combined,
            findings=self._parse_findings(combined),
        )

    def _parse_findings(self, output: str) -> list[dict[str, Any]]:
        findings = []
        for line in output.splitlines():
            if "/tcp" in line and "open" in line:
                parts = line.split()
                findings.append({
                    "type": "open_port",
                    "port": parts[0] if parts else "",
                    "state": parts[1] if len(parts) > 1 else "",
                    "service": parts[2] if len(parts) > 2 else "",
                    "version": " ".join(parts[3:]) if len(parts) > 3 else "",
                    "severity": "info",
                })
        return findings


class SubdomainEnumModule(BaseModule):
    """Subdomain enumeration using multiple tools."""

    name = "subdomain-enum"
    description = "Enumerate subdomains of a target domain"
    category = "recon"

    def get_commands(self, domain: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {
                "command": f"subfinder -d {domain} -silent -o /tmp/relic_subs.txt",
                "description": f"Subdomain discovery for {domain}",
            },
            {
                "command": "cat /tmp/relic_subs.txt | sort -u",
                "description": "List discovered subdomains",
            },
            {
                "command": f"cat /tmp/relic_subs.txt | httpx -silent -status-code -title",
                "description": "Probe discovered subdomains for live HTTP services",
            },
        ]

    async def run(self, engine: "Engine", domain: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(domain=domain, **kwargs)
        all_output = []
        for cmd in commands:
            output = await engine.run_single_command(cmd["command"])
            all_output.append(output)

        combined = "\n".join(all_output)
        return ModuleResult(
            module=self.name,
            output=combined,
            findings=[{"type": "subdomain", "domain": line.strip()}
                      for line in combined.splitlines() if line.strip() and "." in line],
        )


class DNSReconModule(BaseModule):
    """DNS enumeration and zone transfer attempts."""

    name = "dns-recon"
    description = "DNS enumeration including zone transfer attempts"
    category = "recon"

    def get_commands(self, domain: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {
                "command": f"dig {domain} ANY +noall +answer",
                "description": f"Full DNS record lookup for {domain}",
            },
            {
                "command": f"dig axfr {domain}",
                "description": f"Attempt DNS zone transfer for {domain}",
            },
            {
                "command": f"whois {domain}",
                "description": f"WHOIS lookup for {domain}",
            },
        ]

    async def run(self, engine: "Engine", domain: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(domain=domain, **kwargs)
        all_output = []
        for cmd in commands:
            output = await engine.run_single_command(cmd["command"])
            all_output.append(output)
        return ModuleResult(module=self.name, output="\n".join(all_output))


class WebReconModule(BaseModule):
    """Web application reconnaissance."""

    name = "web-recon"
    description = "Web application enumeration — directories, technologies, headers"
    category = "recon"

    def get_commands(self, url: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {
                "command": f"curl -sI {url}",
                "description": f"Grab HTTP headers from {url}",
            },
            {
                "command": f"whatweb -a 3 {url}",
                "description": f"Identify technologies on {url}",
            },
            {
                "command": f"gobuster dir -u {url} -w /usr/share/wordlists/dirb/common.txt -q",
                "description": f"Directory brute-force on {url}",
            },
            {
                "command": f"nikto -h {url} -output /tmp/relic_nikto.txt",
                "description": f"Nikto vulnerability scan on {url}",
            },
        ]

    async def run(self, engine: "Engine", url: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(url=url, **kwargs)
        all_output = []
        for cmd in commands:
            output = await engine.run_single_command(cmd["command"])
            all_output.append(output)
        return ModuleResult(module=self.name, output="\n".join(all_output))


class TechDetectModule(BaseModule):
    """Technology fingerprinting via multiple tools."""

    name = "tech-detect"
    description = "Fingerprint web technologies, frameworks, and server software"
    category = "recon"

    def get_commands(self, url: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"whatweb -a 3 --color=never {url}", "description": f"WhatWeb on {url}"},
            {"command": f"webanalyze -host {url} -silent 2>/dev/null", "description": f"Wappalyzer-cli on {url}"},
            {"command": f"curl -sI {url} | grep -iE '(server|x-powered|x-aspnet|x-generator)'", "description": "Server header fingerprint"},
        ]

    async def run(self, engine: "Engine", url: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(url=url, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        return ModuleResult(module=self.name, output="\n".join(outputs))


class ScreenshotModule(BaseModule):
    """Take screenshots of web pages for visual recon."""

    name = "screenshot"
    description = "Capture web page screenshots with gowitness or eyewitness"
    category = "recon"

    def get_commands(self, url: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"gowitness single {url} --output /tmp/relic_screenshots/ 2>/dev/null",
             "description": f"Screenshot {url} with gowitness"},
        ]

    async def run(self, engine: "Engine", url: str = "", **kwargs: Any) -> ModuleResult:
        output = await engine.run_single_command(self.get_commands(url=url)[0]["command"])
        return ModuleResult(module=self.name, output=output)


class HTTPProbeModule(BaseModule):
    """Probe hosts for live HTTP(S) services."""

    name = "http-probe"
    description = "Probe for live HTTP/HTTPS services with httpx"
    category = "recon"

    def get_commands(self, target: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"echo '{target}' | httpx -silent -status-code -title -tech-detect -follow-redirects",
             "description": f"httpx probe on {target}"},
        ]

    async def run(self, engine: "Engine", target: str = "", **kwargs: Any) -> ModuleResult:
        output = await engine.run_single_command(self.get_commands(target=target)[0]["command"])
        return ModuleResult(module=self.name, output=output)


class VHostEnumModule(BaseModule):
    """Virtual host enumeration."""

    name = "vhost-enum"
    description = "Enumerate virtual hosts via Host header brute-force"
    category = "recon"

    def get_commands(self, target: str = "", domain: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"gobuster vhost -u http://{target} -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt --append-domain -q 2>/dev/null | head -30",
             "description": f"VHost brute-force on {target}"},
            {"command": f"ffuf -u http://{target} -H 'Host: FUZZ.{domain or target}' -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt -mc all -fc 301,302,404 -fs 0 2>/dev/null | head -30",
             "description": f"ffuf vhost enumeration on {target}"},
        ]

    async def run(self, engine: "Engine", target: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(target=target, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        return ModuleResult(module=self.name, output="\n".join(outputs))


class CloudEnumModule(BaseModule):
    """Enumerate cloud assets (S3, Azure, GCP buckets)."""

    name = "cloud-enum"
    description = "Enumerate cloud storage buckets and assets"
    category = "recon"

    def get_commands(self, keyword: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"cloud_enum -k {keyword} --disable-azure --disable-gcp 2>/dev/null | head -30",
             "description": f"Enumerate AWS S3 buckets for '{keyword}'"},
            {"command": f"s3scanner scan --bucket {keyword} 2>/dev/null",
             "description": f"S3 bucket scan for '{keyword}'"},
        ]

    async def run(self, engine: "Engine", keyword: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(keyword=keyword, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        return ModuleResult(module=self.name, output="\n".join(outputs))


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

RECON_MODULES: dict[str, type[BaseModule]] = {
    "port-scan": PortScanModule,
    "subdomain-enum": SubdomainEnumModule,
    "dns-recon": DNSReconModule,
    "web-recon": WebReconModule,
    "tech-detect": TechDetectModule,
    "screenshot": ScreenshotModule,
    "http-probe": HTTPProbeModule,
    "vhost-enum": VHostEnumModule,
    "cloud-enum": CloudEnumModule,
}
