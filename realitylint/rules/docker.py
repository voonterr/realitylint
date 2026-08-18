from __future__ import annotations

import re
import shlex
from pathlib import Path

import yaml
from yaml.composer import ComposerError
from yaml.events import AliasEvent

from ..models import Finding
from .common import Command, display_path, extract_commands, resolve_inside

COMPOSE_NAMES = ("compose.yaml", "compose.yml", "docker-compose.yaml", "docker-compose.yml")
SERVICE_COMMANDS = {"up", "run", "exec", "logs", "stop", "start", "restart", "rm", "kill", "pull", "build"}
OPTIONS_WITH_VALUE = {
    "-f", "--file", "--env-file", "--project-directory", "--project-name", "--profile",
    "--scale", "--timeout", "--wait-timeout", "--exit-code-from", "--pull",
    "-p", "--publish", "--name", "-e", "--env", "-u", "--user", "-w", "--workdir",
}


def _tokens(command: str) -> list[str]:
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return command.split()


def _compose_invocation(root: Path, command: Command) -> tuple[Path | None, str | None, list[str], list[str]]:
    tokens = _tokens(command.text)
    try:
        docker_index = next(i for i, token in enumerate(tokens) if token.lower() == "docker")
    except StopIteration:
        return None, None, [], []
    if docker_index + 1 >= len(tokens) or tokens[docker_index + 1].lower() != "compose":
        return None, None, [], []

    base = command.base
    compose_file: Path | None = None
    subcommand: str | None = None
    tail: list[str] = []
    profiles: list[str] = []
    i = docker_index + 2
    while i < len(tokens):
        token = tokens[i]
        lower = token.lower()
        if lower in ("-f", "--file") and i + 1 < len(tokens):
            compose_file = resolve_inside(root, base, tokens[i + 1])
            i += 2
            continue
        if lower.startswith("--file="):
            compose_file = resolve_inside(root, base, token.split("=", 1)[1])
            i += 1
            continue
        if lower == "--profile" and i + 1 < len(tokens):
            profiles.append(tokens[i + 1])
            i += 2
            continue
        if lower.startswith("--profile="):
            profiles.append(token.split("=", 1)[1])
            i += 1
            continue
        if lower == "--project-directory" and i + 1 < len(tokens):
            resolved = resolve_inside(root, base, tokens[i + 1])
            if resolved is not None:
                base = resolved
            i += 2
            continue
        if lower.startswith("--project-directory="):
            resolved = resolve_inside(root, base, token.split("=", 1)[1])
            if resolved is not None:
                base = resolved
            i += 1
            continue
        if not token.startswith("-"):
            subcommand = lower
            tail = tokens[i + 1:]
            break
        i += 2 if lower in OPTIONS_WITH_VALUE and i + 1 < len(tokens) else 1

    if compose_file is None:
        for name in COMPOSE_NAMES:
            candidate = base / name
            try:
                if candidate.is_file():
                    compose_file = candidate
                    break
            except OSError:
                continue
    return compose_file, subcommand, tail, profiles


def _service_args(subcommand: str | None, tail: list[str]) -> list[str]:
    if subcommand not in SERVICE_COMMANDS:
        return []
    values: list[str] = []
    i = 0
    while i < len(tail):
        token = tail[i]
        lower = token.lower()
        if token == "--":
            values.extend(tail[i + 1:])
            break
        if token.startswith("-"):
            i += 2 if lower in OPTIONS_WITH_VALUE and i + 1 < len(tail) else 1
            continue
        values.append(token)
        if subcommand in {"run", "exec"}:
            break
        i += 1
    return [value for value in values if value and "=" not in value]


class _LimitedSafeLoader(yaml.SafeLoader):
    def __init__(self, stream: str) -> None:
        super().__init__(stream)
        self._realitylint_aliases = 0

    def compose_node(self, parent: object, index: object) -> object:
        if self.check_event(AliasEvent):
            self._realitylint_aliases += 1
            if self._realitylint_aliases > 64:
                raise ComposerError(None, None, "too many YAML aliases", self.peek_event().start_mark)
        return super().compose_node(parent, index)


def _load_compose(root: Path, path: Path) -> tuple[dict | None, str | None]:
    try:
        resolved = path.resolve(strict=False)
        resolved.relative_to(root.resolve(strict=False))
        path = resolved
        if not path.is_file():
            return None, "file does not exist"
        if path.stat().st_size > 2 * 1024 * 1024:
            return None, "file is larger than 2 MiB"
        data = yaml.load(path.read_text(encoding="utf-8", errors="replace"), Loader=_LimitedSafeLoader)
    except (OSError, RuntimeError, ValueError, yaml.YAMLError) as exc:
        return None, f"cannot parse Compose YAML: {exc.__class__.__name__}"
    if not isinstance(data, dict):
        return None, "top-level Compose document is not a mapping"
    return data, None


def _env_files(service: object) -> list[str]:
    if not isinstance(service, dict):
        return []
    raw = service.get("env_file")
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        result: list[str] = []
        for item in raw:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict) and isinstance(item.get("path"), str):
                result.append(item["path"])
        return result
    return []



def _available_profiles(services: dict) -> set[str]:
    result: set[str] = set()
    for service in services.values():
        if not isinstance(service, dict):
            continue
        raw = service.get("profiles")
        if isinstance(raw, list):
            result.update(str(value) for value in raw if isinstance(value, str))
    return result


def _host_ports(services: dict) -> set[int]:
    result: set[int] = set()
    for service in services.values():
        if not isinstance(service, dict):
            continue
        raw_ports = service.get("ports")
        if not isinstance(raw_ports, list):
            continue
        for item in raw_ports:
            if isinstance(item, int):
                result.add(item)
                continue
            if isinstance(item, dict):
                published = item.get("published")
                if isinstance(published, int):
                    result.add(published)
                elif isinstance(published, str) and published.isdigit():
                    result.add(int(published))
                continue
            if not isinstance(item, str) or "$" in item:
                continue
            # 8080:80, 127.0.0.1:8080:80, [::1]:8080:80
            clean = item.split("/", 1)[0]
            parts = clean.rsplit(":", 2)
            if len(parts) >= 2:
                candidate = parts[-2]
                if candidate.isdigit():
                    result.add(int(candidate))
            elif clean.isdigit():
                result.add(int(clean))
    return result


def _nearby_localhost_ports(text: str, command_line: int, radius: int = 12) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    lines = text.splitlines()
    start = max(0, command_line - radius - 1)
    end = min(len(lines), command_line + radius)
    pattern = re.compile(r"\b(?:localhost|127\.0\.0\.1|0\.0\.0\.0):([0-9]{2,5})\b", re.I)
    for index in range(start, end):
        for match in pattern.finditer(lines[index]):
            port = int(match.group(1))
            if 1 <= port <= 65535:
                result.append((port, index + 1))
    return result


def scan_docker_drift(root: Path, doc_path: Path) -> list[Finding]:
    try:
        text = doc_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    doc_display = display_path(root, doc_path)
    commands = extract_commands(root, doc_path, text, (r"\bdocker\s+compose\b",))
    findings: list[Finding] = []
    checked_env_files: set[tuple[str, str]] = set()

    for command in commands:
        compose_file, subcommand, tail, requested_profiles = _compose_invocation(root, command)
        if compose_file is None:
            findings.append(Finding(
                "RL011", "error", "Documented docker compose command has no Compose file in its working directory.",
                doc_display, command.line,
                suggestion="Add compose.yaml/docker-compose.yml or document the correct -f/--file path.",
            ))
            continue
        compose_display = display_path(root, compose_file)
        data, error = _load_compose(root, compose_file)
        if error:
            findings.append(Finding(
                "RL011", "error", f'Documented Compose file "{compose_display}" cannot be verified: {error}.',
                doc_display, command.line,
                suggestion="Fix the Compose file or update the documented command.",
            ))
            continue
        services_obj = data.get("services") if data else None
        services = services_obj if isinstance(services_obj, dict) else {}
        documented_services = _service_args(subcommand, tail)
        available_profiles = _available_profiles(services)
        for profile in requested_profiles:
            if profile not in available_profiles:
                findings.append(Finding(
                    "RL019", "warning", f'Documented Docker Compose profile "{profile}" is not declared by any service.',
                    doc_display, command.line,
                    evidence=f"Available profiles in {compose_display}: {', '.join(sorted(available_profiles)) or '(none)'}",
                    suggestion="Use a declared profile or update the Compose services.",
                ))

        host_ports = _host_ports(services)
        if host_ports:
            for port, port_line in _nearby_localhost_ports(text, command.line):
                if port not in host_ports:
                    findings.append(Finding(
                        "RL020", "warning", f'Documented localhost port {port} is not published by the referenced Compose model.',
                        doc_display, port_line,
                        evidence=f"Published host ports in {compose_display}: {', '.join(str(value) for value in sorted(host_ports))}",
                        suggestion="Update the documented URL/port or the Compose port mapping.",
                    ))

        for service in documented_services:
            if service not in services:
                evidence = ", ".join(sorted(str(name) for name in services)[:30]) or "(none)"
                findings.append(Finding(
                    "RL012", "error", f'Documented Docker Compose service "{service}" does not exist.',
                    doc_display, command.line,
                    evidence=f"Available services in {compose_display}: {evidence}",
                    suggestion="Use an existing service name or update the Compose file.",
                ))

        for service_name, service_data in services.items():
            for env_file in _env_files(service_data):
                key = (compose_display, env_file)
                if key in checked_env_files:
                    continue
                checked_env_files.add(key)
                resolved = resolve_inside(root, compose_file.parent, env_file)
                if resolved is None:
                    continue
                try:
                    exists = resolved.is_file()
                except OSError:
                    exists = False
                if not exists:
                    findings.append(Finding(
                        "RL013", "error", f'Compose service "{service_name}" references missing env_file "{env_file}".',
                        compose_display, 1,
                        suggestion="Add the env file or correct the env_file path in Compose.",
                    ))
    return findings
