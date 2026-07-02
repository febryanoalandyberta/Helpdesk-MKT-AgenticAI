"""
Diagnostic Tools — Read-Only tools for Tier 1 Technical Agent
SSH, Ping, Port Check, System Logs, Service Status, Disk/CPU/Memory
All operations are READ-ONLY per security policy.
"""
import socket
import subprocess
import paramiko
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from loguru import logger


# ─────────────────────────────────────────────
# Ping Host
# ─────────────────────────────────────────────
class PingInput(BaseModel):
    host: str = Field(..., description="IP address or hostname to ping")
    count: int = Field(4, description="Number of ping packets to send")


class PingHost(BaseTool):
    name: str = "ping_host"
    description: str = (
        "Ping a device by IP address or hostname to check reachability. "
        "Returns latency statistics and packet loss percentage."
    )
    args_schema: type = PingInput

    def _run(self, host: str, count: int = 4) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ["ping", "-n", str(count), host],
                capture_output=True, text=True, timeout=30
            )
            output = result.stdout + result.stderr
            reachable = "TTL=" in output or "bytes from" in output.lower()
            logger.info(f"[DiagTool] Ping {host}: {'REACHABLE' if reachable else 'UNREACHABLE'}")
            return {
                "host": host,
                "reachable": reachable,
                "output": output,
                "return_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"host": host, "reachable": False, "error": "Ping timeout"}
        except Exception as e:
            return {"host": host, "reachable": False, "error": str(e)}


# ─────────────────────────────────────────────
# Check Port
# ─────────────────────────────────────────────
class CheckPortInput(BaseModel):
    host: str = Field(..., description="IP address or hostname")
    port: int = Field(..., description="TCP port number to check")
    timeout: int = Field(5, description="Connection timeout in seconds")


class CheckPort(BaseTool):
    name: str = "check_port"
    description: str = (
        "Check if a specific TCP port is open on a remote device. "
        "Useful for checking RDP (3389), SSH (22), HTTP (80/443), POS services."
    )
    args_schema: type = CheckPortInput

    def _run(self, host: str, port: int, timeout: int = 5) -> Dict[str, Any]:
        try:
            with socket.create_connection((host, port), timeout=timeout) as sock:
                logger.info(f"[DiagTool] Port {host}:{port} is OPEN")
                return {"host": host, "port": port, "open": True}
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            return {"host": host, "port": port, "open": False, "error": str(e)}


# ─────────────────────────────────────────────
# SSH Execute (Read-Only)
# ─────────────────────────────────────────────
class SSHExecuteInput(BaseModel):
    host: str = Field(..., description="IP address or hostname")
    username: str = Field(..., description="SSH username")
    password: Optional[str] = Field(None, description="SSH password")
    command: str = Field(..., description="Read-only command to execute (e.g., 'df -h', 'systemctl status X')")
    port: int = Field(22, description="SSH port number")


# Allowed read-only commands (security guardrail)
ALLOWED_COMMANDS = [
    "df", "free", "top", "ps", "systemctl status", "journalctl",
    "cat /var/log", "ls", "pwd", "whoami", "uptime", "netstat",
    "ss", "ifconfig", "ip addr", "hostname", "uname", "lscpu",
    "iostat", "vmstat", "dmesg", "last", "who", "w",
]


class SSHExecuteReadOnly(BaseTool):
    name: str = "ssh_execute_readonly"
    description: str = (
        "Execute a READ-ONLY command on a remote device via SSH. "
        "Only diagnostic commands are allowed (df, ps, systemctl status, journalctl, etc.). "
        "Destructive commands are blocked by security policy."
    )
    args_schema: type = SSHExecuteInput

    def _is_allowed(self, command: str) -> bool:
        cmd_lower = command.lower().strip()
        return any(cmd_lower.startswith(allowed) for allowed in ALLOWED_COMMANDS)

    def _run(self, host: str, username: str, command: str,
             password: Optional[str] = None, port: int = 22) -> Dict[str, Any]:
        if not self._is_allowed(command):
            return {
                "success": False,
                "error": f"BLOCKED: Command '{command}' is not in the allowed read-only list.",
            }
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host, port=port, username=username, password=password, timeout=15)
            stdin, stdout, stderr = ssh.exec_command(command, timeout=30)
            output = stdout.read().decode()
            error = stderr.read().decode()
            ssh.close()
            logger.info(f"[DiagTool] SSH {host}: executed '{command}'")
            return {
                "success": True,
                "host": host,
                "command": command,
                "output": output,
                "error": error,
            }
        except Exception as e:
            logger.error(f"[DiagTool] SSH error on {host}: {e}")
            return {"success": False, "host": host, "error": str(e)}


# ─────────────────────────────────────────────
# Get System Logs
# ─────────────────────────────────────────────
class GetLogsInput(BaseModel):
    host: str = Field(..., description="IP address or hostname")
    username: str = Field(..., description="SSH username")
    password: Optional[str] = Field(None, description="SSH password")
    log_type: str = Field("syslog", description="Log type: syslog, auth, application")
    lines: int = Field(50, description="Number of log lines to retrieve")


class GetSystemLogs(BaseTool):
    name: str = "get_system_logs"
    description: str = (
        "Retrieve system log entries from a remote device via SSH. "
        "Supports syslog, auth, and application logs."
    )
    args_schema: type = GetLogsInput

    def _run(self, host: str, username: str, log_type: str = "syslog",
             password: Optional[str] = None, lines: int = 50) -> Dict[str, Any]:
        log_commands = {
            "syslog": f"tail -n {lines} /var/log/syslog",
            "auth": f"tail -n {lines} /var/log/auth.log",
            "application": f"journalctl -n {lines} --no-pager",
        }
        command = log_commands.get(log_type, f"journalctl -n {lines} --no-pager")
        ssh_tool = SSHExecuteReadOnly()
        return ssh_tool._run(host=host, username=username, password=password, command=command)


# ─────────────────────────────────────────────
# Get Service Status
# ─────────────────────────────────────────────
class ServiceStatusInput(BaseModel):
    host: str = Field(..., description="IP address or hostname")
    username: str = Field(..., description="SSH username")
    password: Optional[str] = Field(None, description="SSH password")
    service_name: str = Field(..., description="Service name to check status (e.g., 'nginx', 'postgresql')")


class GetServiceStatus(BaseTool):
    name: str = "get_service_status"
    description: str = "Check the running status of a specific system service on a remote device."
    args_schema: type = ServiceStatusInput

    def _run(self, host: str, username: str, service_name: str,
             password: Optional[str] = None) -> Dict[str, Any]:
        command = f"systemctl status {service_name}"
        ssh_tool = SSHExecuteReadOnly()
        return ssh_tool._run(host=host, username=username, password=password, command=command)


# ─────────────────────────────────────────────
# Get Disk Usage
# ─────────────────────────────────────────────
class DiskUsageInput(BaseModel):
    host: str = Field(..., description="IP address or hostname")
    username: str = Field(..., description="SSH username")
    password: Optional[str] = Field(None, description="SSH password")


class GetDiskUsage(BaseTool):
    name: str = "get_disk_usage"
    description: str = "Retrieve disk usage statistics from a remote device. Returns used/free space per partition."
    args_schema: type = DiskUsageInput

    def _run(self, host: str, username: str, password: Optional[str] = None) -> Dict[str, Any]:
        ssh_tool = SSHExecuteReadOnly()
        return ssh_tool._run(host=host, username=username, password=password, command="df -h")


# ─────────────────────────────────────────────
# Get CPU & Memory Usage
# ─────────────────────────────────────────────
class CPUMemoryInput(BaseModel):
    host: str = Field(..., description="IP address or hostname")
    username: str = Field(..., description="SSH username")
    password: Optional[str] = Field(None, description="SSH password")


class GetCPUMemoryUsage(BaseTool):
    name: str = "get_cpu_memory_usage"
    description: str = "Retrieve CPU and memory usage statistics from a remote device."
    args_schema: type = CPUMemoryInput

    def _run(self, host: str, username: str, password: Optional[str] = None) -> Dict[str, Any]:
        ssh_tool = SSHExecuteReadOnly()
        mem_result = ssh_tool._run(host=host, username=username, password=password, command="free -h")
        cpu_result = ssh_tool._run(host=host, username=username, password=password, command="uptime")
        return {
            "host": host,
            "memory": mem_result.get("output", ""),
            "cpu_load": cpu_result.get("output", ""),
        }


class DiagnosticTools:
    @staticmethod
    def get_all() -> list:
        return [
            PingHost(),
            CheckPort(),
            SSHExecuteReadOnly(),
            GetSystemLogs(),
            GetServiceStatus(),
            GetDiskUsage(),
            GetCPUMemoryUsage(),
        ]
