"""
OSINT & information gathering modules — passive reconnaissance,
domain intelligence, email harvesting, and social engineering recon.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from relic.modules.base import BaseModule, ModuleResult

if TYPE_CHECKING:
    from relic.core.engine import Engine


class WhoisModule(BaseModule):
    """WHOIS domain registration lookups."""

    name = "whois"
    description = "WHOIS domain and IP registration data"
    category = "osint"

    def get_commands(self, target: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"whois {target}", "description": f"WHOIS lookup for {target}"},
        ]

    async def run(self, engine: "Engine", target: str = "", **kwargs: Any) -> ModuleResult:
        output = await engine.run_single_command(f"whois {target}")
        findings = []
        for line in output.splitlines():
            ll = line.lower()
            if "registrar:" in ll or "name server:" in ll or "creation date:" in ll:
                findings.append({"type": "whois", "detail": line.strip(), "severity": "info"})
        return ModuleResult(module=self.name, output=output, findings=findings)


class TheHarvesterModule(BaseModule):
    """theHarvester — email, subdomain, and name harvesting."""

    name = "theharvester"
    description = "Harvest emails, names, subdomains, and IPs from public sources"
    category = "osint"

    def get_commands(self, domain: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"theHarvester -d {domain} -b all -l 200 -f /tmp/relic_harvester",
             "description": f"theHarvester on {domain} (all sources)"},
            {"command": "cat /tmp/relic_harvester.xml 2>/dev/null | head -100",
             "description": "Read harvester results"},
        ]

    async def run(self, engine: "Engine", domain: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(domain=domain, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = []
        for line in combined.splitlines():
            if "@" in line and "." in line:
                findings.append({"type": "email", "value": line.strip(), "severity": "info"})
        return ModuleResult(module=self.name, output=combined, findings=findings)


class AmassModule(BaseModule):
    """Amass — in-depth subdomain enumeration."""

    name = "amass"
    description = "Advanced subdomain enumeration with Amass"
    category = "osint"

    def get_commands(self, domain: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"amass enum -passive -d {domain} -o /tmp/relic_amass.txt",
             "description": f"Amass passive enum on {domain}"},
            {"command": f"amass enum -active -d {domain} -o /tmp/relic_amass_active.txt -brute -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt 2>/dev/null",
             "description": f"Amass active enum + brute-force on {domain}"},
            {"command": "cat /tmp/relic_amass.txt /tmp/relic_amass_active.txt 2>/dev/null | sort -u",
             "description": "Combined Amass results"},
        ]

    async def run(self, engine: "Engine", domain: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(domain=domain, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        subs = [l.strip() for l in combined.splitlines() if l.strip() and "." in l]
        findings = [{"type": "subdomain", "value": s, "severity": "info"} for s in subs[:100]]
        return ModuleResult(module=self.name, output=combined, findings=findings)


class SubfinderModule(BaseModule):
    """Subfinder — fast passive subdomain discovery."""

    name = "subfinder"
    description = "Fast passive subdomain enumeration"
    category = "osint"

    def get_commands(self, domain: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"subfinder -d {domain} -silent -o /tmp/relic_subfinder.txt",
             "description": f"Subfinder passive enumeration on {domain}"},
            {"command": f"cat /tmp/relic_subfinder.txt | httpx -silent -status-code -title",
             "description": "Probe discovered subdomains"},
        ]

    async def run(self, engine: "Engine", domain: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(domain=domain, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        return ModuleResult(module=self.name, output="\n".join(outputs))


class ShodanModule(BaseModule):
    """Shodan CLI — internet-wide device/service search."""

    name = "shodan"
    description = "Shodan search for exposed services and devices"
    category = "osint"

    def get_commands(self, target: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"shodan host {target} 2>/dev/null",
             "description": f"Shodan host info for {target}"},
            {"command": f"shodan search hostname:{target} 2>/dev/null | head -20",
             "description": f"Shodan search for {target}"},
        ]

    async def run(self, engine: "Engine", target: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(target=target, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        return ModuleResult(module=self.name, output="\n".join(outputs))


class CensysModule(BaseModule):
    """Censys — internet-wide scanning and certificate transparency."""

    name = "censys"
    description = "Censys host and certificate search"
    category = "osint"

    def get_commands(self, target: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"censys search 'ip:{target}' 2>/dev/null | head -30",
             "description": f"Censys search for {target}"},
        ]

    async def run(self, engine: "Engine", target: str = "", **kwargs: Any) -> ModuleResult:
        output = await engine.run_single_command(self.get_commands(target=target)[0]["command"])
        return ModuleResult(module=self.name, output=output)


class DNSEnumAdvancedModule(BaseModule):
    """Advanced DNS enumeration — records, zone transfers, bruteforce."""

    name = "dns-advanced"
    description = "Comprehensive DNS enumeration (all record types, zone transfer, brute-force)"
    category = "osint"

    def get_commands(self, domain: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"dig {domain} ANY +noall +answer",
             "description": f"All DNS records for {domain}"},
            {"command": f"dig {domain} A +short",
             "description": f"A records for {domain}"},
            {"command": f"dig {domain} AAAA +short",
             "description": f"AAAA records for {domain}"},
            {"command": f"dig {domain} MX +short",
             "description": f"MX records for {domain}"},
            {"command": f"dig {domain} TXT +short",
             "description": f"TXT records for {domain} (SPF, DKIM, DMARC)"},
            {"command": f"dig {domain} NS +short",
             "description": f"NS records for {domain}"},
            {"command": f"dig {domain} SOA +short",
             "description": f"SOA record for {domain}"},
            {"command": f"dig {domain} CNAME +short",
             "description": f"CNAME records for {domain}"},
            {"command": f"dig axfr {domain} @$(dig NS {domain} +short | head -1) 2>/dev/null",
             "description": f"Zone transfer attempt for {domain}"},
            {"command": f"dnsrecon -d {domain} -t brt -D /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt 2>/dev/null",
             "description": f"DNS brute-force on {domain}"},
            {"command": f"fierce --domain {domain} 2>/dev/null",
             "description": f"Fierce DNS enumeration on {domain}"},
        ]

    async def run(self, engine: "Engine", domain: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(domain=domain, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = []
        if "axfr" in combined.lower() and len([l for l in combined.splitlines() if "\t" in l]) > 5:
            findings.append({"type": "zone_transfer", "title": "DNS Zone Transfer Successful", "severity": "high"})
        return ModuleResult(module=self.name, output=combined, findings=findings)


class WaybackModule(BaseModule):
    """Wayback Machine / web archive URL gathering."""

    name = "wayback"
    description = "Gather historical URLs from the Wayback Machine"
    category = "osint"

    def get_commands(self, domain: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"waybackurls {domain} 2>/dev/null | sort -u | head -200",
             "description": f"Wayback Machine URLs for {domain}"},
            {"command": f"gau {domain} 2>/dev/null | sort -u | head -200",
             "description": f"GetAllUrls for {domain}"},
        ]

    async def run(self, engine: "Engine", domain: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(domain=domain, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        return ModuleResult(module=self.name, output="\n".join(outputs))


class CertTransparencyModule(BaseModule):
    """Certificate Transparency log search."""

    name = "cert-transparency"
    description = "Search Certificate Transparency logs for subdomains"
    category = "osint"

    def get_commands(self, domain: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"curl -s 'https://crt.sh/?q=%.{domain}&output=json' | python3 -m json.tool 2>/dev/null | grep name_value | sort -u | head -50",
             "description": f"crt.sh certificate search for {domain}"},
        ]

    async def run(self, engine: "Engine", domain: str = "", **kwargs: Any) -> ModuleResult:
        output = await engine.run_single_command(self.get_commands(domain=domain)[0]["command"])
        return ModuleResult(module=self.name, output=output)


class GoogleDorkModule(BaseModule):
    """Google dorking queries (manual execution)."""

    name = "google-dork"
    description = "Generate Google dork queries for target reconnaissance"
    category = "osint"

    def get_commands(self, domain: str = "", **kwargs: Any) -> list[dict[str, str]]:
        dorks = [
            f"site:{domain} filetype:pdf",
            f"site:{domain} filetype:sql",
            f"site:{domain} filetype:env",
            f"site:{domain} filetype:log",
            f"site:{domain} inurl:admin",
            f"site:{domain} inurl:login",
            f"site:{domain} inurl:api",
            f"site:{domain} intitle:\"index of\"",
            f"site:{domain} ext:xml | ext:conf | ext:cnf | ext:reg | ext:inf | ext:rdp | ext:cfg",
            f"site:{domain} ext:bak | ext:old | ext:tmp",
        ]
        return [{"command": f"echo 'DORK: {d}'", "description": f"Google dork: {d}"} for d in dorks]

    async def run(self, engine: "Engine", domain: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(domain=domain, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        return ModuleResult(module=self.name, output="\n".join(outputs))


class GitLeaksModule(BaseModule):
    """Git repository secret scanning."""

    name = "gitleaks"
    description = "Scan Git repositories for secrets and credentials"
    category = "osint"

    def get_commands(self, repo: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"gitleaks detect --source={repo} --report-path=/tmp/relic_gitleaks.json 2>/dev/null",
             "description": f"Gitleaks secret scan on {repo}"},
            {"command": f"trufflehog git file://{repo} --json 2>/dev/null | head -50",
             "description": f"TruffleHog secret scan on {repo}"},
        ]

    async def run(self, engine: "Engine", repo: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(repo=repo, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = []
        if "secret" in combined.lower() or "password" in combined.lower() or "token" in combined.lower():
            findings.append({"type": "secret_leak", "title": "Secrets Found in Repository", "severity": "critical"})
        return ModuleResult(module=self.name, output=combined, findings=findings)


# ═══════════════════════════════════════════════════════════════════
# Registry
# ═══════════════════════════════════════════════════════════════════

OSINT_MODULES: dict[str, type[BaseModule]] = {
    "whois": WhoisModule,
    "theharvester": TheHarvesterModule,
    "amass": AmassModule,
    "subfinder": SubfinderModule,
    "shodan": ShodanModule,
    "censys": CensysModule,
    "dns-advanced": DNSEnumAdvancedModule,
    "wayback": WaybackModule,
    "cert-transparency": CertTransparencyModule,
    "google-dork": GoogleDorkModule,
    "gitleaks": GitLeaksModule,
}
