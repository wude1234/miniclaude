# Mini Claude Code

> **This repository has moved to [learn-claude-code](https://github.com/shareAI-lab/learn-claude-code)**
>
> Please visit the new repository for the latest content and updates.

---

**Build your own coding agent from scratch.**

[中文文档](./README_zh.md)

> Works with **[Kode CLI](https://github.com/shareAI-lab/Kode)**, **Claude Code**, **Cursor**, and any agent supporting the [Agent Skills Spec](https://github.com/anthropics/agent-skills).

<img height="400" alt="demo" src="https://github.com/user-attachments/assets/0e1e31f8-064f-4908-92ce-121e2eb8d453" />

## What is this?

A progressive tutorial that demystifies AI coding agents like Kode, Claude Code, and Cursor Agent.

**7 versions: the first 5 stay progressive, while v5/v6 add interview-oriented engineering details:**

| Version | Lines | What it adds | Core insight |
|---------|-------|--------------|--------------|
| [v0](./v0_bash_agent.py) | ~50 | 1 bash tool | Bash is all you need |
| [v1](./v1_basic_agent.py) | ~200 | 4 core tools | Model as Agent |
| [v2](./v2_todo_agent.py) | ~300 | Todo tracking | Explicit planning |
| [v3](./v3_subagent.py) | ~450 | Subagents | Divide and conquer |
| [v4](./v4_skills_agent.py) | ~550 | Skills | Domain expertise on-demand |
| [v5](./v5_interview_agent.py) | ~1000 | File safety, permissions, memory, compression, more tools | Interview-ready engineering details |
| [v6](./v6_full_agent.py) | ~1500 | MCP, semantic memory, streaming dual backends, sessions/budget | Full interview edition |

## Quick Start

```bash
pip install anthropic python-dotenv

# Configure your API
cp .env.example .env
# Edit .env with your API key

# Run any version
python v0_bash_agent.py  # Minimal
python v1_basic_agent.py # Core agent loop
python v2_todo_agent.py  # + Todo planning
python v3_subagent.py    # + Subagents
python v4_skills_agent.py # + Skills
python v5_interview_agent.py # + Interview-enhanced mechanisms
python v6_full_agent.py # + Full interview edition
```

### Run v5 with Alibaba Cloud DashScope

v5 supports OpenAI-compatible APIs, so it can run against DashScope:

```bash
export MINI_CLAUDE_BACKEND=openai
export DASHSCOPE_API_KEY=sk-xxx
export MODEL_NAME=qwen-turbo
python3 v5_interview_agent.py
python3 v6_full_agent.py --session demo --resume
```

## The Core Pattern

Every coding agent is just this loop:

```python
while True:
    response = model(messages, tools)
    if response.stop_reason != "tool_use":
        return response.text
    results = execute(response.tool_calls)
    messages.append(results)
```

That's it. The model calls tools until done. Everything else is refinement.

## File Structure

```
mini-claude-code/
├── v0_bash_agent.py       # ~50 lines: 1 tool, recursive subagents
├── v0_bash_agent_mini.py  # ~16 lines: extreme compression
├── v1_basic_agent.py      # ~200 lines: 4 tools, core loop
├── v2_todo_agent.py       # ~300 lines: + TodoManager
├── v3_subagent.py         # ~450 lines: + Task tool, agent registry
├── v4_skills_agent.py     # ~550 lines: + Skill tool, SkillLoader
├── v5_interview_agent.py  # Interview-enhanced: safety, permissions, memory, compression
├── v6_full_agent.py       # Full interview edition: MCP, streaming, semantic memory, sessions, budget
├── skills/                # Example skills (for learning)
└── docs/                  # Detailed explanations (EN + ZH)
```

## Using the Agent Builder Skill

This repository includes a meta-skill that teaches agents how to build agents:

```bash
# Scaffold a new agent project
python skills/agent-builder/scripts/init_agent.py my-agent

# Or with specific complexity level
python skills/agent-builder/scripts/init_agent.py my-agent --level 0  # Minimal
python skills/agent-builder/scripts/init_agent.py my-agent --level 1  # 4 tools (default)
```

### Install Skills for Production Use

```bash
# Kode CLI (recommended)
kode plugins install https://github.com/shareAI-lab/shareAI-skills

# Claude Code
claude plugins install https://github.com/shareAI-lab/shareAI-skills
```

See [shareAI-skills](https://github.com/shareAI-lab/shareAI-skills) for the full collection of production-ready skills.

## Key Concepts

### v0: Bash is All You Need
One tool. Recursive self-calls for subagents. Proves the core is tiny.

### v1: Model as Agent
4 tools (bash, read, write, edit). The complete agent in one function.

### v2: Structured Planning
Todo tool makes plans explicit. Constraints enable complex tasks.

### v3: Subagent Mechanism
Task tool spawns isolated child agents. Context stays clean.

### v4: Skills Mechanism
SKILL.md files provide domain expertise on-demand. Knowledge as a first-class citizen.

### v5: Interview-Enhanced Agent
Implements the engineering topics from `01-MiniClaudeCode项目专属面试题(1).pdf` that fit naturally on top of the teaching code:

- File safety: read-before-edit, mtime tracking, quote normalization, uniqueness checks, unified diff
- Permission modes: plan/default/acceptEdits/bypassPermissions/dontAsk
- More tools: list_files, grep_search, run_shell, remember, recall_memory, show_state
- Context control: large tool-result spillover, stale result snipping, recent-result retention
- Stronger subagents: isolated context, tool allowlists, token usage aggregation
- Better Skills loader: multiline frontmatter descriptions and resource hints

It is still a compact learning implementation, not a full production sandbox. Heavier topics from the PDF, such as a full MCP client, true semantic sideQuery recall, and dual Anthropic/OpenAI streaming backends, can be built on top of v5.

### v6: Full Interview Edition
Adds the advanced topics from the PDF:

- MCP client: loads servers from `~/.claude/settings.json`, project `.claude/settings.json`, and `.mcp.json`; initializes JSON-RPC over stdio, discovers tools, and routes calls
- semantic sideQuery: scans memory candidates, asks the LLM to select relevant notes, and falls back to keyword recall
- streaming dual backends: Anthropic streaming accumulates `partial_json` and assembles tool calls on `content_block_stop`; OpenAI/DashScope uses SSE deltas for tool calls
- 4-tier compression: large-result spillover, stale-result snipping, recent-result retention, and LLM summary compression
- sessions and budget: auto-saves `.mini_claude/sessions/*.json`, with `--resume`, `--session`, and `--max-cost`

Offline tests:

```bash
python3 tests/run_v6_offline_tests.py
```

The test requires no API key and covers Anthropic `content_block_stop` tool assembly, MCP stdio discovery/calls, file safety, compression, and session resume.

## Deep Dives

**Technical tutorials (docs/):**

| English | 中文 |
|---------|------|
| [v0: Bash is All You Need](./docs/v0-bash-is-all-you-need.md) | [v0: Bash 就是一切](./docs/v0-Bash就是一切.md) |
| [v1: Model as Agent](./docs/v1-model-as-agent.md) | [v1: 模型即代理](./docs/v1-模型即代理.md) |
| [v2: Structured Planning](./docs/v2-structured-planning.md) | [v2: 结构化规划](./docs/v2-结构化规划.md) |
| [v3: Subagent Mechanism](./docs/v3-subagent-mechanism.md) | [v3: 子代理机制](./docs/v3-子代理机制.md) |
| [v4: Skills Mechanism](./docs/v4-skills-mechanism.md) | [v4: Skills 机制](./docs/v4-Skills机制.md) |

**Original articles (articles/) - Chinese only, social media style:**
- [v0文章](./articles/v0文章.md) | [v1文章](./articles/v1文章.md) | [v2文章](./articles/v2文章.md) | [v3文章](./articles/v3文章.md) | [v4文章](./articles/v4文章.md)
- [上下文缓存经济学](./articles/上下文缓存经济学.md) - Context Caching Economics for Agent Developers

## Related Projects

| Repository | Purpose |
|------------|---------|
| [learn-claude-code](https://github.com/shareAI-lab/learn-claude-code) | New home for this project |
| [Kode](https://github.com/shareAI-lab/Kode) | Full-featured open source agent CLI (production) |
| [shareAI-skills](https://github.com/shareAI-lab/shareAI-skills) | Production-ready skills for AI agents |
| [Agent Skills Spec](https://github.com/anthropics/agent-skills) | Official specification |

### Use as Template

Fork and customize for your own agent projects:

```bash
git clone https://github.com/shareAI-lab/learn-claude-code
cd learn-claude-code
# Start from any version level
cp v1_basic_agent.py my_agent.py
```

## Philosophy

> The model is 80%. Code is 20%.

Kode and Claude Code work not because of clever engineering, but because the model is trained to be an agent. Our job is to give it tools and stay out of the way.

## License

MIT

---

**Model as Agent. That's the whole secret.**

[@baicai003](https://x.com/baicai003)
