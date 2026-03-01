"""
VM Manager — abstracts provisioning and command execution across
Vagrant, Docker, and direct SSH targets.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import paramiko

from relic.core.config import VMConfig

log = logging.getLogger("relic.vm")


class VMState(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    SUSPENDED = "suspended"
    PROVISIONING = "provisioning"
    ERROR = "error"


@dataclass
class VMInfo:
    name: str = "relic-vm"
    state: VMState = VMState.STOPPED
    ip: str = ""
    ssh_port: int = 22
    ssh_user: str = "vagrant"
    ssh_key: str = ""
    provider: str = "vagrant"
    metadata: dict[str, Any] = field(default_factory=dict)


# ══════════════════════════════════════════════════════════════════════
# Abstract base
# ══════════════════════════════════════════════════════════════════════

class VMProvider(ABC):
    """Interface that all VM providers must implement."""

    @abstractmethod
    async def create(self) -> VMInfo:
        ...

    @abstractmethod
    async def start(self) -> VMInfo:
        ...

    @abstractmethod
    async def stop(self) -> None:
        ...

    @abstractmethod
    async def destroy(self) -> None:
        ...

    @abstractmethod
    async def status(self) -> VMInfo:
        ...

    @abstractmethod
    async def snapshot(self, name: str) -> None:
        ...

    @abstractmethod
    async def restore_snapshot(self, name: str) -> None:
        ...


# ══════════════════════════════════════════════════════════════════════
# Vagrant provider
# ══════════════════════════════════════════════════════════════════════

VAGRANTFILE_TEMPLATE = """\
Vagrant.configure("2") do |config|
  config.vm.box = "{base_image}"
  config.vm.hostname = "relic-target"

  config.vm.provider "virtualbox" do |vb|
    vb.memory = "{memory}"
    vb.cpus = {cpus}
    vb.name = "relic-pentest-vm"
    vb.customize ["modifyvm", :id, "--natdnshostresolver1", "on"]
    vb.customize ["modifyvm", :id, "--nicpromisc2", "allow-all"]
  end

  config.vm.network "{network}", type: "dhcp"
  # Allow unrestricted outbound (bridged or port forward everything)
  config.vm.network "forwarded_port", guest: 1, host: 1,
    auto_correct: true, protocol: "tcp"

  config.vm.synced_folder "{shared_folder}", "/shared"

  config.ssh.insert_key = true

  config.vm.provision "shell", privileged: true, inline: <<-SHELL
    set -e

    # --- Root access & no restrictions ---
    echo 'vagrant ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/vagrant
    chmod 0440 /etc/sudoers.d/vagrant
    echo 'root:relic' | chpasswd

    # --- Ensure Kali tools metapackage ---
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq kali-tools-top10 kali-tools-web \\
      kali-tools-information-gathering kali-tools-vulnerability \\
      kali-tools-passwords kali-tools-exploitation \\
      seclists wordlists nmap nikto sqlmap hydra john hashcat \\
      gobuster feroxbuster ffuf wfuzz masscan \\
      sslscan testssl.sh sslyze \\
      python3-pip golang-go \\
      2>/dev/null || true

    # --- Go-based tools ---
    export GOPATH=/opt/go
    go install github.com/projectdiscovery/httpx/cmd/httpx@latest 2>/dev/null || true
    go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest 2>/dev/null || true
    go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest 2>/dev/null || true
    go install github.com/tomnomnom/waybackurls@latest 2>/dev/null || true
    go install github.com/sensepost/gowitness@latest 2>/dev/null || true
    ln -sf /opt/go/bin/* /usr/local/bin/ 2>/dev/null || true

    # --- Remove IP/firewall restrictions inside VM ---
    iptables -F 2>/dev/null || true
    iptables -P INPUT ACCEPT 2>/dev/null || true
    iptables -P FORWARD ACCEPT 2>/dev/null || true
    iptables -P OUTPUT ACCEPT 2>/dev/null || true

    echo "[relic] VM fully provisioned — unrestricted access ready."
  SHELL
end
"""


class VagrantProvider(VMProvider):
    """Provision and manage VMs using Vagrant."""

    def __init__(self, config: VMConfig, workdir: str = "./.relic/vm") -> None:
        self.config = config
        self.workdir = workdir
        self._info = VMInfo(provider="vagrant")

    async def create(self) -> VMInfo:
        import os
        os.makedirs(self.workdir, exist_ok=True)

        vagrantfile = VAGRANTFILE_TEMPLATE.format(
            base_image=self.config.base_image,
            memory=self.config.memory,
            cpus=self.config.cpus,
            network=self.config.network,
            shared_folder=self.config.shared_folder,
        )
        vf_path = os.path.join(self.workdir, "Vagrantfile")
        with open(vf_path, "w") as f:
            f.write(vagrantfile)

        log.info("Created Vagrantfile at %s", vf_path)
        self._info.state = VMState.STOPPED
        return self._info

    async def start(self) -> VMInfo:
        self._info.state = VMState.PROVISIONING
        log.info("Starting Vagrant VM...")

        proc = await asyncio.create_subprocess_exec(
            "vagrant", "up",
            cwd=self.workdir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            log.error("Vagrant up failed: %s", stderr.decode())
            self._info.state = VMState.ERROR
            return self._info

        # Get SSH config
        proc2 = await asyncio.create_subprocess_exec(
            "vagrant", "ssh-config",
            cwd=self.workdir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        ssh_out, _ = await proc2.communicate()
        self._parse_ssh_config(ssh_out.decode())

        if self.config.snapshot_on_start:
            await self.snapshot("relic-initial")

        self._info.state = VMState.RUNNING
        log.info("VM running at %s:%d", self._info.ip, self._info.ssh_port)
        return self._info

    async def stop(self) -> None:
        await asyncio.create_subprocess_exec("vagrant", "halt", cwd=self.workdir)
        self._info.state = VMState.STOPPED

    async def destroy(self) -> None:
        await asyncio.create_subprocess_exec("vagrant", "destroy", "-f", cwd=self.workdir)
        self._info.state = VMState.STOPPED

    async def status(self) -> VMInfo:
        proc = await asyncio.create_subprocess_exec(
            "vagrant", "status", "--machine-readable",
            cwd=self.workdir,
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode()
        if "running" in output:
            self._info.state = VMState.RUNNING
        elif "poweroff" in output or "not_created" in output:
            self._info.state = VMState.STOPPED
        return self._info

    async def snapshot(self, name: str) -> None:
        await asyncio.create_subprocess_exec(
            "vagrant", "snapshot", "save", name,
            cwd=self.workdir,
        )
        log.info("Snapshot '%s' saved.", name)

    async def restore_snapshot(self, name: str) -> None:
        await asyncio.create_subprocess_exec(
            "vagrant", "snapshot", "restore", name,
            cwd=self.workdir,
        )
        log.info("Snapshot '%s' restored.", name)

    def _parse_ssh_config(self, text: str) -> None:
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("HostName"):
                self._info.ip = line.split()[-1]
            elif line.startswith("Port"):
                self._info.ssh_port = int(line.split()[-1])
            elif line.startswith("User"):
                self._info.ssh_user = line.split()[-1]
            elif line.startswith("IdentityFile"):
                self._info.ssh_key = line.split()[-1]


# ══════════════════════════════════════════════════════════════════════
# SSH executor (used by all providers)
# ══════════════════════════════════════════════════════════════════════

class SSHExecutor:
    """Execute commands on a remote VM over SSH using Paramiko."""

    def __init__(self, info: VMInfo) -> None:
        self.info = info
        self._client: paramiko.SSHClient | None = None

    def connect(self) -> None:
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        kwargs: dict[str, Any] = {
            "hostname": self.info.ip,
            "port": self.info.ssh_port,
            "username": self.info.ssh_user,
        }
        if self.info.ssh_key:
            kwargs["key_filename"] = self.info.ssh_key
        else:
            kwargs["password"] = ""

        log.info("SSH connecting to %s@%s:%d", self.info.ssh_user, self.info.ip, self.info.ssh_port)
        self._client.connect(**kwargs)

    def disconnect(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def exec_command(self, command: str, timeout: int = 300) -> tuple[str, int]:
        """Execute a command and return (combined_output, exit_code)."""
        if not self._client:
            raise RuntimeError("SSH not connected")

        _, stdout, stderr = self._client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        combined = out + ("\n" + err if err else "")
        return combined, exit_code


# ══════════════════════════════════════════════════════════════════════
# VM Manager — high-level facade
# ══════════════════════════════════════════════════════════════════════

class VMManager:
    """
    High-level manager combining a VM provider with SSH execution.
    This is the primary interface the engine uses.
    """

    def __init__(self, config: VMConfig) -> None:
        self.config = config
        self.provider: VMProvider = self._create_provider(config)
        self.ssh: SSHExecutor | None = None
        self.info: VMInfo = VMInfo()

    def _create_provider(self, config: VMConfig) -> VMProvider:
        if config.provider == "vagrant":
            return VagrantProvider(config)
        # Future: docker, libvirt, etc.
        raise ValueError(f"Unsupported VM provider: {config.provider}")

    async def provision(self) -> VMInfo:
        """Create and start the VM."""
        self.info = await self.provider.create()
        self.info = await self.provider.start()
        self.ssh = SSHExecutor(self.info)
        self.ssh.connect()
        return self.info

    async def execute(self, command: str, timeout: int = 300) -> tuple[str, int]:
        """Execute a command in the VM. Returns (output, exit_code)."""
        if self.ssh is None:
            raise RuntimeError("VM not provisioned or SSH not connected")
        return await asyncio.to_thread(self.ssh.exec_command, command, timeout)

    async def teardown(self) -> None:
        """Stop and destroy the VM."""
        if self.ssh:
            self.ssh.disconnect()
        await self.provider.destroy()
        self.info.state = VMState.STOPPED

    async def reset(self) -> None:
        """Restore the VM to its initial snapshot."""
        await self.provider.restore_snapshot("relic-initial")
        if self.ssh:
            self.ssh.disconnect()
            self.ssh.connect()

    async def status(self) -> VMInfo:
        return await self.provider.status()
