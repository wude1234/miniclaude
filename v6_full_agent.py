#!/usr/bin/env python3
"""
v6_full_agent.py - Mini Claude Code: full interview agent.

This file keeps the v0-v4 teaching style, but adds the engineering details
that are useful for interview discussion:

- MCP client over JSON-RPC stdio
- semantic sideQuery memory recall
- Anthropic streaming content_block_stop early execution
- OpenAI-compatible streaming backend
- four-tier context compression including LLM summary compression
- session persistence, resume, and cost budget controls

It is still a compact learning implementation, not a production sandbox.
"""

from __future__ import annotations

import argparse
import asyncio
import difflib
import fnmatch
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args: Any, **_kwargs: Any) -> bool:
        return False

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None


load_dotenv()


# =============================================================================
# Configuration
# =============================================================================

WORKDIR = Path.cwd()
SKILLS_DIR = WORKDIR / "skills"
STATE_DIR = WORKDIR / ".mini_claude"
CONTEXT_DIR = STATE_DIR / "context"
MEMORY_DIR = STATE_DIR / "memory"
SESSION_DIR = STATE_DIR / "sessions"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
OPENAI_BASE_URL = (
    os.getenv("OPENAI_BASE_URL")
    or os.getenv("DASHSCOPE_BASE_URL")
    or "https://dashscope.aliyuncs.com/compatible-mode/v1"
).rstrip("/")

BACKEND = os.getenv("MINI_CLAUDE_BACKEND", "").strip().lower()
if not BACKEND:
    BACKEND = "openai" if OPENAI_API_KEY else "anthropic"

if BACKEND == "openai":
    MODEL = os.getenv("MODEL_NAME", "qwen-turbo")
else:
    MODEL = os.getenv("MODEL_NAME", "claude-sonnet-4-20250514")

USE_STREAMING = os.getenv("MINI_CLAUDE_STREAM", "1") != "0"
SESSION_ID = os.getenv("MINI_CLAUDE_SESSION", "default")
MAX_COST = float(os.getenv("MINI_CLAUDE_MAX_COST", "0") or 0)
SUMMARY_MODEL = os.getenv("MINI_CLAUDE_SUMMARY_MODEL", MODEL)

MAX_TOOL_RESULT_CHARS = 120_000
LARGE_RESULT_CHARS = 30_000
SOFT_CONTEXT_CHARS = 180_000
HARD_CONTEXT_CHARS = 240_000
KEEP_RECENT_RESULTS = 3
SUMMARY_CONTEXT_CHARS = 300_000

MODEL_PRICES_PER_MTOK = {
    # Approximate/default knobs for budget demos. Override by setting
    # MINI_CLAUDE_INPUT_PER_MTOK and MINI_CLAUDE_OUTPUT_PER_MTOK.
    "qwen-turbo": (0.05, 0.20),
    "qwen-plus": (0.40, 1.20),
    "qwen-max": (2.40, 9.60),
    "claude-sonnet-4-20250514": (3.00, 15.00),
}

INPUT_PRICE_PER_MTOK = float(
    os.getenv("MINI_CLAUDE_INPUT_PER_MTOK", MODEL_PRICES_PER_MTOK.get(MODEL, (0.0, 0.0))[0])
)
OUTPUT_PRICE_PER_MTOK = float(
    os.getenv("MINI_CLAUDE_OUTPUT_PER_MTOK", MODEL_PRICES_PER_MTOK.get(MODEL, (0.0, 0.0))[1])
)

_anthropic_client = None


def get_anthropic_client() -> Any:
    global _anthropic_client
    if _anthropic_client is None:
        if Anthropic is None:
            raise RuntimeError("Please install dependencies: python3 -m pip install anthropic python-dotenv")
        _anthropic_client = (
            Anthropic(api_key=ANTHROPIC_API_KEY, base_url=ANTHROPIC_BASE_URL)
            if ANTHROPIC_BASE_URL
            else Anthropic(api_key=ANTHROPIC_API_KEY)
        )
    return _anthropic_client


# =============================================================================
# Utility helpers
# =============================================================================

def now_ms() -> int:
    return int(time.time() * 1000)


def safe_slug(text: str, max_len: int = 60) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", text.strip()).strip("-")
    return (cleaned or "item")[:max_len]


def head_tail(text: str, limit: int = 12_000) -> str:
    if len(text) <= limit:
        return text
    half = max(1, limit // 2)
    omitted = len(text) - (half * 2)
    return text[:half] + f"\n\n[... {omitted} chars omitted ...]\n\n" + text[-half:]


def json_size(obj: Any) -> int:
    return len(json.dumps(obj, ensure_ascii=False, default=str))


def block_text(block: Any) -> str:
    if isinstance(block, dict):
        return str(block.get("text") or block.get("content") or "")
    return str(getattr(block, "text", ""))


def block_type(block: Any) -> str:
    if isinstance(block, dict):
        return str(block.get("type", ""))
    return str(getattr(block, "type", ""))


# =============================================================================
# Permissions
# =============================================================================

MUTATING_TOOLS = {
    "write_file",
    "edit_file",
    "run_shell",
    "remember",
}

READ_ONLY_TOOLS = {
    "read_file",
    "list_files",
    "grep_search",
    "recall_memory",
    "show_state",
    "Skill",
    "Task",
    "TodoWrite",
    "enter_plan_mode",
}


class PermissionManager:
    """Small permission engine inspired by Claude Code modes."""

    MODES = {"plan", "default", "acceptEdits", "bypassPermissions", "dontAsk"}

    DANGEROUS_PATTERNS = [
        r"\brm\s+-rf\s+/",
        r"\bsudo\b",
        r"\bshutdown\b",
        r"\breboot\b",
        r"\bmkfs\b",
        r"\bdd\s+if=",
        r":\(\)\s*\{",
        r">\s*/dev/sd[a-z]",
        r"\bgit\s+reset\s+--hard\b",
        r"\bgit\s+checkout\s+--\b",
        r"\bchmod\s+777\b",
    ]
    DANGEROUS_PROGRAMS = {"sudo", "shutdown", "reboot", "mkfs", "dd"}

    def __init__(self, mode: str = "default"):
        if mode not in self.MODES:
            raise ValueError(f"Unknown permission mode: {mode}")
        self.mode = mode
        self.allow_rules = self._load_rules("MINI_CLAUDE_ALLOW")
        self.deny_rules = self._load_rules("MINI_CLAUDE_DENY")

    def _load_rules(self, env_name: str) -> List[str]:
        raw = os.getenv(env_name, "")
        return [r.strip() for r in raw.split(",") if r.strip()]

    def set_mode(self, mode: str) -> str:
        if mode not in self.MODES:
            return f"Error: unknown permission mode '{mode}'"
        old = self.mode
        self.mode = mode
        return f"Permission mode changed: {old} -> {mode}"

    def is_dangerous_shell(self, command: str) -> Optional[str]:
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command):
                return pattern

        for segment in self.split_shell_segments(command):
            try:
                tokens = shlex.split(segment)
            except ValueError:
                tokens = segment.split()
            if not tokens:
                continue
            program = Path(tokens[0]).name
            if program in self.DANGEROUS_PROGRAMS:
                return f"dangerous program: {program}"
            if program == "rm" and "-rf" in tokens and any(t in {"/", "/*"} for t in tokens):
                return "rm -rf root"
            if program == "git" and len(tokens) >= 3 and tokens[1:3] == ["reset", "--hard"]:
                return "git reset --hard"
        return None

    def split_shell_segments(self, command: str) -> List[str]:
        """Approximate shell AST by splitting top-level control operators."""
        segments = []
        current = []
        quote = ""
        i = 0
        while i < len(command):
            ch = command[i]
            if quote:
                current.append(ch)
                if ch == quote:
                    quote = ""
                elif ch == "\\" and i + 1 < len(command):
                    i += 1
                    current.append(command[i])
                i += 1
                continue
            if ch in {"'", '"'}:
                quote = ch
                current.append(ch)
                i += 1
                continue
            if command.startswith("&&", i) or command.startswith("||", i):
                segments.append("".join(current).strip())
                current = []
                i += 2
                continue
            if ch in {";", "|"}:
                segments.append("".join(current).strip())
                current = []
                i += 1
                continue
            current.append(ch)
            i += 1
        tail = "".join(current).strip()
        if tail:
            segments.append(tail)
        return [s for s in segments if s]

    def _matches_rule(self, tool: str, args: Dict[str, Any], rules: Iterable[str]) -> bool:
        target = tool + " " + json.dumps(args, ensure_ascii=False, sort_keys=True)
        return any(fnmatch.fnmatch(target, rule) for rule in rules)

    def check(self, tool: str, args: Dict[str, Any]) -> Tuple[bool, str]:
        if self.mode == "bypassPermissions":
            return True, "allowed by bypassPermissions"

        if self._matches_rule(tool, args, self.deny_rules):
            return False, "blocked by MINI_CLAUDE_DENY"
        if self._matches_rule(tool, args, self.allow_rules):
            return True, "allowed by MINI_CLAUDE_ALLOW"

        if self.mode == "plan" and tool in MUTATING_TOOLS:
            return False, "blocked in plan mode"

        if tool == "run_shell":
            command = str(args.get("command", ""))
            bad = self.is_dangerous_shell(command)
            if bad:
                return False, f"dangerous shell pattern blocked: {bad}"
            if self.mode == "dontAsk":
                return False, "run_shell blocked in dontAsk mode"

        if tool in {"write_file", "edit_file"}:
            if self.mode in {"default", "acceptEdits"}:
                return True, f"allowed by {self.mode}"
            if self.mode == "dontAsk":
                return False, "file edits blocked in dontAsk mode"

        return True, "allowed"


# =============================================================================
# Workspace and file safety
# =============================================================================

QUOTE_MAP = str.maketrans({
    "‘": "'",
    "’": "'",
    "′": "'",
    "“": '"',
    "”": '"',
    "″": '"',
})


class Workspace:
    """Path safety, read tracking, and file editing helpers."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.read_file_state: Dict[str, float] = {}

    def safe_path(self, raw: str) -> Path:
        path = (self.root / raw).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError(f"Path escapes workspace: {raw}")
        return path

    def record_read(self, path: Path) -> None:
        if path.exists():
            self.read_file_state[str(path)] = path.stat().st_mtime

    def ensure_can_write_existing(self, path: Path) -> Optional[str]:
        if not path.exists():
            return None

        key = str(path)
        if key not in self.read_file_state:
            return "Error: read-before-edit failed. Read this file before editing it."

        current_mtime = path.stat().st_mtime
        if current_mtime != self.read_file_state[key]:
            return (
                "Error: file changed after last read. Re-read it before editing "
                f"(old mtime={self.read_file_state[key]}, current={current_mtime})."
            )
        return None

    def normalize_quotes(self, text: str) -> str:
        return text.translate(QUOTE_MAP)

    def find_actual_string(self, file_content: str, search_string: str) -> Optional[str]:
        if search_string in file_content:
            return search_string

        normalized_file = self.normalize_quotes(file_content)
        normalized_search = self.normalize_quotes(search_string)
        idx = normalized_file.find(normalized_search)
        if idx == -1:
            return None

        return file_content[idx:idx + len(search_string)]

    def make_diff(self, path: Path, old_content: str, new_content: str) -> str:
        diff = "\n".join(difflib.unified_diff(
            old_content.splitlines(),
            new_content.splitlines(),
            fromfile=str(path),
            tofile=str(path),
            lineterm="",
        ))
        return diff + ("\n" if diff else "")


# =============================================================================
# Todo, skills, and memory
# =============================================================================

class TodoManager:
    def __init__(self):
        self.items: List[Dict[str, str]] = []

    def update(self, items: List[Dict[str, Any]]) -> str:
        validated = []
        in_progress = 0

        for i, item in enumerate(items):
            content = str(item.get("content", "")).strip()
            status = str(item.get("status", "pending")).lower()
            active = str(item.get("activeForm", "")).strip()

            if not content or not active:
                raise ValueError(f"Item {i}: content and activeForm are required")
            if status not in {"pending", "in_progress", "completed"}:
                raise ValueError(f"Item {i}: invalid status '{status}'")
            if status == "in_progress":
                in_progress += 1

            validated.append({"content": content, "status": status, "activeForm": active})

        if len(validated) > 20:
            raise ValueError("Max 20 todos allowed")
        if in_progress > 1:
            raise ValueError("Only one task can be in_progress")

        self.items = validated
        return self.render()

    def render(self) -> str:
        if not self.items:
            return "No todos."

        lines = []
        for item in self.items:
            mark = "[x]" if item["status"] == "completed" else "[>]" if item["status"] == "in_progress" else "[ ]"
            suffix = f" <- {item['activeForm']}" if item["status"] == "in_progress" else ""
            lines.append(f"{mark} {item['content']}{suffix}")

        done = sum(1 for item in self.items if item["status"] == "completed")
        return "\n".join(lines) + f"\n({done}/{len(self.items)} completed)"


class SkillLoader:
    """Load Agent Skills style SKILL.md files."""

    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills: Dict[str, Dict[str, Any]] = {}
        self.load_skills()

    def parse_frontmatter(self, text: str) -> Optional[Tuple[Dict[str, str], str]]:
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
        if not match:
            return None

        frontmatter, body = match.groups()
        metadata: Dict[str, str] = {}
        current_key: Optional[str] = None
        current_lines: List[str] = []

        def flush_block() -> None:
            nonlocal current_key, current_lines
            if current_key is not None:
                metadata[current_key] = "\n".join(line.strip() for line in current_lines).strip()
                current_key = None
                current_lines = []

        for line in frontmatter.splitlines():
            key_match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
            if key_match:
                flush_block()
                key, value = key_match.groups()
                value = value.strip().strip("\"'")
                if value in {"|", ">"}:
                    current_key = key
                    current_lines = []
                else:
                    metadata[key] = value
            elif current_key is not None:
                current_lines.append(line)

        flush_block()
        return metadata, body.strip()

    def parse_skill_md(self, path: Path) -> Optional[Dict[str, Any]]:
        parsed = self.parse_frontmatter(path.read_text())
        if not parsed:
            return None
        metadata, body = parsed
        if "name" not in metadata or "description" not in metadata:
            return None
        return {
            "name": metadata["name"],
            "description": metadata["description"],
            "context": metadata.get("context", "inline"),
            "allowed_tools": metadata.get("allowed-tools", ""),
            "body": body,
            "dir": path.parent,
            "path": path,
        }

    def load_skills(self) -> None:
        if not self.skills_dir.exists():
            return
        for child in sorted(self.skills_dir.iterdir()):
            skill_md = child / "SKILL.md"
            if child.is_dir() and skill_md.exists():
                skill = self.parse_skill_md(skill_md)
                if skill:
                    self.skills[skill["name"]] = skill

    def descriptions(self) -> str:
        if not self.skills:
            return "(no skills available)"
        return "\n".join(f"- {name}: {skill['description']}" for name, skill in self.skills.items())

    def content(self, name: str) -> Optional[str]:
        skill = self.skills.get(name)
        if not skill:
            return None

        content = f"# Skill: {skill['name']}\n\n{skill['body']}"
        resources = []
        for folder in ("scripts", "references", "assets"):
            folder_path = skill["dir"] / folder
            if folder_path.exists():
                files = sorted(p.name for p in folder_path.iterdir())
                if files:
                    resources.append(f"- {folder}/: {', '.join(files)}")
        if resources:
            content += f"\n\nAvailable resources in {skill['dir']}:\n" + "\n".join(resources)
        return content

    def names(self) -> List[str]:
        return sorted(self.skills)


class MemoryStore:
    """Lightweight file memory. Uses keyword scoring instead of semantic sideQuery."""

    KINDS = {"project", "user", "local", "session"}

    def __init__(self, root: Path, project_root: Path):
        project_hash = hashlib.sha1(str(project_root.resolve()).encode()).hexdigest()[:12]
        self.root = root / project_hash
        self.root.mkdir(parents=True, exist_ok=True)

    def remember(self, kind: str, title: str, content: str) -> str:
        if kind not in self.KINDS:
            return f"Error: kind must be one of {', '.join(sorted(self.KINDS))}"
        filename = f"{now_ms()}-{kind}-{safe_slug(title)}.md"
        path = self.root / filename
        path.write_text(
            f"---\nkind: {kind}\ntitle: {title}\ncreated_ms: {now_ms()}\n---\n\n{content}\n"
        )
        return f"Memory saved: {path.relative_to(WORKDIR)}"

    def candidates(self, max_items: int = 200) -> List[Dict[str, str]]:
        rows = []
        for path in sorted(self.root.glob("*.md"), reverse=True)[:max_items]:
            text = path.read_text(errors="ignore")
            title = path.stem
            kind = "unknown"
            for line in text.splitlines()[:10]:
                if line.startswith("title:"):
                    title = line.split(":", 1)[1].strip()
                elif line.startswith("kind:"):
                    kind = line.split(":", 1)[1].strip()
            preview = " ".join(text.splitlines()[-8:])[:500]
            rows.append({"file": path.name, "title": title, "kind": kind, "preview": preview})
        return rows

    def read_files(self, filenames: Iterable[str]) -> List[Tuple[Path, str]]:
        result = []
        for name in filenames:
            path = (self.root / name).resolve()
            if path.is_relative_to(self.root) and path.exists():
                result.append((path, path.read_text(errors="ignore")))
        return result

    def recall(self, query: str, limit: int = 5) -> str:
        words = [w.lower() for w in re.findall(r"[A-Za-z0-9_\u4e00-\u9fff]+", query)]
        scored = []
        for path in self.root.glob("*.md"):
            text = path.read_text(errors="ignore")
            lowered = text.lower()
            score = sum(lowered.count(w) for w in words) if words else 0
            if score > 0 or not words:
                scored.append((score, path, text))

        scored.sort(key=lambda item: (-item[0], item[1].name))
        if not scored:
            return "No relevant memories found."

        parts = []
        for score, path, text in scored[:max(1, min(limit, 10))]:
            parts.append(f"## {path.name} (score={score})\n{head_tail(text, 3000)}")
        return "\n\n".join(parts)


# =============================================================================
# MCP client
# =============================================================================

class McpConnection:
    """Minimal JSON-RPC over stdio MCP connection."""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.process: Optional[asyncio.subprocess.Process] = None
        self.next_id = 1
        self.pending: Dict[int, asyncio.Future] = {}
        self.read_task: Optional[asyncio.Task] = None
        self.tools: List[Dict[str, Any]] = []
        self.error: Optional[str] = None

    async def connect(self, timeout: float = 15.0) -> None:
        command = self.config.get("command")
        if not command:
            raise ValueError(f"MCP server '{self.name}' missing command")

        args = list(self.config.get("args", []))
        env = os.environ.copy()
        env.update({str(k): str(v) for k, v in self.config.get("env", {}).items()})

        self.process = await asyncio.create_subprocess_exec(
            command,
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=WORKDIR,
            env=env,
        )
        self.read_task = asyncio.create_task(self._read_loop())

        await asyncio.wait_for(self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "mini-claude-code-v6", "version": "0.1"},
        }), timeout=timeout)
        await self._send_notification("notifications/initialized", {})
        result = await asyncio.wait_for(self._send_request("tools/list", {}), timeout=timeout)
        self.tools = list(result.get("tools", []))

    async def close(self) -> None:
        if self.read_task:
            self.read_task.cancel()
        if self.process and self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=2)
            except asyncio.TimeoutError:
                self.process.kill()

    async def _send_json(self, payload: Dict[str, Any]) -> None:
        if not self.process or not self.process.stdin:
            raise RuntimeError("MCP process not connected")
        line = json.dumps(payload, ensure_ascii=False) + "\n"
        self.process.stdin.write(line.encode("utf-8"))
        await self.process.stdin.drain()

    async def _send_notification(self, method: str, params: Dict[str, Any]) -> None:
        await self._send_json({"jsonrpc": "2.0", "method": method, "params": params})

    async def _send_request(self, method: str, params: Dict[str, Any]) -> Any:
        req_id = self.next_id
        self.next_id += 1
        loop = asyncio.get_event_loop()
        fut: asyncio.Future = loop.create_future()
        self.pending[req_id] = fut
        await self._send_json({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})
        return await fut

    async def _read_loop(self) -> None:
        assert self.process and self.process.stdout
        while True:
            line = await self.process.stdout.readline()
            if not line:
                error = RuntimeError(f"MCP server '{self.name}' closed stdout")
                for fut in list(self.pending.values()):
                    if not fut.done():
                        fut.set_exception(error)
                self.pending.clear()
                return

            try:
                msg = json.loads(line.decode("utf-8"))
            except json.JSONDecodeError:
                continue

            msg_id = msg.get("id")
            if msg_id is None:
                continue
            fut = self.pending.pop(int(msg_id), None)
            if not fut or fut.done():
                continue
            if "error" in msg:
                fut.set_exception(RuntimeError(json.dumps(msg["error"], ensure_ascii=False)))
            else:
                fut.set_result(msg.get("result"))

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any], timeout: float = 120.0) -> str:
        result = await asyncio.wait_for(
            self._send_request("tools/call", {"name": tool_name, "arguments": arguments}),
            timeout=timeout,
        )
        parts = []
        for item in result.get("content", []):
            if item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            else:
                parts.append(json.dumps(item, ensure_ascii=False))
        return "\n".join(parts) or json.dumps(result, ensure_ascii=False)


class McpManager:
    def __init__(self):
        self.configs = self._load_configs()
        self.connected = False
        self.errors: Dict[str, str] = {}
        self.tools_by_server: Dict[str, List[Dict[str, Any]]] = {}

    def _load_configs(self) -> Dict[str, Dict[str, Any]]:
        merged: Dict[str, Dict[str, Any]] = {}
        paths = [
            Path.home() / ".claude" / "settings.json",
            WORKDIR / ".claude" / "settings.json",
            WORKDIR / ".mcp.json",
        ]
        for path in paths:
            if not path.exists():
                continue
            try:
                data = json.loads(path.read_text())
            except Exception:
                continue
            for name, config in (data.get("mcpServers") or {}).items():
                merged[name] = config
        return merged

    def connect(self) -> None:
        if self.connected:
            return
        if not self.configs:
            self.connected = True
            return
        asyncio.run(self._connect_all())
        self.connected = True

    async def _connect_all(self) -> None:
        for name, config in self.configs.items():
            conn = McpConnection(name, config)
            try:
                await conn.connect(timeout=15.0)
                self.tools_by_server[name] = conn.tools
            except Exception as exc:
                conn.error = str(exc)
                self.errors[name] = str(exc)
            finally:
                await conn.close()

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        self.connect()
        tools = []
        for server_name, server_tools in self.tools_by_server.items():
            for tool in server_tools:
                schema = tool.get("inputSchema") or tool.get("input_schema") or {"type": "object", "properties": {}}
                tools.append({
                    "name": f"mcp__{server_name}__{tool['name']}",
                    "description": f"[MCP:{server_name}] {tool.get('description', '')}",
                    "input_schema": schema,
                })
        return tools

    def is_mcp_tool(self, name: str) -> bool:
        return name.startswith("mcp__")

    def call_tool(self, prefixed_name: str, args: Dict[str, Any]) -> str:
        self.connect()
        parts = prefixed_name.split("__")
        if len(parts) < 3:
            return f"Error: invalid MCP tool name '{prefixed_name}'"
        server_name = parts[1]
        tool_name = "__".join(parts[2:])
        config = self.configs.get(server_name)
        if not config:
            return f"Error: MCP server '{server_name}' not connected"
        return asyncio.run(self._call_tool_once(server_name, config, tool_name, args))

    async def _call_tool_once(self, server_name: str, config: Dict[str, Any], tool_name: str, args: Dict[str, Any]) -> str:
        conn = McpConnection(server_name, config)
        try:
            await conn.connect(timeout=15.0)
            return await conn.call_tool(tool_name, args)
        finally:
            await conn.close()

    def status(self) -> Dict[str, Any]:
        return {
            "configs": sorted(self.configs),
            "connected": sorted(self.tools_by_server),
            "errors": self.errors,
        }


# =============================================================================
# Tools
# =============================================================================

AGENT_TYPES = {
    "explore": {
        "description": "read-only exploration agent for files and code search",
        "tools": ["read_file", "list_files", "grep_search", "recall_memory", "show_state"],
        "prompt": "Explore quickly. Do not modify files. Return concise findings with file paths.",
    },
    "plan": {
        "description": "read-only planning agent for implementation strategy",
        "tools": ["read_file", "list_files", "grep_search", "recall_memory", "show_state"],
        "prompt": "Analyze the codebase and return a numbered implementation plan. Do not modify files.",
    },
    "code": {
        "description": "implementation agent with editing tools, but no recursive Task tool",
        "tools": "*",
        "prompt": "Implement the requested change efficiently. Read files before editing.",
    },
}


def agent_descriptions() -> str:
    return "\n".join(f"- {name}: {cfg['description']}" for name, cfg in AGENT_TYPES.items())


BASE_TOOLS = [
    {
        "name": "run_shell",
        "description": "Run a shell command in the workspace. Dangerous commands are blocked unless bypassed.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": "Read a workspace file and record its mtime for read-before-edit safety.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "limit": {"type": "integer", "description": "Optional max lines"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_files",
        "description": "List files under a directory with depth and glob filtering.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "default": "."},
                "depth": {"type": "integer", "default": 3},
                "pattern": {"type": "string", "default": "*"},
            },
        },
    },
    {
        "name": "grep_search",
        "description": "Search text in workspace files using a regex pattern.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string", "default": "."},
                "include": {"type": "string", "default": "*"},
                "max_results": {"type": "integer", "default": 80},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "write_file",
        "description": "Create or overwrite a file. Existing files require read-before-edit and mtime match.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": "Replace unique old_text with new_text. Supports quote normalization and returns a diff.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_text": {"type": "string"},
                "new_text": {"type": "string"},
            },
            "required": ["path", "old_text", "new_text"],
        },
    },
    {
        "name": "TodoWrite",
        "description": "Update the visible todo list for multi-step tasks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                            "activeForm": {"type": "string"},
                        },
                        "required": ["content", "status", "activeForm"],
                    },
                }
            },
            "required": ["items"],
        },
    },
    {
        "name": "remember",
        "description": "Persist a project/user/local/session memory note.",
        "input_schema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": ["project", "user", "local", "session"]},
                "title": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["kind", "title", "content"],
        },
    },
    {
        "name": "recall_memory",
        "description": "Recall saved memories by keyword score.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 5}},
            "required": ["query"],
        },
    },
    {
        "name": "enter_plan_mode",
        "description": "Switch permission mode to plan. Mutating tools are blocked.",
        "input_schema": {
            "type": "object",
            "properties": {"reason": {"type": "string"}},
        },
    },
    {
        "name": "exit_plan_mode",
        "description": "Leave plan mode and switch back to default mode.",
        "input_schema": {
            "type": "object",
            "properties": {"summary": {"type": "string"}},
        },
    },
    {
        "name": "show_state",
        "description": "Show permission mode, token totals, todos, loaded skills, and tracked reads.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

TASK_TOOL = {
    "name": "Task",
    "description": f"Spawn an isolated subagent.\n\nAgent types:\n{agent_descriptions()}",
    "input_schema": {
        "type": "object",
        "properties": {
            "description": {"type": "string"},
            "prompt": {"type": "string"},
            "agent_type": {"type": "string", "enum": list(AGENT_TYPES)},
        },
        "required": ["description", "prompt", "agent_type"],
    },
}

SKILL_TOOL = {
    "name": "Skill",
    "description": "Load a SKILL.md file into the conversation as on-demand expertise.",
    "input_schema": {
        "type": "object",
        "properties": {"skill": {"type": "string"}},
        "required": ["skill"],
    },
}


def tool_names(tools: List[Dict[str, Any]]) -> List[str]:
    return [tool["name"] for tool in tools]


# =============================================================================
# Agent
# =============================================================================

@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0

    def add_response(self, response: Any) -> None:
        usage = getattr(response, "usage", None)
        if isinstance(usage, TokenUsage):
            self.add(usage)
            return
        self.input_tokens += int(getattr(usage, "input_tokens", 0) or 0)
        self.output_tokens += int(getattr(usage, "output_tokens", 0) or 0)

    def add(self, other: "TokenUsage") -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens


@dataclass
class ModelResult:
    content: List[Dict[str, Any]]
    stop_reason: str
    usage: TokenUsage


class AnthropicStreamAssembler:
    """Assemble Anthropic stream events and fire when a tool block is complete."""

    def __init__(self, on_tool_ready: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.on_tool_ready = on_tool_ready
        self.response_text: List[str] = []
        self.content: List[Dict[str, Any]] = []
        self.tool_blocks: Dict[int, Dict[str, Any]] = {}
        self.usage = TokenUsage()
        self.stop_reason = "end_turn"
        self.tool_ready_order: List[str] = []

    def handle_event(self, event: Any) -> None:
        typ = getattr(event, "type", "")
        if typ == "message_delta":
            delta = getattr(event, "delta", None)
            self.stop_reason = getattr(delta, "stop_reason", None) or self.stop_reason
            ev_usage = getattr(event, "usage", None)
            self.usage.output_tokens += int(getattr(ev_usage, "output_tokens", 0) or 0)
            return

        if typ == "content_block_start":
            block = getattr(event, "content_block", None)
            idx = int(getattr(event, "index", 0))
            if getattr(block, "type", "") == "tool_use":
                self.tool_blocks[idx] = {
                    "type": "tool_use",
                    "id": getattr(block, "id", ""),
                    "name": getattr(block, "name", ""),
                    "input_json": "",
                }
            return

        if typ == "content_block_delta":
            delta = getattr(event, "delta", None)
            idx = int(getattr(event, "index", 0))
            if hasattr(delta, "text"):
                self.response_text.append(delta.text)
            elif hasattr(delta, "partial_json") and idx in self.tool_blocks:
                self.tool_blocks[idx]["input_json"] += delta.partial_json
            return

        if typ == "content_block_stop":
            idx = int(getattr(event, "index", 0))
            if idx not in self.tool_blocks:
                return
            block = self.tool_blocks.pop(idx)
            try:
                parsed = json.loads(block["input_json"] or "{}")
            except json.JSONDecodeError:
                parsed = {"_raw_arguments": block["input_json"]}
            ready = {
                "type": "tool_use",
                "id": block["id"],
                "name": block["name"],
                "input": parsed,
            }
            self.content.append(ready)
            self.tool_ready_order.append(block["id"])
            if self.on_tool_ready:
                self.on_tool_ready(ready)

    def finish(self, final_message: Any = None) -> ModelResult:
        if final_message is not None:
            final_usage = getattr(final_message, "usage", None)
            self.usage.input_tokens += int(getattr(final_usage, "input_tokens", 0) or 0)
            self.usage.output_tokens = max(
                self.usage.output_tokens,
                int(getattr(final_usage, "output_tokens", 0) or 0),
            )
            self.stop_reason = getattr(final_message, "stop_reason", self.stop_reason)

        text = "".join(self.response_text)
        content = list(self.content)
        if text:
            content.insert(0, {"type": "text", "text": text})
        return ModelResult(content=content, stop_reason=self.stop_reason, usage=self.usage)


class Agent:
    def __init__(
        self,
        workdir: Path,
        permission_mode: str = "default",
        is_sub_agent: bool = False,
        agent_type: str = "main",
        custom_prompt: Optional[str] = None,
        allowed_tool_names: Optional[List[str]] = None,
    ):
        self.workdir = workdir.resolve()
        self.workspace = Workspace(self.workdir)
        self.permissions = PermissionManager(permission_mode)
        self.todos = TodoManager()
        self.skills = SkillLoader(SKILLS_DIR)
        self.memory = MemoryStore(MEMORY_DIR, self.workdir)
        self.mcp = McpManager()
        self.messages: List[Dict[str, Any]] = []
        self.usage = TokenUsage()
        self.is_sub_agent = is_sub_agent
        self.agent_type = agent_type
        self.loaded_skills: List[str] = []
        self.context_counter = 0

        mcp_tools = [] if is_sub_agent else self.mcp.get_tool_definitions()
        all_tools = BASE_TOOLS + [TASK_TOOL, SKILL_TOOL] + mcp_tools
        if is_sub_agent:
            # Subagents cannot spawn more subagents in this compact demo.
            all_tools = BASE_TOOLS + [SKILL_TOOL]

        if allowed_tool_names is not None:
            self.tools = [tool for tool in all_tools if tool["name"] in allowed_tool_names]
        else:
            self.tools = all_tools

        self.system = custom_prompt or self.default_system()

    def default_system(self) -> str:
        return f"""You are Mini Claude Code v6 at {self.workdir}.

Loop: plan -> inspect -> act with tools -> verify -> summarize.

Interview-enhanced mechanisms available:
- read-before-edit and mtime checks protect files from stale edits
- edit_file performs quote normalization, uniqueness checks, and returns unified diff
- permission modes are plan/default/acceptEdits/bypassPermissions/dontAsk
- large or stale tool results may be compressed before API calls
- subagents run with isolated context and return concise summaries
- skills are loaded on demand from SKILL.md
- lightweight memories are stored under .mini_claude/memory

Skills available:
{self.skills.descriptions()}

Subagents available:
{agent_descriptions()}

Rules:
- Use TodoWrite for multi-step work.
- Read files before editing them.
- Use Task for broad exploration or isolated implementation.
- Use Skill immediately when a task matches a skill description.
- Prefer precise, minimal edits and verify with commands when useful.
- After finishing, summarize changes and mention any limits."""

    def allowed_tools_for_agent_type(self, agent_type: str) -> Optional[List[str]]:
        config = AGENT_TYPES.get(agent_type, AGENT_TYPES["explore"])
        allowed = config["tools"]
        if allowed == "*":
            return [tool["name"] for tool in BASE_TOOLS + [SKILL_TOOL]]
        return list(allowed) + ["Skill"]

    def estimated_cost(self) -> float:
        return (
            (self.usage.input_tokens / 1_000_000) * INPUT_PRICE_PER_MTOK
            + (self.usage.output_tokens / 1_000_000) * OUTPUT_PRICE_PER_MTOK
        )

    def budget_exceeded(self) -> bool:
        return MAX_COST > 0 and self.estimated_cost() >= MAX_COST

    def session_path(self, session_id: str = SESSION_ID) -> Path:
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        return SESSION_DIR / f"{safe_slug(session_id)}.json"

    def save_session(self, session_id: str = SESSION_ID) -> str:
        path = self.session_path(session_id)
        payload = {
            "session_id": session_id,
            "backend": BACKEND,
            "model": MODEL,
            "messages": self.messages,
            "usage": {
                "input_tokens": self.usage.input_tokens,
                "output_tokens": self.usage.output_tokens,
            },
            "todos": self.todos.items,
            "loaded_skills": self.loaded_skills,
            "read_file_state": self.workspace.read_file_state,
            "permission_mode": self.permissions.mode,
            "saved_at": time.time(),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        return str(path)

    def load_session(self, session_id: str = SESSION_ID) -> str:
        path = self.session_path(session_id)
        if not path.exists():
            return f"No session found at {path}"
        payload = json.loads(path.read_text())
        self.messages = payload.get("messages", [])
        usage = payload.get("usage", {})
        self.usage = TokenUsage(int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0)))
        self.todos.items = payload.get("todos", [])
        self.loaded_skills = payload.get("loaded_skills", [])
        self.workspace.read_file_state = {str(k): float(v) for k, v in payload.get("read_file_state", {}).items()}
        self.permissions.mode = payload.get("permission_mode", self.permissions.mode)
        return f"Loaded session {session_id} from {path}"

    def compress_messages(self) -> Optional[str]:
        """A compact four-ish tier compression inspired by the interview material."""
        size_before = json_size(self.messages)
        has_large_result = any(
            isinstance(msg.get("content"), list)
            and any(
                isinstance(block, dict)
                and block.get("type") == "tool_result"
                and len(str(block.get("content", ""))) > LARGE_RESULT_CHARS
                and not str(block.get("content", "")).startswith("<large-result")
                for block in msg.get("content", [])
            )
            for msg in self.messages
        )
        if size_before < SOFT_CONTEXT_CHARS and not has_large_result:
            return None

        CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
        changed = False

        # Tier 1/3: move large tool results to disk and keep preview plus path.
        for msg in self.messages:
            content = msg.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                text = str(block.get("content", ""))
                if len(text) <= LARGE_RESULT_CHARS or text.startswith("<large-result"):
                    continue

                self.context_counter += 1
                path = CONTEXT_DIR / f"tool_result_{now_ms()}_{self.context_counter}.txt"
                path.write_text(text)
                block["content"] = (
                    f"<large-result saved_to=\"{path.relative_to(WORKDIR)}\" "
                    f"original_chars=\"{len(text)}\">\n"
                    f"{head_tail(text, 12_000)}\n</large-result>"
                )
                changed = True

        size_mid = json_size(self.messages)
        if size_mid < HARD_CONTEXT_CHARS:
            if changed:
                return f"Compressed large tool results: {size_before} -> {size_mid} chars"
            return None

        # Tier 2: snip stale tool results, keeping the latest few intact.
        seen = 0
        for msg in reversed(self.messages):
            content = msg.get("content")
            if not isinstance(content, list):
                continue
            for block in reversed(content):
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                seen += 1
                if seen <= KEEP_RECENT_RESULTS:
                    continue
                text = str(block.get("content", ""))
                if len(text) > 800:
                    block["content"] = f"<snipped stale tool result; original_chars={len(text)} />"
                    changed = True

        size_after = json_size(self.messages)
        if changed:
            if size_after > SUMMARY_CONTEXT_CHARS:
                summary_note = self.summarize_old_messages()
                return f"Compressed messages: {size_before} -> {json_size(self.messages)} chars; {summary_note}"
            return f"Compressed messages: {size_before} -> {size_after} chars"
        if size_after > SUMMARY_CONTEXT_CHARS:
            summary_note = self.summarize_old_messages()
            return f"Summarized old messages: {size_before} -> {json_size(self.messages)} chars; {summary_note}"
        return None

    def summarize_old_messages(self) -> str:
        if len(self.messages) < 8:
            return "not enough messages to summarize"

        keep = self.messages[-6:]
        old = self.messages[:-6]
        source = json.dumps(old, ensure_ascii=False)[:180_000]
        prompt = f"""Summarize this coding-agent conversation history for continuation.

Keep:
- user goal and constraints
- files read/edited and important diffs
- tool results that affect future decisions
- current plan/progress
- errors and unresolved risks

Return a concise but specific summary.

History JSON:
{source}
"""
        try:
            if BACKEND == "openai":
                summary = self.side_query(
                    "Return JSON as {\"summary\": \"...\"}. The summary string can contain newlines.\n\n" + prompt
                )
                match = re.search(r"\{.*\}", summary, re.DOTALL)
                parsed = json.loads(match.group(0) if match else summary)
                text = str(parsed.get("summary", summary))
            else:
                response = get_anthropic_client().messages.create(
                    model=SUMMARY_MODEL,
                    system="Summarize old agent context for continuation.",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2000,
                )
                text = "".join(block_text(block) for block in response.content)
        except Exception as exc:
            text = f"Automatic summary failed: {exc}. Old message count was {len(old)}."

        self.messages = [
            {"role": "user", "content": "<context-summary-request>Continue from this compressed context.</context-summary-request>"},
            {"role": "assistant", "content": [{"type": "text", "text": "<context-summary>\n" + text + "\n</context-summary>"}]},
        ] + keep
        return f"summarized {len(old)} old messages"

    def call_model(self) -> Any:
        note = self.compress_messages()
        if note and not self.is_sub_agent:
            print(f"[compression] {note}")
        if BACKEND == "openai":
            return self.call_openai_compatible_stream() if USE_STREAMING else self.call_openai_compatible()
        if USE_STREAMING:
            return self.call_anthropic_stream()
        return get_anthropic_client().messages.create(
            model=MODEL,
            system=self.system,
            messages=self.messages,
            tools=self.tools,
            max_tokens=8000,
        )

    def call_anthropic_stream(self) -> ModelResult:
        ready_ids: List[str] = []
        assembler = AnthropicStreamAssembler(on_tool_ready=lambda tool: ready_ids.append(tool["id"]))

        with get_anthropic_client().messages.stream(
            model=MODEL,
            system=self.system,
            messages=self.messages,
            tools=self.tools,
            max_tokens=8000,
        ) as stream:
            for event in stream:
                assembler.handle_event(event)
            return assembler.finish(stream.get_final_message())

    def anthropic_to_openai_messages(self) -> List[Dict[str, Any]]:
        messages: List[Dict[str, Any]] = [{"role": "system", "content": self.system}]

        for msg in self.messages:
            role = msg["role"]
            content = msg.get("content")

            if role == "assistant" and isinstance(content, list):
                text_parts = []
                tool_calls = []
                for block in content:
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_use":
                        tool_calls.append({
                            "id": block["id"],
                            "type": "function",
                            "function": {
                                "name": block["name"],
                                "arguments": json.dumps(block.get("input", {}), ensure_ascii=False),
                            },
                        })
                converted: Dict[str, Any] = {"role": "assistant", "content": "\n".join(text_parts) or None}
                if tool_calls:
                    converted["tool_calls"] = tool_calls
                messages.append(converted)
                continue

            if role == "user" and isinstance(content, list):
                text_parts = []
                for block in content:
                    if block.get("type") == "tool_result":
                        messages.append({
                            "role": "tool",
                            "tool_call_id": block["tool_use_id"],
                            "content": str(block.get("content", "")),
                        })
                    elif block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                if text_parts:
                    messages.append({"role": "user", "content": "\n".join(text_parts)})
                continue

            if isinstance(content, str):
                messages.append({"role": role, "content": content})
            else:
                messages.append({"role": role, "content": str(content)})

        return messages

    def openai_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {"type": "object", "properties": {}}),
                },
            }
            for tool in self.tools
        ]

    def call_openai_compatible(self) -> ModelResult:
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY or DASHSCOPE_API_KEY is required for openai backend")

        payload = {
            "model": MODEL,
            "messages": self.anthropic_to_openai_messages(),
            "tools": self.openai_tools(),
            "tool_choice": "auto",
            "max_tokens": 8000,
        }
        req = urllib.request.Request(
            OPENAI_BASE_URL + "/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI-compatible API error {exc.code}: {body}") from exc

        obj = json.loads(raw)
        choice = obj["choices"][0]
        msg = choice.get("message", {})
        content: List[Dict[str, Any]] = []

        if msg.get("content"):
            content.append({"type": "text", "text": msg["content"]})

        for call in msg.get("tool_calls") or []:
            raw_args = call.get("function", {}).get("arguments") or "{}"
            try:
                parsed_args = json.loads(raw_args)
            except json.JSONDecodeError:
                parsed_args = {"_raw_arguments": raw_args}
            content.append({
                "type": "tool_use",
                "id": call["id"],
                "name": call.get("function", {}).get("name", ""),
                "input": parsed_args,
            })

        usage = obj.get("usage") or {}
        token_usage = TokenUsage(
            input_tokens=int(usage.get("prompt_tokens", 0) or 0),
            output_tokens=int(usage.get("completion_tokens", 0) or 0),
        )
        finish_reason = choice.get("finish_reason") or ""
        stop_reason = "tool_use" if msg.get("tool_calls") else finish_reason
        return ModelResult(content=content, stop_reason=stop_reason, usage=token_usage)

    def call_openai_compatible_stream(self) -> ModelResult:
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY or DASHSCOPE_API_KEY is required for openai backend")

        payload = {
            "model": MODEL,
            "messages": self.anthropic_to_openai_messages(),
            "tools": self.openai_tools(),
            "tool_choice": "auto",
            "max_tokens": 8000,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        req = urllib.request.Request(
            OPENAI_BASE_URL + "/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
            method="POST",
        )

        text_parts: List[str] = []
        tool_calls: Dict[int, Dict[str, Any]] = {}
        usage = TokenUsage()
        finish_reason = ""

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    obj = json.loads(data)
                    if obj.get("usage"):
                        usage = TokenUsage(
                            input_tokens=int(obj["usage"].get("prompt_tokens", 0) or 0),
                            output_tokens=int(obj["usage"].get("completion_tokens", 0) or 0),
                        )
                    for choice in obj.get("choices", []):
                        finish_reason = choice.get("finish_reason") or finish_reason
                        delta = choice.get("delta", {})
                        if delta.get("content"):
                            text_parts.append(delta["content"])
                        for call_delta in delta.get("tool_calls") or []:
                            idx = int(call_delta.get("index", 0))
                            entry = tool_calls.setdefault(idx, {"id": "", "name": "", "arguments": ""})
                            if call_delta.get("id"):
                                entry["id"] = call_delta["id"]
                            fn = call_delta.get("function") or {}
                            if fn.get("name"):
                                entry["name"] += fn["name"]
                            if fn.get("arguments"):
                                entry["arguments"] += fn["arguments"]
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI-compatible API error {exc.code}: {body}") from exc

        content: List[Dict[str, Any]] = []
        text = "".join(text_parts)
        if text:
            content.append({"type": "text", "text": text})

        for idx in sorted(tool_calls):
            call = tool_calls[idx]
            try:
                parsed_args = json.loads(call["arguments"] or "{}")
            except json.JSONDecodeError:
                parsed_args = {"_raw_arguments": call["arguments"]}
            content.append({
                "type": "tool_use",
                "id": call["id"] or f"call_{idx}_{now_ms()}",
                "name": call["name"],
                "input": parsed_args,
            })

        stop_reason = "tool_use" if tool_calls else finish_reason
        return ModelResult(content=content, stop_reason=stop_reason, usage=usage)

    def response_to_message_and_calls(self, response: Any) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], str]:
        assistant_content = []
        tool_calls = []
        text_parts = []

        for block in response.content:
            typ = block_type(block)
            if hasattr(block, "text") or typ == "text":
                text = block_text(block)
                assistant_content.append({"type": "text", "text": text})
                text_parts.append(text)
            elif typ == "tool_use":
                call = {
                    "type": "tool_use",
                    "id": getattr(block, "id", block.get("id") if isinstance(block, dict) else ""),
                    "name": getattr(block, "name", block.get("name") if isinstance(block, dict) else ""),
                    "input": getattr(block, "input", block.get("input") if isinstance(block, dict) else {}),
                }
                assistant_content.append(call)
                tool_calls.append(call)

        return assistant_content, tool_calls, "".join(text_parts)

    def run_once(self, prompt: str, max_turns: int = 40) -> Dict[str, Any]:
        self.messages.append({"role": "user", "content": prompt})
        final_text = ""
        printed_text = False

        for _ in range(max_turns):
            if self.budget_exceeded():
                final_text = f"Stopped: cost budget exceeded (${self.estimated_cost():.6f} >= ${MAX_COST:.6f})."
                break

            response = self.call_model()
            self.usage.add_response(response)
            assistant_content, tool_calls, text = self.response_to_message_and_calls(response)

            if text and not self.is_sub_agent:
                print(text)
                printed_text = True

            self.messages.append({"role": "assistant", "content": assistant_content})

            if not tool_calls:
                final_text = text
                break

            results = []
            for call in tool_calls:
                name = call["name"]
                args = call.get("input") or {}
                if not self.is_sub_agent:
                    display = args if len(str(args)) < 500 else str(args)[:500] + "..."
                    print(f"\n> {name}: {display}")

                output = self.execute_tool(name, args)
                output = output[:MAX_TOOL_RESULT_CHARS]

                if not self.is_sub_agent and name not in {"Task", "Skill"}:
                    print("  " + head_tail(output, 600).replace("\n", "\n  "))
                elif not self.is_sub_agent and name == "Skill":
                    print(f"  Loaded skill content ({len(output)} chars)")

                results.append({
                    "type": "tool_result",
                    "tool_use_id": call["id"],
                    "content": f"[{name}]\n{output}",
                })

            self.messages.append({"role": "user", "content": results})
        else:
            final_text = "Stopped: max agent turns reached."

        if not self.is_sub_agent:
            self.save_session()
        return {"text": final_text, "tokens": self.usage, "printed": printed_text}

    def execute_tool(self, name: str, args: Dict[str, Any]) -> str:
        if self.mcp.is_mcp_tool(name):
            return self.mcp.call_tool(name, args)

        ok, reason = self.permissions.check(name, args)
        if not ok:
            return f"Permission denied: {reason}"

        try:
            if name == "run_shell":
                return self.tool_run_shell(str(args["command"]))
            if name == "read_file":
                return self.tool_read_file(str(args["path"]), args.get("limit"))
            if name == "list_files":
                return self.tool_list_files(str(args.get("path", ".")), int(args.get("depth", 3)), str(args.get("pattern", "*")))
            if name == "grep_search":
                return self.tool_grep_search(
                    str(args["pattern"]),
                    str(args.get("path", ".")),
                    str(args.get("include", "*")),
                    int(args.get("max_results", 80)),
                )
            if name == "write_file":
                return self.tool_write_file(str(args["path"]), str(args["content"]))
            if name == "edit_file":
                return self.tool_edit_file(str(args["path"]), str(args["old_text"]), str(args["new_text"]))
            if name == "TodoWrite":
                return self.todos.update(args["items"])
            if name == "Task":
                return self.tool_task(str(args["description"]), str(args["prompt"]), str(args["agent_type"]))
            if name == "Skill":
                return self.tool_skill(str(args["skill"]))
            if name == "remember":
                return self.memory.remember(str(args["kind"]), str(args["title"]), str(args["content"]))
            if name == "recall_memory":
                return self.semantic_recall(str(args["query"]), int(args.get("limit", 5)))
            if name == "enter_plan_mode":
                return self.permissions.set_mode("plan")
            if name == "exit_plan_mode":
                return self.permissions.set_mode("default")
            if name == "show_state":
                return self.tool_show_state()
        except Exception as exc:
            return f"Error: {exc}"

        return f"Unknown tool: {name}"

    def side_query(self, prompt: str) -> str:
        """Small non-streaming LLM call used for semantic memory selection."""
        if BACKEND == "openai":
            if not OPENAI_API_KEY:
                raise RuntimeError("OPENAI_API_KEY or DASHSCOPE_API_KEY is required for sideQuery")
            payload = {
                "model": SUMMARY_MODEL,
                "messages": [
                    {"role": "system", "content": "Return only valid JSON. No prose."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0,
            }
            req = urllib.request.Request(
                OPENAI_BASE_URL + "/chat/completions",
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                obj = json.loads(resp.read().decode("utf-8"))
            return obj["choices"][0]["message"].get("content", "")

        response = get_anthropic_client().messages.create(
            model=SUMMARY_MODEL,
            system="Return only valid JSON. No prose.",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
        )
        return "".join(block_text(block) for block in response.content)

    def semantic_recall(self, query: str, limit: int = 5) -> str:
        candidates = self.memory.candidates()
        if not candidates:
            return "No memories stored."

        prompt = (
            "Select the memory filenames most relevant to the query. "
            "Return JSON as {\"files\": [\"filename.md\"]}.\n\n"
            f"Query: {query}\n\nCandidates:\n"
            + json.dumps(candidates, ensure_ascii=False, indent=2)
        )
        try:
            raw = self.side_query(prompt)
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            selected = json.loads(match.group(0) if match else raw).get("files", [])
            selected = [str(item) for item in selected][:max(1, min(limit, 10))]
            files = self.memory.read_files(selected)
            if files:
                return "\n\n".join(f"## {path.name}\n{head_tail(text, 5000)}" for path, text in files)
        except Exception as exc:
            fallback = self.memory.recall(query, limit)
            return f"<sideQuery failed: {exc}; using keyword fallback>\n\n{fallback}"

        return self.memory.recall(query, limit)

    def tool_run_shell(self, command: str) -> str:
        result = subprocess.run(
            command,
            shell=True,
            cwd=self.workdir,
            capture_output=True,
            text=True,
            timeout=90,
        )
        output = (result.stdout + result.stderr).strip()
        header = f"exit_code={result.returncode}"
        return header + "\n" + (output or "(no output)")

    def tool_read_file(self, path: str, limit: Optional[int]) -> str:
        fp = self.workspace.safe_path(path)
        text = fp.read_text(errors="ignore")
        self.workspace.record_read(fp)
        lines = text.splitlines()
        if limit and limit > 0 and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(text.splitlines()) - limit} more lines)"]
        return "\n".join(lines)

    def tool_list_files(self, path: str, depth: int, pattern: str) -> str:
        base = self.workspace.safe_path(path)
        if not base.exists():
            return f"Error: path not found: {path}"
        if base.is_file():
            return str(base.relative_to(self.workdir))

        ignored = {".git", "__pycache__", ".venv", "venv", "node_modules", ".mini_claude"}
        rows = []
        base_depth = len(base.relative_to(self.workdir).parts) if base != self.workdir else 0
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in ignored]
            root_path = Path(root)
            rel_depth = len(root_path.relative_to(self.workdir).parts) - base_depth
            if rel_depth >= max(0, depth):
                dirs[:] = []
            for filename in files:
                rel = (root_path / filename).relative_to(self.workdir)
                if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(str(rel), pattern):
                    rows.append(str(rel))
                if len(rows) >= 500:
                    rows.append("... (truncated at 500 files)")
                    return "\n".join(rows)
        return "\n".join(sorted(rows)) or "(no files)"

    def tool_grep_search(self, pattern: str, path: str, include: str, max_results: int) -> str:
        base = self.workspace.safe_path(path)
        regex = re.compile(pattern)
        files = [base] if base.is_file() else [p for p in base.rglob("*") if p.is_file()]
        rows = []
        for fp in files:
            rel = fp.relative_to(self.workdir)
            if any(part in {".git", "__pycache__", ".mini_claude"} for part in rel.parts):
                continue
            if not fnmatch.fnmatch(fp.name, include) and not fnmatch.fnmatch(str(rel), include):
                continue
            try:
                for i, line in enumerate(fp.read_text(errors="ignore").splitlines(), start=1):
                    if regex.search(line):
                        rows.append(f"{rel}:{i}: {line[:300]}")
                        if len(rows) >= max_results:
                            return "\n".join(rows) + "\n... (truncated)"
            except UnicodeDecodeError:
                continue
        return "\n".join(rows) or "(no matches)"

    def tool_write_file(self, path: str, content: str) -> str:
        fp = self.workspace.safe_path(path)
        old_content = fp.read_text(errors="ignore") if fp.exists() else ""
        problem = self.workspace.ensure_can_write_existing(fp)
        if problem:
            return problem

        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        self.workspace.record_read(fp)

        if old_content:
            diff = self.workspace.make_diff(fp, old_content, content)
            return f"Wrote {len(content)} bytes to {path}\n\nDiff:\n{diff}"
        return f"Created {path} ({len(content)} bytes)"

    def tool_edit_file(self, path: str, old_text: str, new_text: str) -> str:
        fp = self.workspace.safe_path(path)
        problem = self.workspace.ensure_can_write_existing(fp)
        if problem:
            return problem

        content = fp.read_text(errors="ignore")
        actual = self.workspace.find_actual_string(content, old_text)
        if actual is None:
            return "Error: old_text not found, even after quote normalization."

        normalized_content = self.workspace.normalize_quotes(content)
        normalized_actual = self.workspace.normalize_quotes(actual)
        count = normalized_content.count(normalized_actual)
        if count > 1:
            return f"Error: old_text found {count} times. Include more surrounding context so it is unique."

        new_content = content.replace(actual, new_text, 1)
        diff = self.workspace.make_diff(fp, content, new_content)
        fp.write_text(new_content)
        self.workspace.record_read(fp)
        return f"Edited {path}\n\nDiff:\n{diff}"

    def tool_skill(self, skill_name: str) -> str:
        content = self.skills.content(skill_name)
        if content is None:
            return f"Error: unknown skill '{skill_name}'. Available: {', '.join(self.skills.names()) or 'none'}"
        if skill_name not in self.loaded_skills:
            self.loaded_skills.append(skill_name)
        return f"<skill-loaded name=\"{skill_name}\">\n{content}\n</skill-loaded>"

    def tool_task(self, description: str, prompt: str, agent_type: str) -> str:
        if agent_type not in AGENT_TYPES:
            return f"Error: unknown agent_type '{agent_type}'"

        config = AGENT_TYPES[agent_type]
        allowed = self.allowed_tools_for_agent_type(agent_type)
        sub_prompt = f"""You are a {agent_type} subagent at {self.workdir}.

{config['prompt']}

Return only the final concise result for the parent agent."""

        sub = Agent(
            self.workdir,
            permission_mode="bypassPermissions",
            is_sub_agent=True,
            agent_type=agent_type,
            custom_prompt=sub_prompt,
            allowed_tool_names=allowed,
        )

        if not self.is_sub_agent:
            print(f"  [{agent_type}] {description}")
        started = time.time()
        result = sub.run_once(prompt, max_turns=25)
        self.usage.add(result["tokens"])
        elapsed = time.time() - started
        if not self.is_sub_agent:
            print(f"  [{agent_type}] done in {elapsed:.1f}s, tokens +{result['tokens'].input_tokens}/{result['tokens'].output_tokens}")
        return result["text"] or "(subagent produced no final text)"

    def tool_show_state(self) -> str:
        state = {
            "backend": BACKEND,
            "model": MODEL,
            "base_url": OPENAI_BASE_URL if BACKEND == "openai" else ANTHROPIC_BASE_URL,
            "streaming": USE_STREAMING,
            "session": SESSION_ID,
            "permission_mode": self.permissions.mode,
            "tools": tool_names(self.tools),
            "loaded_skills": self.loaded_skills,
            "tracked_reads": sorted(str(Path(p).relative_to(self.workdir)) for p in self.workspace.read_file_state),
            "todos": self.todos.items,
            "mcp": self.mcp.status(),
            "tokens": {
                "input": self.usage.input_tokens,
                "output": self.usage.output_tokens,
                "estimated_cost_usd": round(self.estimated_cost(), 6),
                "max_cost_usd": MAX_COST,
            },
        }
        return json.dumps(state, indent=2, ensure_ascii=False)


# =============================================================================
# CLI
# =============================================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mini Claude Code v6 full interview agent")
    parser.add_argument("prompt", nargs="?", help="Run one prompt and exit")
    parser.add_argument(
        "--permission-mode",
        default=os.getenv("MINI_CLAUDE_PERMISSION_MODE", "default"),
        choices=sorted(PermissionManager.MODES),
        help="Permission mode",
    )
    parser.add_argument("--session", default=SESSION_ID, help="Session id for save/resume")
    parser.add_argument("--resume", action="store_true", help="Resume session before running")
    parser.add_argument("--max-cost", type=float, default=MAX_COST, help="Stop when estimated cost reaches this USD budget")
    parser.add_argument("--no-stream", action="store_true", help="Disable streaming API calls")
    return parser


def main() -> None:
    global SESSION_ID, MAX_COST, USE_STREAMING
    args = build_parser().parse_args()
    SESSION_ID = args.session
    MAX_COST = args.max_cost
    if args.no_stream:
        USE_STREAMING = False

    agent = Agent(WORKDIR, permission_mode=args.permission_mode)
    if args.resume:
        print(agent.load_session(args.session))

    print(f"Mini Claude Code v6 - {WORKDIR}")
    print(f"Backend: {BACKEND}")
    print(f"Model: {MODEL}")
    print(f"Streaming: {USE_STREAMING}")
    if BACKEND == "openai":
        print(f"Base URL: {OPENAI_BASE_URL}")
    print(f"Session: {SESSION_ID}")
    if MAX_COST:
        print(f"Max cost: ${MAX_COST:.6f}")
    print(f"Permission mode: {agent.permissions.mode}")
    print(f"Skills: {', '.join(agent.skills.names()) or 'none'}")
    print("Type 'exit' to quit.\n")

    if args.prompt:
        result = agent.run_once(args.prompt)
        if result["text"] and not result.get("printed"):
            print(result["text"])
        return

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input or user_input.lower() in {"exit", "quit", "q"}:
            break

        result = agent.run_once(user_input)
        if result["text"] and not result.get("printed"):
            print(result["text"])
        print()


if __name__ == "__main__":
    main()
