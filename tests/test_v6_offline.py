import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import v6_full_agent as v6


ROOT = Path(__file__).resolve().parents[1]


def ns(**kwargs):
    return SimpleNamespace(**kwargs)


def test_anthropic_stream_content_block_stop_marks_tool_ready():
    ready = []
    assembler = v6.AnthropicStreamAssembler(on_tool_ready=lambda tool: ready.append(tool))

    assembler.handle_event(ns(
        type="content_block_start",
        index=0,
        content_block=ns(type="tool_use", id="toolu_1", name="read_file"),
    ))
    assembler.handle_event(ns(
        type="content_block_delta",
        index=0,
        delta=ns(partial_json='{"path": "READ'),
    ))
    assert ready == []

    assembler.handle_event(ns(
        type="content_block_delta",
        index=0,
        delta=ns(partial_json='ME.md"}'),
    ))
    assert ready == []

    assembler.handle_event(ns(type="content_block_stop", index=0))
    assert ready == [{
        "type": "tool_use",
        "id": "toolu_1",
        "name": "read_file",
        "input": {"path": "README.md"},
    }]

    result = assembler.finish(ns(usage=ns(input_tokens=10, output_tokens=5), stop_reason="tool_use"))
    assert result.stop_reason == "tool_use"
    assert result.usage.input_tokens == 10
    assert result.content[0]["name"] == "read_file"


def test_mcp_discovery_and_call(tmp_path):
    server = tmp_path / "echo_mcp.py"
    server.write_text(r'''
import json, sys
for line in sys.stdin:
    msg = json.loads(line)
    mid = msg.get("id")
    method = msg.get("method")
    if mid is None:
        continue
    if method == "initialize":
        result = {"protocolVersion": "2024-11-05", "capabilities": {}}
    elif method == "tools/list":
        result = {"tools": [{"name": "echo", "description": "Echo text", "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}}]}
    elif method == "tools/call":
        result = {"content": [{"type": "text", "text": "echo:" + msg.get("params", {}).get("arguments", {}).get("text", "")}]}
    else:
        result = {}
    print(json.dumps({"jsonrpc": "2.0", "id": mid, "result": result}), flush=True)
''')
    mcp_json = ROOT / ".mcp.json"
    old = mcp_json.read_text() if mcp_json.exists() else None
    try:
        mcp_json.write_text(json.dumps({
            "mcpServers": {"echo": {"command": "python3", "args": [str(server)]}}
        }))
        manager = v6.McpManager()
        tools = manager.get_tool_definitions()
        assert any(tool["name"] == "mcp__echo__echo" for tool in tools)
        assert manager.call_tool("mcp__echo__echo", {"text": "hi"}) == "echo:hi"
    finally:
        if old is None:
            mcp_json.unlink(missing_ok=True)
        else:
            mcp_json.write_text(old)


def test_file_safety_session_and_compression():
    smoke = ROOT / "tmp" / "v6_offline_test"
    if smoke.exists():
        shutil.rmtree(smoke)
    smoke.mkdir(parents=True)

    external = smoke / "external.py"
    external.write_text("x = 1\n")
    agent = v6.Agent(ROOT)
    assert "sudo" in (agent.permissions.is_dangerous_shell("echo ok && sudo whoami") or "")

    out = agent.execute_tool("edit_file", {
        "path": "tmp/v6_offline_test/external.py",
        "old_text": "x = 1",
        "new_text": "x = 2",
    })
    assert "read-before-edit failed" in out

    out = agent.execute_tool("write_file", {
        "path": "tmp/v6_offline_test/a.py",
        "content": "y = 1\n",
    })
    assert "Created" in out
    agent.execute_tool("read_file", {"path": "tmp/v6_offline_test/a.py"})
    out = agent.execute_tool("edit_file", {
        "path": "tmp/v6_offline_test/a.py",
        "old_text": "y = 1",
        "new_text": "y = 2",
    })
    assert "+y = 2" in out

    agent.messages.append({
        "role": "user",
        "content": [{"type": "tool_result", "tool_use_id": "big", "content": "A" * (v6.LARGE_RESULT_CHARS + 1000)}],
    })
    note = agent.compress_messages()
    assert note is not None
    assert "large-result" in agent.messages[-1]["content"][0]["content"]

    agent.messages.append({"role": "user", "content": "hello"})
    agent.save_session("v6-offline-test")
    restored = v6.Agent(ROOT)
    assert "Loaded session" in restored.load_session("v6-offline-test")
    assert restored.messages[-1]["content"] == "hello"
