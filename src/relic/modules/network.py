"""
Network pentesting modules — port scanning, service enumeration,
traffic analysis, MITM, and network-level attacks.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from relic.modules.base import BaseModule, ModuleResult

if TYPE_CHECKING:
    from relic.core.engine import Engine


# ═══════════════════════════════════════════════════════════════════
# Advanced Port / Service Scanning
# ═══════════════════════════════════════════════════════════════════

class MasscanModule(BaseModule):
    """Masscan — high-speed port scanner."""

    name = "masscan"
    description = "High-speed TCP port scanner (covers all 65535 ports fast)"
    category = "network"

    def get_commands(self, target: str = "", rate: int = 10000, **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"masscan {target} -p0-65535 --rate {rate} -oG /tmp/relic_masscan.txt",
             "description": f"Masscan full port scan on {target} at rate {rate}"},
            {"command": "cat /tmp/relic_masscan.txt | grep open",
             "description": "Extract open ports from masscan results"},
        ]

    async def run(self, engine: "Engine", target: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(target=target, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = [{"type": "open_port", "port": line.strip(), "severity": "info"}
                    for line in combined.splitlines() if "open" in line.lower()]
        return ModuleResult(module=self.name, output=combined, findings=findings)


class RustScanModule(BaseModule):
    """RustScan — fast port scanner that pipes to nmap."""

    name = "rustscan"
    description = "Ultra-fast port scanner with nmap integration"
    category = "network"

    def get_commands(self, target: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"rustscan -a {target} --ulimit 5000 -- -sV -sC -oN /tmp/relic_rustscan.txt",
             "description": f"RustScan + nmap service detection on {target}"},
            {"command": "cat /tmp/relic_rustscan.txt",
             "description": "Read RustScan results"},
        ]

    async def run(self, engine: "Engine", target: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(target=target, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        return ModuleResult(module=self.name, output="\n".join(outputs))


class NmapAdvancedModule(BaseModule):
    """Advanced Nmap scanning profiles."""

    name = "nmap-advanced"
    description = "Advanced nmap scans — UDP, scripts, vuln detection, firewall evasion"
    category = "network"

    def get_commands(self, target: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"nmap -sV -sC -O -A -T4 -oN /tmp/relic_nmap_full.txt {target}",
             "description": f"Aggressive nmap scan with OS/version/script detection on {target}"},
            {"command": f"nmap -sU --top-ports 100 -oN /tmp/relic_nmap_udp.txt {target}",
             "description": f"UDP top-100 port scan on {target}"},
            {"command": f"nmap --script=vuln -oN /tmp/relic_nmap_vuln.txt {target}",
             "description": f"Nmap vulnerability scripts on {target}"},
            {"command": f"nmap -sV --script=banner -oN /tmp/relic_nmap_banner.txt {target}",
             "description": f"Banner grabbing on {target}"},
            {"command": f"nmap -Pn -sS -f --data-length 50 {target}",
             "description": f"Firewall evasion scan (fragmented packets) on {target}"},
            {"command": f"nmap --script=http-enum -p 80,443,8080,8443 {target}",
             "description": f"HTTP enumeration scripts on {target}"},
        ]

    async def run(self, engine: "Engine", target: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(target=target, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = []
        for line in combined.splitlines():
            if "VULNERABLE" in line or "vuln" in line.lower():
                findings.append({"type": "network_vuln", "title": line.strip(), "severity": "high"})
        return ModuleResult(module=self.name, output=combined, findings=findings)


# ═══════════════════════════════════════════════════════════════════
# Network Sniffing / MITM
# ═══════════════════════════════════════════════════════════════════

class TcpdumpModule(BaseModule):
    """Packet capture with tcpdump."""

    name = "tcpdump"
    description = "Network packet capture and analysis"
    category = "network"

    def get_commands(self, interface: str = "eth0", target: str = "",
                     duration: int = 30, **kwargs: Any) -> list[dict[str, str]]:
        host_filter = f"host {target}" if target else ""
        return [
            {"command": f"timeout {duration} tcpdump -i {interface} {host_filter} -w /tmp/relic_capture.pcap -c 1000",
             "description": f"Capture packets on {interface} for {duration}s"},
            {"command": f"tcpdump -r /tmp/relic_capture.pcap -nn | head -50",
             "description": "Read captured packets"},
            {"command": f"tcpdump -r /tmp/relic_capture.pcap -nn -A | grep -iE 'password|user|login|token|cookie' | head -20",
             "description": "Search for credentials in captures"},
        ]

    async def run(self, engine: "Engine", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(**kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = []
        if "password" in combined.lower() or "token" in combined.lower():
            findings.append({"type": "credential_leak", "title": "Credentials in Network Traffic", "severity": "critical"})
        return ModuleResult(module=self.name, output=combined, findings=findings)


class ARPSpoofModule(BaseModule):
    """ARP spoofing / poisoning."""

    name = "arp-spoof"
    description = "ARP spoofing for MITM attacks"
    category = "network"

    def get_commands(self, target: str = "", gateway: str = "",
                     interface: str = "eth0", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": "echo 1 > /proc/sys/net/ipv4/ip_forward",
             "description": "Enable IP forwarding"},
            {"command": f"arpspoof -i {interface} -t {target} {gateway} &",
             "description": f"ARP spoof {target} -> {gateway}"},
            {"command": f"arpspoof -i {interface} -t {gateway} {target} &",
             "description": f"ARP spoof {gateway} -> {target}"},
        ]

    async def run(self, engine: "Engine", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(**kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        return ModuleResult(module=self.name, output="\n".join(outputs))


class ResponderModule(BaseModule):
    """Responder — LLMNR/NBT-NS/MDNS poisoner."""

    name = "responder"
    description = "LLMNR/NBT-NS/MDNS poisoner for credential capture"
    category = "network"

    def get_commands(self, interface: str = "eth0", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"responder -I {interface} -wrf 2>/dev/null &",
             "description": f"Start Responder on {interface}"},
            {"command": "sleep 30 && cat /usr/share/responder/logs/*.txt 2>/dev/null | head -50",
             "description": "Check Responder captured hashes"},
        ]

    async def run(self, engine: "Engine", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(**kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = []
        if "NTLMv" in combined or "Hash" in combined:
            findings.append({"type": "ntlm_hash", "title": "NTLM Hashes Captured", "severity": "critical"})
        return ModuleResult(module=self.name, output=combined, findings=findings)


class BettercapModule(BaseModule):
    """Bettercap — network attack and MITM framework."""

    name = "bettercap"
    description = "Network reconnaissance, MITM, and attack framework"
    category = "network"

    def get_commands(self, target: str = "", interface: str = "eth0",
                     **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"bettercap -iface {interface} -eval 'net.probe on; net.sniff on; sleep 15; net.show' -no-colors 2>/dev/null",
             "description": f"Bettercap network discovery on {interface}"},
        ]

    async def run(self, engine: "Engine", **kwargs: Any) -> ModuleResult:
        output = await engine.run_single_command(self.get_commands(**kwargs)[0]["command"])
        return ModuleResult(module=self.name, output=output)


# ═══════════════════════════════════════════════════════════════════
# SMB / NetBIOS / LDAP / Kerberos
# ═══════════════════════════════════════════════════════════════════

class SMBEnumModule(BaseModule):
    """SMB enumeration and exploitation."""

    name = "smb-enum"
    description = "SMB share enumeration, user listing, and vulnerability checks"
    category = "network"

    def get_commands(self, target: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"enum4linux -a {target}",
             "description": f"Full SMB enumeration on {target}"},
            {"command": f"smbclient -L //{target} -N",
             "description": f"List SMB shares on {target} (null session)"},
            {"command": f"crackmapexec smb {target} --shares",
             "description": f"CrackMapExec share enumeration on {target}"},
            {"command": f"nmap --script smb-vuln* -p 445 {target}",
             "description": f"Nmap SMB vulnerability scripts on {target}"},
            {"command": f"smbmap -H {target}",
             "description": f"SMBMap share permissions on {target}"},
        ]

    async def run(self, engine: "Engine", target: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(target=target, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        combined = "\n".join(outputs)
        findings = []
        if "READ" in combined or "WRITE" in combined:
            findings.append({"type": "smb_access", "title": "SMB Share Access", "severity": "medium"})
        if "VULNERABLE" in combined or "MS17-010" in combined:
            findings.append({"type": "smb_vuln", "title": "SMB Vulnerability Detected", "severity": "critical"})
        return ModuleResult(module=self.name, output=combined, findings=findings)


class LDAPEnumModule(BaseModule):
    """LDAP enumeration."""

    name = "ldap-enum"
    description = "LDAP enumeration and information gathering"
    category = "network"

    def get_commands(self, target: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"ldapsearch -x -H ldap://{target} -b '' -s base '(objectclass=*)' namingContexts",
             "description": f"LDAP base enumeration on {target}"},
            {"command": f"nmap --script ldap-rootdse -p 389 {target}",
             "description": f"Nmap LDAP scripts on {target}"},
            {"command": f"ldapdomaindump -u '' -p '' ldap://{target} -o /tmp/relic_ldap/ 2>/dev/null",
             "description": f"LDAP domain dump on {target}"},
        ]

    async def run(self, engine: "Engine", target: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(target=target, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        return ModuleResult(module=self.name, output="\n".join(outputs))


class SNMPEnumModule(BaseModule):
    """SNMP enumeration."""

    name = "snmp-enum"
    description = "SNMP community string brute-force and enumeration"
    category = "network"

    def get_commands(self, target: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"onesixtyone -c /usr/share/seclists/Discovery/SNMP/common-snmp-community-strings.txt {target}",
             "description": f"SNMP community string brute-force on {target}"},
            {"command": f"snmpwalk -v2c -c public {target}",
             "description": f"SNMP walk with public community on {target}"},
            {"command": f"snmp-check {target} 2>/dev/null",
             "description": f"SNMP enumeration on {target}"},
        ]

    async def run(self, engine: "Engine", target: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(target=target, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        return ModuleResult(module=self.name, output="\n".join(outputs))


class NetcatModule(BaseModule):
    """Netcat — TCP/UDP networking utility."""

    name = "netcat"
    description = "Banner grabbing and port connectivity testing with netcat"
    category = "network"

    def get_commands(self, target: str = "", ports: str = "21,22,25,80,443",
                     **kwargs: Any) -> list[dict[str, str]]:
        cmds = []
        for port in ports.split(","):
            port = port.strip()
            cmds.append({
                "command": f"echo '' | timeout 5 nc -vn {target} {port} 2>&1",
                "description": f"Banner grab {target}:{port}",
            })
        return cmds

    async def run(self, engine: "Engine", target: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(target=target, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        return ModuleResult(module=self.name, output="\n".join(outputs))


class PingModule(BaseModule):
    """Ping sweep and host discovery."""

    name = "ping-sweep"
    description = "ICMP ping sweep and host discovery"
    category = "network"

    def get_commands(self, target: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"nmap -sn {target}",
             "description": f"Ping sweep on {target}"},
            {"command": f"fping -a -g {target} 2>/dev/null",
             "description": f"Fast ping sweep with fping on {target}"},
        ]

    async def run(self, engine: "Engine", target: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(target=target, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        return ModuleResult(module=self.name, output="\n".join(outputs))


class TracerouteModule(BaseModule):
    """Network traceroute and path analysis."""

    name = "traceroute"
    description = "Network path and hop analysis"
    category = "network"

    def get_commands(self, target: str = "", **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"command": f"traceroute {target}",
             "description": f"Traceroute to {target}"},
            {"command": f"mtr -r -c 10 {target} 2>/dev/null || traceroute -T {target}",
             "description": f"MTR path analysis to {target}"},
        ]

    async def run(self, engine: "Engine", target: str = "", **kwargs: Any) -> ModuleResult:
        commands = self.get_commands(target=target, **kwargs)
        outputs = [await engine.run_single_command(c["command"]) for c in commands]
        return ModuleResult(module=self.name, output="\n".join(outputs))


# ═══════════════════════════════════════════════════════════════════
# Registry
# ═══════════════════════════════════════════════════════════════════

NETWORK_MODULES: dict[str, type[BaseModule]] = {
    "masscan": MasscanModule,
    "rustscan": RustScanModule,
    "nmap-advanced": NmapAdvancedModule,
    "tcpdump": TcpdumpModule,
    "arp-spoof": ARPSpoofModule,
    "responder": ResponderModule,
    "bettercap": BettercapModule,
    "smb-enum": SMBEnumModule,
    "ldap-enum": LDAPEnumModule,
    "snmp-enum": SNMPEnumModule,
    "netcat": NetcatModule,
    "ping-sweep": PingModule,
    "traceroute": TracerouteModule,
}
