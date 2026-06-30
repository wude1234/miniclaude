# Mini Claude Code

> **本仓库已迁移至 [learn-claude-code](https://github.com/shareAI-lab/learn-claude-code)**
>
> 请访问新仓库获取最新内容和更新。

---

**从零开始构建你自己的 AI Agent。**

[English](./README.md)

> 兼容 **[Kode CLI](https://github.com/shareAI-lab/Kode)**、**Claude Code**、**Cursor**，以及任何支持 [Agent Skills Spec](https://github.com/anthropics/agent-skills) 的 Agent。

<img height="400" alt="demo" src="https://github.com/user-attachments/assets/0e1e31f8-064f-4908-92ce-121e2eb8d453" />

## 这是什么？

一个渐进式教程，揭开 Kode、Claude Code、Cursor Agent 等 AI Agent 的神秘面纱。

**7 个版本，前 5 个保持渐进式教学，v5/v6 对齐面试材料做工程化增强：**

| 版本 | 行数 | 新增内容 | 核心洞察 |
|------|------|---------|---------|
| [v0](./v0_bash_agent.py) | ~50 | 1 个 bash 工具 | Bash 就是一切 |
| [v1](./v1_basic_agent.py) | ~200 | 4 个核心工具 | 模型即代理 |
| [v2](./v2_todo_agent.py) | ~300 | Todo 追踪 | 显式规划 |
| [v3](./v3_subagent.py) | ~450 | 子代理 | 分而治之 |
| [v4](./v4_skills_agent.py) | ~550 | Skills | 按需领域专业 |
| [v5](./v5_interview_agent.py) | ~1000 | 文件安全、权限、记忆、压缩、更多工具 | 面试级工程细节 |
| [v6](./v6_full_agent.py) | ~1500 | MCP、语义记忆、流式双后端、会话/预算 | 完整面试版 |

## 快速开始

```bash
pip install anthropic python-dotenv

# 配置 API
cp .env.example .env
# 编辑 .env 填入你的 API key

# 运行任意版本
python v0_bash_agent.py  # 极简版
python v1_basic_agent.py # 核心 Agent 循环
python v2_todo_agent.py  # + Todo 规划
python v3_subagent.py    # + 子代理
python v4_skills_agent.py # + Skills
python v5_interview_agent.py # + 面试增强版工程机制
python v6_full_agent.py # + 完整面试版
```

### 使用阿里云百炼 / DashScope 运行 v5

v5 支持 OpenAI-compatible 接口，可直接使用 DashScope：

```bash
export MINI_CLAUDE_BACKEND=openai
export DASHSCOPE_API_KEY=sk-xxx
export MODEL_NAME=qwen-turbo
python3 v5_interview_agent.py
python3 v6_full_agent.py --session demo --resume
```

## 核心模式

每个 Agent 都只是这个循环：

```python
while True:
    response = model(messages, tools)
    if response.stop_reason != "tool_use":
        return response.text
    results = execute(response.tool_calls)
    messages.append(results)
```

就这样。模型持续调用工具直到完成。其他一切都是精化。

## 文件结构

```
mini-claude-code/
├── v0_bash_agent.py       # ~50 行: 1 个工具，递归子代理
├── v0_bash_agent_mini.py  # ~16 行: 极限压缩
├── v1_basic_agent.py      # ~200 行: 4 个工具，核心循环
├── v2_todo_agent.py       # ~300 行: + TodoManager
├── v3_subagent.py         # ~450 行: + Task 工具，代理注册表
├── v4_skills_agent.py     # ~550 行: + Skill 工具，SkillLoader
├── v5_interview_agent.py  # 面试增强版: 文件安全、权限、记忆、压缩
├── v6_full_agent.py       # 完整面试版: MCP、流式、语义记忆、会话、预算
├── skills/                # 示例 Skills（用于学习）
└── docs/                  # 详细文档 (中英双语)
```

## 使用 Agent Builder Skill

本仓库包含一个元技能，教 Agent 如何构建 Agent：

```bash
# 脚手架生成新 Agent 项目
python skills/agent-builder/scripts/init_agent.py my-agent

# 或指定复杂度级别
python skills/agent-builder/scripts/init_agent.py my-agent --level 0  # 极简
python skills/agent-builder/scripts/init_agent.py my-agent --level 1  # 4 工具 (默认)
```

### 生产环境安装 Skills

```bash
# Kode CLI（推荐）
kode plugins install https://github.com/shareAI-lab/shareAI-skills

# Claude Code
claude plugins install https://github.com/shareAI-lab/shareAI-skills
```

详见 [shareAI-skills](https://github.com/shareAI-lab/shareAI-skills) 获取完整的生产就绪 skills 集合。

## 核心概念

### v0: Bash 就是一切
一个工具。递归自调用实现子代理。证明核心是极小的。

### v1: 模型即代理
4 个工具 (bash, read, write, edit)。完整 Agent 在一个函数里。

### v2: 结构化规划
Todo 工具让计划显式化。约束赋能复杂任务。

### v3: 子代理机制
Task 工具生成隔离的子代理。上下文保持干净。

### v4: Skills 机制
SKILL.md 文件按需提供领域专业知识。知识作为一等公民。

### v5: 面试增强版
把 `01-MiniClaudeCode项目专属面试题(1).pdf` 中能自然落地到教学版的工程点实现出来：

- 文件安全：read-before-edit、mtime 追踪、弯引号归一化、唯一性检查、unified diff
- 权限模式：plan/default/acceptEdits/bypassPermissions/dontAsk
- 更多工具：list_files、grep_search、run_shell、remember、recall_memory、show_state
- 上下文控制：大结果落盘、旧工具结果 snip、保留最近结果
- 子代理增强：隔离上下文、工具白名单、token 用量回传
- Skills 增强：支持多行 frontmatter description 和资源提示

它仍然是学习实现，不是完整生产沙箱。PDF 中提到的完整 MCP client、真正的 semantic sideQuery、Anthropic/OpenAI 双 streaming 后端等更重模块，可以在 v5 基础上继续扩展。

### v6: 完整面试版
进一步补齐 PDF 中的高级追问点：

- MCP client：从 `~/.claude/settings.json`、项目 `.claude/settings.json`、`.mcp.json` 加载 MCP server，使用 JSON-RPC over stdio 初始化、发现工具、路由调用
- semantic sideQuery：先扫描记忆候选，再用 LLM 选择相关记忆；失败时回退关键词召回
- 双后端 streaming：Anthropic streaming 累积 `partial_json`，在 `content_block_stop` 组装工具调用；OpenAI/DashScope 走 SSE delta 累积 tool calls
- 4 层压缩：大结果落盘、旧结果 snip、保留最近结果、超阈值 LLM 摘要压缩
- 会话与预算：`.mini_claude/sessions/*.json` 自动保存，支持 `--resume`、`--session`、`--max-cost`

离线测试：

```bash
python3 tests/run_v6_offline_tests.py
```

该测试不需要 API key，会覆盖 Anthropic `content_block_stop` 工具块组装、MCP stdio 工具发现/调用、文件安全、压缩和 session resume。

## 深入阅读

**技术教程 (docs/):**

| English | 中文 |
|---------|------|
| [v0: Bash is All You Need](./docs/v0-bash-is-all-you-need.md) | [v0: Bash 就是一切](./docs/v0-Bash就是一切.md) |
| [v1: Model as Agent](./docs/v1-model-as-agent.md) | [v1: 模型即代理](./docs/v1-模型即代理.md) |
| [v2: Structured Planning](./docs/v2-structured-planning.md) | [v2: 结构化规划](./docs/v2-结构化规划.md) |
| [v3: Subagent Mechanism](./docs/v3-subagent-mechanism.md) | [v3: 子代理机制](./docs/v3-子代理机制.md) |
| [v4: Skills Mechanism](./docs/v4-skills-mechanism.md) | [v4: Skills 机制](./docs/v4-Skills机制.md) |

**原创文章 (articles/) - 公众号风格:**
- [v0文章](./articles/v0文章.md) | [v1文章](./articles/v1文章.md) | [v2文章](./articles/v2文章.md) | [v3文章](./articles/v3文章.md) | [v4文章](./articles/v4文章.md)
- [上下文缓存经济学](./articles/上下文缓存经济学.md) - Agent 开发者必知的成本优化指南

## 相关项目

| 仓库 | 用途 |
|------|------|
| [learn-claude-code](https://github.com/shareAI-lab/learn-claude-code) | 本项目的新地址 |
| [Kode](https://github.com/shareAI-lab/Kode) | 全功能开源 Agent CLI（生产环境） |
| [shareAI-skills](https://github.com/shareAI-lab/shareAI-skills) | 生产就绪的 AI Agent Skills |
| [Agent Skills Spec](https://github.com/anthropics/agent-skills) | 官方规范 |

### 作为模板

Fork 并自定义为你自己的 Agent 项目：

```bash
git clone https://github.com/shareAI-lab/learn-claude-code
cd learn-claude-code
# 从任意版本级别开始
cp v1_basic_agent.py my_agent.py
```

## 设计哲学

> 模型是 80%，代码是 20%。

Kode 和 Claude Code 能工作，不是因为巧妙的工程，而是因为模型被训练成了 Agent。我们的工作就是给它工具，然后闪开。

## License

MIT

---

**模型即代理。这就是全部秘密。**

[@baicai003](https://x.com/baicai003)
