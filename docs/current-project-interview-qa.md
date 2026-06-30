# Mini Claude Code 当前项目面试题汇总

> 基于当前仓库 `v0_bash_agent.py` 到 `v6_full_agent.py` 的真实实现整理。
> 原 PDF 中的题目方向被保留，但回答口径已改成当前项目可运行、可追源码、可测试的版本。

## 使用口径

面试时建议这样介绍：

> Mini Claude Code 是一个基于 Python 复现并扩展 Claude Code 类 coding agent 核心机制的项目。v0-v4 用最少代码讲清 Agent Loop、工具调用、Todo、Sub-agent 和 Skills；v5/v6 在教学版基础上补充文件安全、权限系统、上下文压缩、语义记忆、MCP、双后端 streaming、session resume 和 cost budget 等工程机制。它不是 Claude Code 50 万行生产代码的完整复刻，而是核心机制可运行、可演示、可追源码的学习/面试复现版。

不要说：

> 我完整复刻了 Claude Code 的全部生产能力。

建议说：

> 我复现并验证了 Claude Code 类 coding agent 的关键机制，并用 v6 做成了一个可运行的 Python 面试完整版。

如果面试官追问 GitHub 历史或“从零实现”的边界，建议补一句：

> 这个项目保留了 Mini Claude Code 教学主线，我重点做的是基于这条主线补齐和验证 v5/v6 的工程机制，包括文件安全、上下文压缩、MCP、双后端 streaming、session resume 和离线测试。我不会把它包装成完整生产级 Claude Code，而是定位为核心机制可运行、可测试、可讲清楚的面试版。

## 项目版本速览

| 版本 | 文件 | 核心能力 | 面试价值 |
| --- | --- | --- | --- |
| v0 | `v0_bash_agent.py` | 单 bash 工具 + agent loop | 证明 agent 核心极小 |
| v1 | `v1_basic_agent.py` | bash/read/write/edit 四工具 | 模型即代理 |
| v2 | `v2_todo_agent.py` | TodoWrite | 显式规划与状态追踪 |
| v3 | `v3_subagent.py` | Task subagent | 上下文隔离 |
| v4 | `v4_skills_agent.py` | SkillLoader + SKILL.md | 知识外置 |
| v5 | `v5_interview_agent.py` | 文件安全、权限、记忆、压缩、DashScope 后端 | 面试增强版 |
| v6 | `v6_full_agent.py` | MCP、semantic sideQuery、双 streaming、session、cost budget | 完整面试版 |

## 简历项目写法

推荐放在简历里的版本：

**Mini Claude Code：Claude Code 类 Coding Agent 核心机制复现与工程化增强**  
Github 仓库链接：https://github.com/wude1234/miniclaude

- 基于 Python 复现并扩展 **ReAct 式 Agent Loop**，构建“模型决策 - Tool Calling - 工具执行 - Observation 回写”的闭环，支持文件读写、命令执行、代码搜索、Todo 规划、Sub-agent 和 Skills。
- 针对 Coding Agent 长任务中的上下文膨胀和信息污染问题，设计 **4 层上下文压缩策略**，包括大工具结果落盘、旧结果 snip、最近结果保留和 LLM 摘要压缩，并通过 **session resume** 保存 messages、token usage、权限状态和文件读取状态。
- 针对自动代码编辑可靠性问题，实现 **read-before-edit**、**mtime 追踪**、**old_text 唯一性检查**、**unified diff** 和危险 shell 检测，降低 stale edit、误替换和高风险命令执行带来的工程风险。
- 集成 **MCP JSON-RPC stdio** 工具发现/调用机制，并适配 **Anthropic / OpenAI-compatible 双后端 streaming**，统一抽象为内部 `ModelResult`；离线测试覆盖 streaming tool assembly、MCP 调用、文件安全、上下文压缩和 session 恢复。

更适合空间紧张的简历短版：

> 基于 Python 复现并扩展 Claude Code 类 **ReAct 式 Coding Agent**，支持 Agent Loop、Tool Calling、Sub-agent、Skills、MCP、双后端 streaming、上下文压缩、权限控制与 session resume。针对长任务中的上下文膨胀、工具结果污染和自动代码编辑风险，设计 **4 层上下文治理策略** 与 **read-before-edit / mtime / unified diff** 文件安全机制，并通过离线测试验证 streaming 工具调用组装、MCP 调用、压缩和会话恢复流程。

简历上建议加粗的关键词：

- **ReAct 式 Agent Loop**
- **Tool Calling**
- **4 层上下文压缩策略**
- **read-before-edit**
- **Sub-agent**
- **Skills**
- **MCP JSON-RPC stdio**
- **双后端 streaming**
- **session resume**

简历上不建议夸大的说法：

- 不说“完整复刻 Claude Code 生产能力”。
- 不说“完全从零实现 50 万行 Claude Code”。
- 不说“生产级安全沙箱”，当前权限和 shell 安全是学习/面试级防护。

## 可验证命令

```bash
python3 -m py_compile v0_bash_agent_mini.py v0_bash_agent.py v1_basic_agent.py v2_todo_agent.py v3_subagent.py v4_skills_agent.py v5_interview_agent.py v6_full_agent.py
python3 tests/run_v6_offline_tests.py
python3 v6_full_agent.py --help
```

DashScope 真实测试方式：

```bash
export MINI_CLAUDE_BACKEND=openai
export DASHSCOPE_API_KEY=sk-xxx
export MODEL_NAME=qwen-turbo
export MINI_CLAUDE_STREAM=1
python3 v6_full_agent.py --session demo --resume
```

## 第一部分：项目整体

### Q1：请介绍一下你的 Mini Claude Code 项目

标准回答：

Mini Claude Code 是一个渐进式 coding agent 复现项目。它从一个最小 bash agent 开始，逐步加入文件工具、Todo 规划、Sub-agent、Skills，最后在 v5/v6 中补齐面试材料里常见的工程机制：文件编辑安全、权限模式、上下文压缩、语义记忆、MCP、双后端 streaming、session persistence 和 cost budget。

核心结构：

- v0-v4：教学主线，强调 agent 的本质是模型 + 工具 + 循环。
- v5：面试增强版，加入文件安全、权限、轻量记忆、DashScope/OpenAI-compatible 后端。
- v6：完整面试版，加入 MCP client、semantic sideQuery、Anthropic/OpenAI 双 streaming、4 层压缩、会话恢复和预算控制。

STAR 说法：

- S：Claude Code/Cursor 这类 coding agent 对外看起来复杂，但核心机制可以拆解。
- T：目标是用 Python 做一个可运行、可讲解、可扩展的 Mini Claude Code。
- A：按 v0-v6 渐进实现，从工具循环到生产级机制逐步叠加。
- R：最终形成一个可演示、可追源码、可测试的 agent 学习项目。

追问方向：

- 为什么不一开始就写 v6？
- v0-v4 和 v5/v6 的定位差异是什么？
- 这个项目和直接调用 LLM API 有什么本质区别？

### Q2：这个项目最核心的洞察是什么？

标准回答：

最核心的洞察是：模型本身就是 agent，代码主要负责提供工具、保存上下文、执行工具结果并再次喂给模型。

核心循环是：

```python
while True:
    response = model(messages, tools)
    if no tool calls:
        return response
    results = execute_tools(response.tool_calls)
    messages.append(tool_results)
```

这个模式在 v1 的 `agent_loop` 中最清楚，v2-v6 都是在这个循环上叠加工程能力。

追问方向：

- Agent Loop 的退出条件是什么？
- 如果模型无限调用工具怎么办？
- 为什么 tool result 要作为下一轮上下文？

### Q3：v0-v6 的递进设计为什么重要？

标准回答：

递进设计让项目具备很强的可解释性：

- v0 证明 bash 一个工具也能构成 agent。
- v1 把文件读写拆成显式工具，降低模型使用 shell 的风险。
- v2 用 TodoWrite 解决长任务计划遗忘。
- v3 用 Task 解决上下文污染。
- v4 用 Skill 解决领域知识按需注入。
- v5/v6 把这些教学机制扩展成面试可问的工程系统。

追问方向：

- 哪个版本最能体现 agent 的本质？
- 哪个版本最接近真实 Claude Code？
- 为什么 Skills 不直接写进 system prompt？

### Q4：项目和普通 chatbot 的区别是什么？

标准回答：

普通 chatbot 是用户输入到模型输出；Mini Claude Code 是 Agent Loop。

区别包括：

- 工具调用：能读文件、写文件、搜索、执行 shell、调用 MCP。
- 状态管理：维护 messages、Todo、read_file_state、session、token usage。
- 安全控制：权限模式、read-before-edit、mtime 检查、危险 shell 检测。
- 上下文治理：大结果落盘、旧结果 snip、摘要压缩。
- 多 agent 协作：Task subagent 通过隔离上下文完成子任务。

追问方向：

- tool call 失败后 agent 怎么恢复？
- 工具结果太大怎么办？
- 为什么需要权限系统？

### Q5：当前项目和原 PDF 中描述的版本有什么差异？

标准回答：

原 PDF 更像一个完整面试题库，很多题目描述的是理想完整版。当前项目经过扩展后，v6 已经覆盖了大部分核心机制，但仍保持单文件教学实现的边界。

当前已实现：

- MCP client over stdio
- semantic sideQuery 记忆召回
- Anthropic streaming 事件解析
- DashScope/OpenAI-compatible streaming 真测
- 4 层压缩
- session resume
- cost budget

边界：

- 不是 Claude Code 生产代码的完整复刻。
- 权限和 shell 安全是面试/学习级，不是强隔离沙箱。
- Anthropic streaming 没有官方 key 真连，但 `content_block_stop` 解析逻辑有离线模拟测试覆盖。

追问方向：

- 哪些能力真测过？
- 哪些能力是离线测试覆盖？
- 为什么不直接说完整复刻？

### Q6：如果重新设计，你会怎么改？

标准回答：

会做三类改进：

1. 模块化：把 v6 单文件拆成 `agent.py`、`tools.py`、`memory.py`、`mcp_client.py`、`compression.py`。
2. 安全化：把 shell 执行放进沙箱或容器，引入 allowlist 和用户确认机制。
3. 持久化：把 session、memory、tool result 文件统一成可索引的项目状态库。

追问方向：

- 为什么现在保留单文件？
- 拆模块后怎么避免循环依赖？
- 权限系统如何做到生产级？

## 第二部分：Agent Loop 与 Tool Calling

### Q7：Agent Loop 的主流程是什么？

标准回答：

主流程在 v6 的 `run_once` 中：

1. 把用户 prompt 加入 `messages`。
2. 每轮调用 `call_model`。
3. 将模型响应转换成 assistant message 和 tool_calls。
4. 如果没有 tool_calls，返回最终文本。
5. 如果有 tool_calls，逐个执行工具。
6. 把 tool_result 作为 user message 加回 messages。
7. 自动保存 session。

追问方向：

- 为什么 tool_result 是 user message？
- 为什么 assistant 的 tool_use 也要保存？
- max_turns 有什么用？

### Q8：Tool schema 是怎么定义的？

标准回答：

工具都用类似 Anthropic/OpenAI function calling 的 schema 定义：

- `name`
- `description`
- `input_schema`

v6 的 `BASE_TOOLS` 包括：

- `run_shell`
- `read_file`
- `list_files`
- `grep_search`
- `write_file`
- `edit_file`
- `TodoWrite`
- `remember`
- `recall_memory`
- `enter_plan_mode`
- `exit_plan_mode`
- `show_state`

另有 `Task`、`Skill` 和动态 MCP 工具。

追问方向：

- schema 为什么能约束模型？
- description 写得好坏会影响什么？
- 新增工具需要改哪些地方？

### Q9：Anthropic streaming 模式下工具 JSON 怎么累积？

标准回答：

v6 中由 `AnthropicStreamAssembler` 负责：

- `content_block_start`：记录 tool block 的 `id/name/index`。
- `content_block_delta`：不断把 `partial_json` 拼到对应 index 的缓冲区。
- `content_block_stop`：说明该工具块 JSON 已完整，此时才 `json.loads`。
- 解析完成后触发 `on_tool_ready` 回调。

为什么不能在 delta 阶段解析？

因为 `partial_json` 是碎片，中间状态通常不是合法 JSON。

追问方向：

- 一次响应有多个 tool_use 怎么办？
- index 的作用是什么？
- JSON 解析失败怎么处理？

### Q10：`content_block_stop` 早期执行怎么实现？

标准回答：

在 v6 中，`AnthropicStreamAssembler.handle_event` 收到 `content_block_stop` 后立即把对应工具块从 `tool_blocks` 中 pop 出来，解析 JSON，并调用 `on_tool_ready`。

当前实现把“工具块就绪”和“最终执行工具”解耦了：

- 解析器层能在 stop 时立即标记 tool ready。
- Agent 层仍统一在模型响应收束后执行工具，便于保持教学实现简单。
- 离线测试覆盖了 stop 到达前不触发、stop 到达后触发的行为。

追问方向：

- 真正生产版如何做到边流式边执行？
- 如果 tool A ready 了但模型还在输出 tool B，能否并行执行？
- 早期执行的风险是什么？

### Q11：OpenAI/DashScope streaming 和 Anthropic 有什么区别？

标准回答：

Anthropic 是 content block 事件：

- `content_block_start`
- `content_block_delta`
- `content_block_stop`

OpenAI-compatible/DashScope 是 SSE delta：

- 每行 `data: {...}`
- `choices[].delta.content`
- `choices[].delta.tool_calls[].function.arguments`

v6 的 `call_openai_compatible_stream` 会累积每个 tool call index 的 name、id、arguments，直到 stream 结束后组装成统一的 `ModelResult`。

追问方向：

- OpenAI 为什么没有 `content_block_stop`？
- DashScope 怎么兼容 OpenAI tools？
- streaming usage 怎么统计？

### Q12：双后端如何统一到同一套 Agent Loop？

标准回答：

v6 定义了统一的 `ModelResult`：

- `content`
- `stop_reason`
- `usage`

Anthropic 原生响应、Anthropic streaming、OpenAI-compatible 非流式、OpenAI-compatible streaming 最后都转换成这个结构。

这样 `run_once` 不需要关心后端差异，只处理统一的 `tool_use` 和 `text`。

追问方向：

- 为什么要做中间层？
- 如果以后接 Gemini 怎么扩展？
- tool schema 在两个后端间有什么差异？

### Q13：ReAct 框架和这个项目有什么关系？

标准回答：

ReAct 是 Reason + Act 的循环。Mini Claude Code 的表现形式是：

- Reason：模型根据上下文决定下一步。
- Act：调用工具。
- Observation：工具结果写回 messages。
- Repeat：继续下一轮。

项目没有强制输出显式 CoT，而是用工具结果驱动模型隐式推理。

追问方向：

- ReAct 和 CoT 有什么区别？
- 为什么不要求模型输出详细思考过程？
- 工具结果如何影响下一轮决策？

## 第三部分：文件编辑安全

### Q14：read-before-edit 是怎么实现的？

标准回答：

`Workspace` 维护 `read_file_state: dict[path, mtime]`。

- `read_file` 时记录文件绝对路径和 mtime。
- `write_file/edit_file` 修改已有文件前检查：
  - 文件是否读过。
  - 当前 mtime 是否和读取时一致。

如果没读过或文件被外部改过，就拒绝编辑。

追问方向：

- 新建文件为什么不需要 read-before-edit？
- mtime 精度不足怎么办？
- 多 subagent 同时编辑同一文件会怎样？

### Q15：mtime 检查解决什么问题？

标准回答：

mtime 检查解决 stale edit 和并发覆盖问题。

场景：

1. Agent 读了文件 A。
2. 用户或另一个工具修改了文件 A。
3. Agent 还按旧内容 edit。

没有 mtime 检查会静默覆盖新改动；有 mtime 检查会要求重新读取。

追问方向：

- mtime 和文件 hash 哪个更可靠？
- 如果保存太快 mtime 没变怎么办？
- 生产版是否需要文件锁？

### Q16：弯引号归一化为什么需要？

标准回答：

LLM 有时会输出 typographic quotes：

- `“”`
- `‘’`
- `′″`

但代码里通常是直引号。v6 的 `normalize_quotes` 会把弯引号映射成直引号，`find_actual_string` 会先精确匹配，失败后做归一化匹配。

追问方向：

- 如果 Markdown 文档本来就需要弯引号怎么办？
- 除了引号，还有哪些 LLM 输出污染？
- 归一化会不会误替换？

### Q17：edit_file 的唯一性检查是什么？

标准回答：

`edit_file` 在找到 old_text 后，会检查归一化后的 old_text 在文件中出现次数。

如果出现多次，拒绝编辑，要求模型提供更多上下文。

作用：

- 防止只替换第一个重复片段导致误改。
- 逼模型提供更精确的 old_text。

追问方向：

- 如果用户想全部替换怎么办？
- `str.count` 有什么局限？
- 怎么实现 range-based edit？

### Q18：unified diff 在 Agent 工作流里有什么作用？

标准回答：

每次 `write_file/edit_file` 成功后，v6 会返回 unified diff。

作用：

- 给用户可视化变更。
- 给模型下一轮上下文，让模型知道自己改了什么。
- 方便调试和回滚。

追问方向：

- 为什么不用只返回 success？
- diff 太大怎么办？
- diff 和 session persistence 如何结合？

### Q19：文件安全机制整体有哪些层？

标准回答：

当前项目有四层：

1. workspace path sandbox：禁止路径逃出项目。
2. read-before-edit：已有文件必须先读。
3. mtime tracking：防止外部修改后 stale edit。
4. quote normalization + uniqueness check + diff。

追问方向：

- 为什么 path sandbox 不等于安全沙箱？
- run_shell 是否绕过文件工具限制？
- 生产级应该怎么做？

## 第四部分：上下文压缩

### Q20：为什么需要上下文压缩？

标准回答：

Agent 每次工具结果都会进入 messages。复杂任务读很多文件、grep 很多结果、运行测试输出很长，很快会导致：

- token 成本增加。
- 延迟增加。
- 超过上下文窗口。
- 模型注意力稀释。

所以需要压缩工具结果和历史消息。

追问方向：

- 哪些内容不能压缩？
- 压缩会不会丢失关键信息？
- 怎么判断压缩时机？

### Q21：v6 的 4 层压缩是什么？

标准回答：

v6 的 `compress_messages` 有四类策略：

1. 大结果落盘：单个 tool_result 超过 `LARGE_RESULT_CHARS`，完整内容写到 `.mini_claude/context/`，上下文里只保留预览和路径。
2. 旧结果 snip：上下文过大时，旧 tool_result 替换成 `<snipped ...>`。
3. 保留最近结果：最近 `KEEP_RECENT_RESULTS` 个工具结果不 snip。
4. LLM 摘要压缩：超过 `SUMMARY_CONTEXT_CHARS` 后，把旧 messages 摘要成 `<context-summary>`，保留最近消息。

追问方向：

- 为什么先落盘再摘要？
- 为什么保留最近结果？
- 摘要失败怎么办？

### Q22：大结果落盘怎么实现？

标准回答：

当工具结果超过阈值：

- 写入 `.mini_claude/context/tool_result_*.txt`
- messages 中替换为：
  - 保存路径
  - 原始字符数
  - 头尾预览

这样既避免上下文爆炸，又保留完整结果可追溯。

追问方向：

- 为什么不直接截断？
- 落盘文件如何清理？
- 模型如何重新读取完整结果？

### Q23：LLM 摘要压缩后的消息结构是什么？

标准回答：

v6 会把旧消息替换成两条消息：

- user：`<context-summary-request>...`
- assistant：`<context-summary>...</context-summary>`

然后拼接最近 6 条原始消息。

这样保持 user/assistant 交替结构，避免破坏模型 API 的消息格式约束。

追问方向：

- 为什么不能直接塞 system prompt？
- 为什么保留最近 6 条？
- 摘要 prompt 应包含哪些内容？

### Q24：如何支持 30+ 轮工具调用？

标准回答：

靠组合策略：

- 大工具结果落盘。
- 旧工具结果 snip。
- 最近结果保留。
- 超阈值摘要旧上下文。
- session 保存完整历史，压缩只是运行上下文治理。

追问方向：

- 成本和上下文窗口如何权衡？
- 摘要会不会遗漏 bug？
- 是否应该保存原始历史和压缩历史两份？

## 第五部分：权限系统

### Q25：v6 有哪些权限模式？

标准回答：

有五种：

- `plan`：禁止写文件和 shell 等 mutating tools。
- `default`：允许常规操作，危险 shell 被拦截。
- `acceptEdits`：偏向允许文件编辑。
- `bypassPermissions`：跳过权限，主要给可信 subagent 或测试使用。
- `dontAsk`：更保守，阻断写操作和 shell。

追问方向：

- plan mode 里能做什么？
- bypassPermissions 为什么危险？
- dontAsk 和 plan 有什么区别？

### Q26：声明式 allow/deny 规则怎么实现？

标准回答：

`PermissionManager` 从环境变量读取：

- `MINI_CLAUDE_ALLOW`
- `MINI_CLAUDE_DENY`

每条规则用 fnmatch 匹配 `tool + args_json`。deny 优先于 allow。

追问方向：

- 为什么 deny 优先？
- 规则太复杂怎么办？
- 是否应该支持项目级配置文件？

### Q27：危险 shell 检测怎么做？

标准回答：

v6 有两层：

1. 正则模式：拦截 `rm -rf /`、`sudo`、`shutdown`、`git reset --hard` 等。
2. 近似 shell AST：按 `&&`、`||`、`;`、`|` 拆 segment，再用 `shlex.split` 识别每段命令。

这样可以识别：

```bash
echo ok && sudo whoami
```

追问方向：

- 为什么这还不是生产级安全？
- shell 语法有哪些难点？
- 如何用容器沙箱替代黑名单？

### Q28：plan mode 如何工作？

标准回答：

模型可调用 `enter_plan_mode` 进入 plan。进入后：

- read/search/recall/show_state 等仍可用。
- write/edit/run_shell/remember 等 mutating tools 被阻断。
- `exit_plan_mode` 允许退出，避免死锁。

追问方向：

- 为什么 exit_plan_mode 不能被阻断？
- plan mode 的输出应该如何让用户确认？
- acceptEdits 如何接 plan mode？

## 第六部分：记忆系统

### Q29：项目支持哪些 memory 类型？

标准回答：

v6 的 `MemoryStore` 支持四种 kind：

- `project`
- `user`
- `local`
- `session`

保存路径在 `.mini_claude/memory/{project_hash}/`，文件是 Markdown + frontmatter。

追问方向：

- 为什么要用 project hash？
- user memory 和 project memory 有什么区别？
- memory 文件如何迁移？

### Q30：semantic sideQuery 是怎么实现的？

标准回答：

`semantic_recall` 分三步：

1. `MemoryStore.candidates()` 扫描 memory 文件，生成 filename/title/kind/preview。
2. `side_query` 调用 LLM，让它返回相关 memory 文件名 JSON。
3. 读取选中的 memory 文件，返回给主 agent。

如果 sideQuery 失败，回退到关键词 recall。

追问方向：

- sideQuery 为什么要单独调用？
- sideQuery 消耗 token，如何控制成本？
- 为什么需要 fallback？

### Q31：异步预取是否实现了？

标准回答：

当前 v6 实现了 semantic sideQuery，但没有把 prefetch 做成后台异步任务。原因是单文件教学实现优先保证可读性。

可以扩展为：

- 用户输入后立即启动 memory prefetch task。
- 模型响应前/工具调用前合并结果。
- 超时则跳过，不阻塞主流程。

追问方向：

- prefetch 什么时候启动？
- 失败或超时怎么办？
- prefetch 结果如何注入上下文？

### Q32：为什么维护 memory candidates 而不是每次全文喂给 LLM？

标准回答：

因为全文可能很大，sideQuery 只需要判断相关性。用 headers/preview 候选列表能降低 token 成本。

完整内容只在候选被选中后读取。

追问方向：

- preview 太短会不会漏召回？
- 是否需要 embedding？
- 什么时候用关键词，什么时候用 LLM？

## 第七部分：Sub-agent、MCP 与 Skills

### Q33：Sub-agent 的 fork-return 模式是什么？

标准回答：

`tool_task` 创建新的 `Agent` 实例：

- 新 messages，隔离上下文。
- 根据 agent_type 限制工具集。
- 执行子任务后只返回最终文本给主 agent。
- token usage 合并到主 agent。

这就是 fork-return：fork 出子 agent，return 摘要结果。

追问方向：

- 为什么不把主上下文传给子 agent？
- subagent 能不能再递归创建 subagent？
- token 如何聚合？

### Q34：内置 agent 类型有哪些？

标准回答：

当前有：

- `explore`：只读搜索和分析。
- `plan`：只读规划。
- `code`：允许实现，但不递归 Task。

差异主要体现在工具白名单和 system prompt。

追问方向：

- explore 和 plan 都只读，差异是什么？
- 为什么 code subagent 不给 Task？
- 自定义 agent 怎么做？

### Q35：MCP 是什么？为什么用 JSON-RPC over stdio？

标准回答：

MCP 是 Model Context Protocol，用于让 agent 动态发现和调用外部工具。

使用 JSON-RPC over stdio 的原因：

- server 是独立进程，隔离崩溃。
- 语言无关。
- 不需要网络端口。
- 和 Claude Code 生态一致。

追问方向：

- JSON-RPC 和 REST 的区别？
- stdio server 崩溃怎么办？
- MCP 工具如何映射成 LLM tools？

### Q36：MCP client 如何实现？

标准回答：

v6 的 `McpConnection`：

- `initialize`
- `notifications/initialized`
- `tools/list`
- `tools/call`

内部用：

- `next_id` 生成 request id。
- `pending: dict[id, Future]` 匹配响应。
- `_read_loop` 后台读取 stdout。

`McpManager` 负责读取配置、发现工具、路由调用。

追问方向：

- pending future 解决什么问题？
- 响应乱序怎么办？
- 为什么当前实现用短连接？

### Q37：MCP 工具命名前缀为什么是 `mcp__server__tool`？

标准回答：

作用：

- 避免和内置工具重名。
- 根据 serverName 路由到对应 MCP server。
- 支持多个 server 都有同名工具。

解析时：

- split `__`
- 第二段是 server name
- 后面拼回 tool name

追问方向：

- tool name 自身含 `__` 怎么办？
- server name 能不能含 `__`？
- MCP 工具 schema 从哪里来？

### Q38：Skills 系统如何实现？

标准回答：

`SkillLoader` 扫描 `skills/*/SKILL.md`：

- 解析 YAML-like frontmatter。
- 读取 name/description/context/allowed-tools。
- 系统提示只放技能描述。
- 调用 `Skill` 工具时才注入完整 SKILL.md 内容。

这是 progressive disclosure，避免一开始塞太多上下文。

追问方向：

- 为什么技能不直接进 system prompt？
- allowed-tools 如何限制 skill？
- inline skill 和 fork skill 有什么区别？

## 第八部分：双后端、会话与预算

### Q39：如何支持 Anthropic 和 OpenAI/DashScope 双后端？

标准回答：

通过环境变量：

- `MINI_CLAUDE_BACKEND=openai` 走 OpenAI-compatible。
- `DASHSCOPE_API_KEY` 或 `OPENAI_API_KEY` 提供 key。
- 默认 DashScope base url 是 `https://dashscope.aliyuncs.com/compatible-mode/v1`。
- 否则走 Anthropic SDK。

两种后端都统一成 `ModelResult`。

追问方向：

- 为什么 DashScope 能走 OpenAI-compatible？
- tool schema 如何转换？
- 后端切换会影响 messages 格式吗？

### Q40：OpenAI-compatible messages 如何转换？

标准回答：

内部 messages 接近 Anthropic 结构：

- assistant content list 里有 text/tool_use。
- user content list 里有 tool_result。

发送 OpenAI-compatible 时转换为：

- system message
- assistant `tool_calls`
- tool role message
- user text message

追问方向：

- tool_call_id 为什么重要？
- OpenAI 的 tool role 和 Anthropic tool_result 有什么区别？
- 多 tool call 如何保持顺序？

### Q41：session persistence 如何实现？

标准回答：

v6 自动保存到：

```text
.mini_claude/sessions/{session_id}.json
```

保存内容：

- messages
- token usage
- todos
- loaded skills
- read_file_state
- permission mode

CLI 支持：

```bash
python3 v6_full_agent.py --session demo --resume
```

追问方向：

- 为什么 read_file_state 也要保存？
- resume 后压缩状态怎么处理？
- session 文件会不会泄露敏感信息？

### Q42：cost budget 如何实现？

标准回答：

`TokenUsage` 记录 input/output tokens。`estimated_cost` 根据每百万 token 单价估算费用。

可配置：

- `MINI_CLAUDE_MAX_COST`
- `MINI_CLAUDE_INPUT_PER_MTOK`
- `MINI_CLAUDE_OUTPUT_PER_MTOK`

每轮调用前检查预算，超过就停止。

追问方向：

- 为什么是调用前检查？
- 不同模型价格如何维护？
- subagent token 如何计入总成本？

### Q43：测试覆盖了哪些能力？

标准回答：

离线测试 `tests/run_v6_offline_tests.py` 覆盖：

- Anthropic `content_block_stop` 工具块组装。
- MCP stdio discovery/call。
- read-before-edit。
- edit diff。
- 大结果落盘压缩。
- session save/load。
- 危险 shell segment 检测。

真实 DashScope 测过：

- OpenAI-compatible streaming tool calling。
- semantic sideQuery memory recall。

追问方向：

- 为什么 Anthropic 没真测？
- 如何 mock streaming events？
- 为什么需要无 API key 测试？

## 第九部分：综合与答辩

### Q44：项目中你最想强调的技术点是什么？

标准回答：

我会强调三点：

1. Agent Loop 抽象：模型、工具、上下文闭环。
2. 工程安全：read-before-edit、mtime、权限、diff。
3. 上下文治理：压缩、记忆、subagent、session。

这些组合起来，才从 chatbot 变成 coding agent。

追问方向：

- 哪个点最难？
- 哪个点最接近 Claude Code？
- 哪个点最有工程价值？

### Q45：最难实现的部分是什么？

标准回答：

最难的是 streaming tool calling 和上下文治理。

Streaming 难在不同后端事件结构不同：

- Anthropic 要等 `content_block_stop` 才能解析 JSON。
- OpenAI/DashScope 要从 SSE delta 中拼 tool_calls。

上下文治理难在不能粗暴截断，需要兼顾：

- 可追溯
- 成本
- 最近上下文
- 消息结构合法

追问方向：

- 如果 streaming 中断怎么办？
- JSON 拼接失败怎么办？
- 摘要压缩是否会破坏上下文？

### Q46：如果面试官问“你和 Claude Code 的区别是什么”怎么答？

标准回答：

Claude Code 是生产级系统，包含更完整的权限、安全沙箱、UI、工具生态、复杂压缩和长期维护。我的项目是核心机制复现：

- 用 v0-v4 讲清原理。
- 用 v5/v6 做到可运行的工程机制。
- 重点是理解和复现关键设计，而不是替代 Claude Code。

追问方向：

- 哪些地方比 Claude Code 简化？
- 哪些机制是自己实现的？
- 为什么这个项目仍然有价值？

### Q47：这个项目体现了哪些工程能力？

标准回答：

体现了：

- 大系统拆解能力：把复杂 agent 拆成 v0-v6。
- API 抽象能力：多后端统一成 `ModelResult`。
- 安全意识：文件编辑和 shell 权限。
- 异步/协议能力：MCP JSON-RPC stdio。
- 测试意识：离线模拟 streaming + 真后端回归。
- 成本意识：token usage 和 cost budget。

追问方向：

- 如何证明这些能力不是纸面设计？
- 哪些测试是真实跑过的？
- 后续如何演进成生产项目？

### Q48：如何现场演示？

建议演示顺序：

1. 跑离线测试：

```bash
python3 tests/run_v6_offline_tests.py
```

2. 展示 help：

```bash
python3 v6_full_agent.py --help
```

3. DashScope 运行：

```bash
export MINI_CLAUDE_BACKEND=openai
export DASHSCOPE_API_KEY=sk-xxx
export MODEL_NAME=qwen-turbo
export MINI_CLAUDE_STREAM=1
python3 v6_full_agent.py --session demo --resume
```

4. 让模型调用 `show_state`，展示：

- backend
- streaming
- tools
- mcp
- tokens
- estimated_cost

追问方向：

- 如果没有网络怎么演示？
- 如果 API 失败怎么办？
- 如何展示 Anthropic `content_block_stop`？

### Q49：一句话总结这个项目

标准回答：

Mini Claude Code 是一个从最小 bash agent 递进到 v6 完整面试版的 coding agent 复现项目，它用可运行代码展示了 Agent Loop、工具调用、规划、子代理、Skills、文件安全、权限、压缩、记忆、MCP、双后端 streaming、会话恢复和成本预算这些核心机制。

## 快速背诵版

如果时间很短，可以只背这段：

> 我的 Mini Claude Code 项目分成 v0-v6。v0-v4 是教学链路：bash agent、四工具 agent、Todo、Sub-agent、Skills。v5/v6 是面试增强：加入 read-before-edit、mtime、diff、权限模式、上下文压缩、semantic sideQuery、MCP、DashScope/OpenAI-compatible streaming、Anthropic streaming 事件解析、session resume 和 cost budget。核心思想是模型本身负责决策，代码提供工具、上下文、安全和执行闭环。项目不是 Claude Code 的生产级完整替代，而是核心机制可运行、可测试、可追源码的 Python 复现。

## 简历追问的 STAR 段落回答

下面这些回答按 STAR 法则组织，但不写成生硬的 S/T/A/R 列表，面试时可以直接按段落讲。

### 1. 请介绍一下你的 Mini Claude Code 项目

这个项目的背景是我想系统理解 Claude Code、Cursor Agent 这类 Coding Agent 的核心架构，而不是只停留在调用 LLM API 的层面。普通 Chatbot 是“用户输入到模型输出”，但 Coding Agent 的关键是模型能持续调用工具、观察结果并再次决策。我的目标是基于 Python 复现这套核心闭环，并在最终版本补充真实 Agent 系统会遇到的工程问题，比如上下文膨胀、代码编辑安全、子任务隔离、MCP 工具扩展和会话恢复。

具体实现上，我按 v0 到 v6 渐进式拆解：先用最小 bash agent 跑通工具调用，再加入文件工具、Todo、Sub-agent、Skills，最后在 v5/v6 中实现压缩、权限、MCP、双后端 streaming 和 session resume。最终结果是一个可运行、可测试、可追源码的 Claude Code 类 Agent 学习与面试版。这里我会主动说明，它不是替代生产级 Claude Code，而是把核心机制拆出来并做成可验证实现。

### 2. 这个项目和普通 LLM 应用有什么区别？

我做这个项目时，最核心的问题是区分“LLM 应用”和“Agent 系统”。普通 LLM 应用通常是一次输入、一次输出，而 Coding Agent 需要形成执行闭环：模型先根据上下文决定是否调用工具，程序执行工具后把结果作为 Observation 写回 messages，再让模型继续决策。这个闭环会带来普通 Chatbot 不需要处理的问题，包括工具结果管理、文件状态追踪、权限控制、长上下文压缩和会话恢复。

实现上，我设计了统一的 Agent Loop，把模型输出解析成 tool calls，执行文件读写、代码搜索、命令执行等工具，再把 tool result 回写到下一轮上下文。这样模型从“回答者”变成“决策者”，代码负责工具执行、上下文管理和安全边界。最终项目能支撑多轮代码任务，也能展示 Agent 系统和普通 API wrapper 的本质区别。

### 3. 为什么要做 4 层上下文压缩？

在 Coding Agent 长任务里，一个很现实的问题是工具结果会快速撑爆上下文窗口。比如 grep 大量文件、读取长代码、运行测试产生长日志，如果不治理，token 成本、响应延迟和模型注意力都会恶化，甚至无法继续调用模型。所以我设计了 4 层上下文压缩策略，目标不是简单截断，而是在成本、可追溯性和最近上下文之间做平衡。

具体做法是：第一层把大工具结果落盘到 `.mini_claude/context/`，上下文里只保留路径和头尾预览；第二层把旧 tool result 替换成 snip 标记；第三层保留最近几个工具结果，因为最近 Observation 对下一步决策最重要；第四层在超阈值后调用 LLM 把旧 messages 摘成 `<context-summary>`，同时保持 user/assistant 消息结构合法。这个机制让长任务可以继续推进，也保留了必要的追溯路径，体现的是 Agent 系统里的上下文治理能力。

### 4. 文件安全机制为什么重要？

Coding Agent 和普通问答最大的区别之一是它会真的修改文件、执行命令。如果没有安全机制，模型可能基于旧上下文覆盖用户改动，或者因为 old_text 太短误替换代码。我的目标是让自动代码编辑更可靠，而不是只让模型“能写文件”。

实现上，我做了 read-before-edit，要求修改已有文件前必须先读取；读取时记录 mtime，编辑前检查文件是否被外部改过，避免 stale edit；`edit_file` 会检查 old_text 是否唯一，避免误替换；修改成功后返回 unified diff，让用户和模型都能看到具体变更。对于 shell，我用危险命令正则和简单 segment 解析拦截 `sudo`、`rm -rf /`、`git reset --hard` 等高风险操作。结果是项目具备一层学习/面试级安全防护。生产环境还需要容器沙箱、AST 级 shell 分析和更严格的权限审批，这一点我会主动说明。

### 5. Sub-agent 和 Skills 分别解决什么问题？

我引入 Sub-agent 和 Skills 是为了解决两个不同问题。Sub-agent 主要解决上下文污染：主 Agent 做实现任务前，可能需要先探索很多文件，如果所有中间结果都进入主上下文，会干扰后续决策。因此我实现了 `Task` 工具，为 explore、plan、code 等子代理创建独立 Agent 实例，使用独立 messages 和工具白名单，最后只把摘要返回给主 Agent。

Skills 解决的是领域知识按需注入问题。比如 PDF 处理、MCP 构建、代码审查等任务不适合全部塞进 system prompt，否则初始上下文和成本都会上升。所以我通过 `SKILL.md` 做 progressive disclosure：系统提示里只放 skill 名称和描述，真正需要时才加载完整内容。这样 Sub-agent 提升任务隔离能力，Skills 提升领域泛化能力，两者分别解决“怎么拆任务”和“怎么注入专业流程”。

### 6. MCP 和双后端 streaming 怎么讲？

在最终版里，我希望 Agent 不只依赖内置工具，而是能接入外部工具生态，所以实现了一个最小 MCP client。它从配置文件读取 MCP server，通过 JSON-RPC over stdio 完成 `initialize`、`tools/list` 和 `tools/call`，并把外部工具映射成 `mcp__server__tool` 的命名格式，避免和内置工具冲突，也方便按 server 路由。

双后端方面，我把 Anthropic 和 OpenAI-compatible/DashScope 的响应统一抽象成内部 `ModelResult`，主循环只处理 text 和 tool_use，不关心底层后端差异。Anthropic streaming 侧重点是处理 `content_block_start/delta/stop`，在 `content_block_stop` 后解析完整工具 JSON；OpenAI-compatible 则通过 SSE delta 累积 tool call arguments。这样后端适配被隔离在模型调用层，Agent Loop 本身保持稳定。

### 7. 这个项目最难的地方是什么？

最难的不是写工具函数，而是处理 Agent 系统里的状态一致性。比如 streaming tool call 不是一次性返回完整 JSON，而是跨 chunk 累积，如果在 delta 阶段解析就会触发 JSONDecodeError，所以必须等 block stop 后再解析。再比如压缩不能随便删 messages，因为模型 API 对 user/assistant 结构有要求；文件编辑也不能只靠字符串替换，因为会遇到旧内容重复、文件被外部修改等问题。

我的处理方式是把这些问题拆成几个机制：`AnthropicStreamAssembler` 负责工具块组装，compression pipeline 负责上下文治理，`Workspace` 负责读写安全，`PermissionManager` 负责权限控制，`McpConnection` 负责外部工具协议适配。最终这些模块一起保证 Agent Loop 能比较稳定地跑长任务。这个回答的重点是：Agent 难点不是“调模型”，而是模型调用工具后的状态、安全和上下文一致性。

### 8. 如果重新设计会怎么改？

如果重新设计，我会做三类改进。第一是模块化，现在 v6 为了教学可读性保留成单文件，但生产化应该拆成 `agent.py`、`tools.py`、`memory.py`、`mcp_client.py`、`compression.py`，降低耦合，也方便单元测试。第二是安全增强，现在危险命令检测主要靠正则和简单 shell segment 解析，生产版应该引入容器沙箱、命令 AST 分析、权限审批和文件系统隔离。

第三是上下文和记忆系统升级。当前 memory 主要是文件候选加 sideQuery，后续可以引入 embedding index、长期记忆索引和原始历史/压缩历史双轨存储。这样既保留当前项目作为学习实现的简洁性，也能说明我知道它距离生产级 Agent 还差哪些工程环节。

### 9. 如果面试官问 GitHub 历史或“从零实现”怎么答？

这个问题要正面回答，不要硬说完整从零。我会说：这个仓库保留了 Mini Claude Code 的教学主线，我的重点是基于这条主线做复现理解和面试版扩展，尤其是 v5/v6 的工程机制，包括文件安全、上下文压缩、MCP、双后端 streaming、session resume 和离线测试。我在简历里更准确的表述是“基于 Python 复现并扩展 Claude Code 类 Agent 核心机制”，而不是“完整复刻 Claude Code 生产系统”。

这样回答的好处是把边界讲清楚，同时把价值落在可验证的工作上：代码能运行，测试能跑，关键机制能追源码，面试时能解释为什么这些机制是 Coding Agent 区别于普通 LLM 应用的核心。

## 阿里 AI 研发面试官视角高频问答库

这一部分按阿里 AI 研发 / Agent 算法工程面试的常见追问方式整理。重点不是背名词，而是把问题讲成“业务/系统痛点 - 技术方案 - 工程取舍 - 可验证结果”。

### 一、项目整体与定位

#### Q1：你这个 Mini Claude Code 项目到底解决了什么问题？

推荐回答：

这个项目解决的是 Coding Agent 从“简单调用 LLM API”到“可持续执行代码任务”的系统化问题。普通 LLM 应用只做输入到输出，但 Coding Agent 需要让模型能决策工具调用、执行工具、观察结果并继续推理。我做这个项目的背景是想拆解 Claude Code 类系统的核心机制，所以基于 Python 复现并扩展了 ReAct 式 Agent Loop，并逐步加入文件操作、Todo 规划、Sub-agent、Skills、上下文压缩、文件安全、MCP 和双后端 streaming。最终结果不是替代生产级 Claude Code，而是把核心机制做成可运行、可测试、可讲清楚的面试版。

#### Q2：这个项目和普通 Chatbot 最大区别是什么？

推荐回答：

最大区别是闭环。Chatbot 是用户输入后模型直接输出，而 Coding Agent 是模型先判断是否需要调用工具，工具执行后把结果作为 Observation 回写上下文，再让模型继续决策。这个循环会带来很多普通 Chatbot 没有的问题，比如工具结果过大、文件被误改、命令执行风险、session 恢复、子任务隔离等。我这个项目的重点就是围绕这些问题设计 Agent Loop、上下文压缩、文件安全和工具扩展机制。

#### Q3：为什么你把项目设计成 v0 到 v6，而不是直接写最终版？

推荐回答：

我刻意做成渐进式版本，是为了体现系统拆解能力。v0 用单 bash 工具证明 Agent 的最小闭环，v1 拆出文件读写工具，v2 加 Todo 解决长任务规划，v3 加 Sub-agent 解决上下文污染，v4 加 Skills 解决领域知识按需注入，v5/v6 再补文件安全、压缩、MCP、双后端 streaming 和 session。这样设计的结果是每一层都能解释“为什么需要它”，而不是直接堆功能。

#### Q4：你觉得这个项目最核心的技术价值是什么？

推荐回答：

我认为核心价值是把 Coding Agent 的关键工程问题拆清楚了：第一是 ReAct 式执行闭环，让模型从回答者变成决策者；第二是长上下文治理，解决工具结果不断累积后的成本和注意力问题；第三是代码编辑安全，解决自动化修改文件时的 stale edit、误替换和危险命令问题；第四是工具生态扩展，通过 Skills 和 MCP 让 Agent 能动态获得流程知识和外部工具。这个项目的价值不是功能数量，而是围绕 Agent 长任务执行的核心痛点做了系统化实现。

### 二、Agent Loop 与 ReAct

#### Q5：你说实现了 ReAct 式 Agent Loop，具体 ReAct 体现在哪里？

推荐回答：

ReAct 的核心是 Reason + Act。在这个项目里，Reason 是模型根据当前 messages 判断下一步，Act 是模型发起 tool call，Observation 是工具执行结果被写回 messages，然后下一轮继续决策。我没有强制模型输出详细思维链，而是让工具调用和工具结果构成可观察的推理轨迹。这样既符合真实 Agent 的工作方式，也避免把大量 CoT 暴露在上下文里。

#### Q6：Agent Loop 的退出条件是什么？如果模型一直调用工具怎么办？

推荐回答：

正常退出条件是模型不再返回 tool call，也就是认为任务完成。工程上还需要额外保护，比如 max_turns、cost budget、异常退出和用户中断。我的 v6 里有 max_turns 和 cost budget，防止 runaway agent。生产环境还可以进一步加入重复工具调用检测，比如连续多次调用同一个工具且输入不变，就判定为潜在死循环并让模型总结当前状态或请求用户确认。

#### Q7：为什么 tool result 要作为 user message 回写？

推荐回答：

因为对模型来说，工具结果就是外部环境给它的 Observation。Anthropic 的工具调用协议里，tool_result 本质上会作为下一轮用户侧内容进入 messages。这样模型才能基于真实执行结果继续决策，比如读到文件内容后再编辑、测试失败后再修复。如果不回写，模型就无法知道工具执行结果，Agent Loop 就断了。

#### Q8：Tool schema 的作用是什么？只是 JSON 参数约束吗？

推荐回答：

Tool schema 不只是参数约束，也是行为引导。工具的 name、description、input_schema 会影响模型什么时候选择工具、怎么构造参数、是否理解工具边界。比如 `edit_file` 的描述强调唯一 old_text 和 diff，模型就更倾向于给出精确上下文；`TodoWrite` 的 schema 要求 status 和 activeForm，就能让模型显式维护任务状态。对 Agent 来说，schema 是一种软约束和接口契约。

### 三、Tool Calling 与 Streaming

#### Q9：Anthropic streaming 下 tool call 参数为什么不能边收到边解析？

推荐回答：

因为 Anthropic streaming 的工具参数是 partial_json，它是 JSON 字符串的片段，中间任意一个 chunk 都不保证是合法 JSON。如果在 delta 阶段解析，很容易 JSONDecodeError。正确做法是按 content block 的 index 维护缓冲区，在 `content_block_delta` 阶段只拼接字符串，等 `content_block_stop` 到达后再解析完整 JSON。这个项目里用 `AnthropicStreamAssembler` 做这件事。

#### Q10：OpenAI-compatible / DashScope streaming 和 Anthropic 有什么差异？

推荐回答：

Anthropic 是 content block 事件模型，有 `content_block_start`、`content_block_delta`、`content_block_stop`，所以可以知道单个工具块什么时候结束。OpenAI-compatible 是 SSE delta 模型，tool call 的 name、id、arguments 会分散在多个 delta 里，没有单独的 content_block_stop，所以通常要等 stream 结束后统一组装。我在项目里把两边都转换成统一的 `ModelResult`，让上层 Agent Loop 不关心后端差异。

#### Q11：你这个项目是否真的实现了 streaming 早期执行？

推荐回答：

这里要区分清楚。当前 v6 实现了 Anthropic `content_block_stop` 后工具块完整组装和 ready 回调，也就是早期执行的前置条件；但为了保持教学实现简单，Agent 层仍然是在模型响应收束后统一执行工具。生产级实现可以在 tool block ready 后立即对只读工具创建异步任务，让模型继续输出后续内容时，文件读取或搜索已经并行执行。这个边界我会主动说明，避免把当前实现说成完整生产级早期执行。

#### Q12：为什么要抽象 `ModelResult`？

推荐回答：

因为 Anthropic、Anthropic streaming、OpenAI-compatible 非流式和 OpenAI-compatible streaming 的返回格式都不一样。如果主循环直接处理各家 API 结构，Agent Loop 会和后端强耦合。`ModelResult` 把它们统一成 content、stop_reason 和 usage，主循环只关心 text 和 tool_use。这样后续接入 Gemini 或其他模型时，只需要新增后端适配层，不需要改 Agent Loop。

### 四、上下文压缩与长任务

#### Q13：为什么 Coding Agent 一定需要上下文压缩？

推荐回答：

因为 Coding Agent 每次工具结果都会进入上下文。长任务中读文件、grep、跑测试会产生大量输出，如果不治理，token 成本和延迟会上升，模型注意力也会被旧结果稀释，甚至超过上下文窗口。我的目标不是简单截断，而是保留可追溯信息的同时降低上下文压力，所以设计了大结果落盘、旧结果 snip、保留最近结果和 LLM 摘要压缩四层策略。

#### Q14：为什么大结果要落盘，而不是直接截断？

推荐回答：

直接截断会丢失信息，后续如果模型需要完整日志或完整搜索结果，就无法恢复。落盘的好处是上下文里只保留路径、原始长度和头尾预览，既减少 token，又让完整内容仍然可追溯。模型如果需要，可以再通过 read_file 读取落盘文件。这体现的是 Agent 系统中“压缩上下文”和“保留可恢复信息”的平衡。

#### Q15：为什么要保留最近工具结果？

推荐回答：

最近工具结果通常是模型下一步决策最依赖的信息，比如刚刚读到的函数、刚刚失败的测试、刚刚生成的 diff。如果过早 snip 最近结果，模型可能丢失局部操作上下文。所以我的策略是旧结果可以更激进地压缩，但最近几个 tool result 保持完整。这是基于 Agent 决策的时间局部性做的取舍。

#### Q16：LLM 摘要压缩会不会丢关键信息？

推荐回答：

会有这个风险，所以摘要压缩应该是最后一层，而不是第一层。我的策略是先落盘、snip 旧结果、保留最近 Observation，只有超过更高阈值时才做 LLM summary。摘要 prompt 会要求保留用户目标、约束、读过和改过的文件、关键 diff、错误和未解决风险。生产环境可以进一步保存原始历史和压缩历史两份，做到可恢复和可审计。

### 五、文件安全与权限控制

#### Q17：read-before-edit 解决什么问题？

推荐回答：

它解决的是模型在不了解当前文件真实内容时直接修改文件的问题。Coding Agent 如果不先读文件，可能基于幻觉路径或旧上下文编辑代码。我的实现是在 read_file 时记录文件路径和 mtime，write/edit 已有文件前检查是否读过。如果没有读过，就拒绝修改。这个机制能逼模型先观察真实环境，再执行编辑。

#### Q18：mtime 追踪有什么用？为什么不只靠 read-before-edit？

推荐回答：

read-before-edit 只能保证模型曾经读过文件，但不能保证文件在读取后没有被用户或其他进程改过。mtime 追踪解决的是 stale edit 问题：Agent 读完文件后，如果外部又修改了文件，Agent 再按旧内容编辑就可能覆盖新改动。所以编辑前检查当前 mtime 是否和读取时一致，不一致就要求重新读取。生产环境还可以用文件 hash 或文件锁提高可靠性。

#### Q19：old_text 唯一性检查为什么重要？

推荐回答：

如果 old_text 在文件里出现多次，直接 replace 第一个匹配很容易误改。比如多个函数都有相似代码片段，模型给的 old_text 太短，就可能改错位置。我的 edit_file 会检查归一化后的 old_text 出现次数，如果多于一次就拒绝，并要求提供更多上下文。这个机制本质上是用约束换可靠性。

#### Q20：危险 shell 检测是不是足够安全？

推荐回答：

不够。当前实现是学习/面试级防护，主要通过正则和简单 shell segment 解析拦截 `sudo`、`rm -rf /`、`git reset --hard` 等明显危险命令。它能覆盖常见风险，但不是生产级沙箱，因为 shell 语法非常复杂，可以通过变量、子 shell、重定向等方式绕过。生产环境应该用容器沙箱、文件系统隔离、命令 allowlist、AST 级解析和人工审批机制。

#### Q21：plan/default/acceptEdits/bypassPermissions/dontAsk 这些权限模式怎么理解？

推荐回答：

这些模式本质上是不同信任级别下的工具策略。plan 模式禁止写文件和 shell 等 mutating tools，只允许读和分析；default 允许常规操作但拦截危险 shell；acceptEdits 更偏向允许文件编辑；bypassPermissions 用于可信子代理或测试，但风险最高；dontAsk 更保守，会阻断写操作和 shell。这个设计体现的是 Agent 在不同任务阶段应该有不同权限边界。

### 六、Sub-agent 与 Skills

#### Q22：Sub-agent 解决什么问题？

推荐回答：

Sub-agent 主要解决上下文污染。主 Agent 如果为了一个实现任务先探索几十个文件，所有中间结果都会进入主上下文，影响后续决策。Sub-agent 的设计是 fork 一个独立 Agent，用自己的 messages 和工具白名单完成探索或规划，最后只把摘要返回主 Agent。这样主 Agent 拿到的是压缩后的结论，而不是大量原始噪声。

#### Q23：explore、plan、code subagent 有什么区别？

推荐回答：

区别主要在工具权限和 system prompt。explore 偏搜索和读文件，不允许修改；plan 偏方案分析，也保持只读；code 可以执行实现类任务，但为了避免递归失控，不给它继续创建 Task 的能力。这样做既是安全限制，也是行为引导，让不同子代理专注不同阶段。

#### Q24：Skills 和工具有什么区别？

推荐回答：

工具是模型“能做什么”，Skills 是模型“应该怎么做”。比如 read_file 是工具，但 PDF 处理流程、MCP 构建规范、代码审查 checklist 是技能。Skills 通过 `SKILL.md` 存储领域流程，系统提示里只放描述，真正匹配任务时再加载完整内容。这是一种 progressive disclosure，能减少初始上下文，也能让知识可维护。

### 七、MCP 与工具生态

#### Q25：MCP 在项目里解决什么问题？

推荐回答：

MCP 解决的是 Agent 工具体系扩展问题。如果所有工具都写死在 Agent 里，扩展成本高，而且和外部系统集成不灵活。MCP 通过 JSON-RPC over stdio 让外部 server 提供工具，Agent 可以动态发现 tools/list，再通过 tools/call 调用。我的实现把 MCP 工具映射为 `mcp__server__tool`，既避免命名冲突，也方便路由。

#### Q26：为什么用 JSON-RPC over stdio，而不是 HTTP？

推荐回答：

stdio 的好处是简单、进程级隔离、无需端口管理，也和 Claude Code / MCP 生态一致。JSON-RPC 提供 request id，适合处理异步请求和响应匹配。HTTP 更适合远程服务和长期服务化场景，但本地 Agent 调本地工具时，stdio 更轻量。我的项目里 `McpConnection` 用 pending future 根据 request id 匹配响应。

#### Q27：MCP 工具为什么要用 `mcp__server__tool` 前缀？

推荐回答：

这个前缀主要解决命名冲突和路由问题。不同 MCP server 可能都有 search、read_file 这类同名工具，也可能和内置工具重名。用 `mcp__server__tool` 后，Agent 可以通过前缀判断这是 MCP 工具，再解析 server name 和 tool name，把调用路由到正确的 server。这样工具列表是扁平的，但路由信息仍然保留。

### 八、测试与评估

#### Q28：你如何证明这个项目不是纸面设计？

推荐回答：

我做了离线测试来覆盖核心机制，不依赖真实 API key。测试包括 Anthropic `content_block_stop` 工具块组装、MCP stdio discovery/call、read-before-edit、edit diff、大结果落盘压缩、session save/load 和危险 shell segment 检测。这样即使没有网络，也能证明关键逻辑是可运行的。DashScope / OpenAI-compatible streaming 可以作为真实后端演示，但面试时离线测试更稳定。

#### Q29：如果要评估一个 Coding Agent，你会看哪些指标？

推荐回答：

我会分四类指标。第一是任务成功率，比如代码修改后测试是否通过；第二是工具调用效率，比如平均 tool calls、重复调用率、无效调用率；第三是上下文和成本，比如 token 消耗、压缩触发次数、恢复后是否能继续；第四是安全性，比如是否发生未读先改、stale edit、危险命令执行。这个项目目前主要验证机制正确性，后续如果生产化，需要接入 benchmark 和任务级自动评测。

#### Q30：离线测试为什么重要？

推荐回答：

Agent 项目很容易依赖真实 LLM API，但真实 API 有网络、价格、模型随机性和 key 权限问题。如果所有验证都依赖在线模型，面试现场或 CI 环境很不稳定。离线测试的价值是把协议解析、MCP 调用、文件安全、压缩和 session 这些确定性逻辑先固定住。这样即使没有 API key，也能证明核心工程机制不是纸面设计。

### 九、项目边界与生产化

#### Q31：你的项目和 Claude Code 差距在哪里？

推荐回答：

差距主要在生产化层面。Claude Code 有更完整的权限系统、安全沙箱、终端 UI、工具生态、异常恢复、真实并发和长期维护。我这个项目是核心机制复现和面试版实现，重点是解释 Agent Loop、文件安全、压缩、Sub-agent、Skills、MCP 和双后端 streaming 的设计。它的价值不是替代 Claude Code，而是让我能从原理和工程角度讲清楚 Coding Agent 怎么工作。

#### Q32：GitHub 上看起来有原项目历史，你哪些是自己做的？

推荐回答：

这个问题我会直接说明：仓库保留了 Mini Claude Code 的教学主线，我重点做的是基于这条主线进行复现理解和面试版扩展，尤其是 v5/v6 的工程机制，包括文件安全、上下文压缩、MCP、双后端 streaming、session resume 和离线测试。我在简历里更准确的表述是“基于 Python 复现并扩展 Claude Code 类 Agent 核心机制”，不是声称完整从零复刻 Claude Code 生产系统。

#### Q33：如果让你把这个项目生产化，你优先做什么？

推荐回答：

我会优先做三件事。第一是模块化，把 v6 单文件拆成 agent、tools、memory、mcp、compression 等模块，提升可维护性。第二是安全沙箱，把 shell 和文件写入放到容器或受限文件系统里，配合 allowlist 和人工确认。第三是评测体系，构建一组 coding tasks，统计成功率、工具调用效率、token 成本和安全违规率。这样项目才能从面试版走向工程可用版。

#### Q34：如果公司要做企业级 Coding Agent，你会怎么设计整体架构？

推荐回答：

我会把系统拆成五层：第一层是模型适配层，统一不同模型和 streaming tool call；第二层是 Agent Runtime，维护 Agent Loop、任务状态、预算和中断恢复；第三层是 Tool Runtime，负责工具注册、权限、沙箱和审计；第四层是 Context/Memory 层，负责短期上下文压缩、长期记忆和检索；第五层是评测与观测层，记录工具调用轨迹、成功率、成本和安全事件。Mini Claude Code 对应的是这些层的最小可运行版，生产系统需要进一步工程化。

### 十、最建议重点背的 5 个问题

1. 这个项目和普通 LLM 应用有什么区别？
2. 为什么需要 4 层上下文压缩？
3. read-before-edit / mtime / diff 分别解决什么风险？
4. Sub-agent 和 Skills 的区别是什么？
5. MCP + 双后端 streaming 是怎么抽象到同一个 Agent Loop 的？

这 5 个答好，面试官基本会认为你不是只会调 API，而是理解 Agent 系统的关键工程问题。

## 简历项目面试准备优先级（面试官视角）

这一节专门用于简历项目准备。真实面试里，面试官通常不会先看完整代码，而是根据简历里的关键词追问：`Claude Code 类 Coding Agent`、`ReAct Agent Loop`、`上下文压缩`、`read-before-edit`、`Sub-agent`、`Skills`、`MCP`、`streaming`、`offline tests`。所以准备顺序不能按代码文件顺序背，而要按“简历关键词 -> 面试官为什么会问 -> 高分回答必须证明什么 -> 可能继续追问什么”来准备。

### 一、面试官会怎么从简历生成问题

面试官看到“Claude Code 类 Coding Agent”，第一反应不是问你写了多少行代码，而是判断你是否理解 Agent 和普通 LLM 应用的区别。因此他大概率会先问：这个项目解决什么问题？为什么它不是一个 Chatbot？Agent Loop 里的状态怎么流转？

面试官看到“4 层上下文压缩”，会继续判断你有没有做过长任务 Agent。他会问：为什么需要压缩？为什么不是直接截断？最近 Observation 为什么要保留？LLM summary 会不会丢信息？压缩后怎么恢复？

面试官看到“read-before-edit、mtime、old_text、unified diff”，会判断你是否理解自动代码编辑的工程风险。他会问：模型为什么不能直接改文件？mtime 和 hash 有什么差别？old_text 多处匹配怎么办？危险 shell 检测是不是足够安全？

面试官看到“MCP、双后端 streaming、ModelResult”，会判断你是否理解协议和抽象层。他会问：MCP 为什么不是普通函数调用？JSON-RPC stdio 怎么做工具发现？Anthropic streaming 和 OpenAI-compatible streaming 差异是什么？为什么要统一成 `ModelResult`？

面试官看到“离线测试覆盖”，会判断项目是不是只停留在口头设计。他会问：不依赖真实 API key 怎么验证？测试覆盖哪些核心路径？还有哪些没有覆盖？

### 二、准备优先级总表

| 优先级 | 必须准备的问题 | 为什么最可能问 | 高分回答要证明什么 |
| --- | --- | --- | --- |
| P0 | 1 分钟介绍这个项目 | 所有项目面都会从这里开始 | 能把项目定性为 Coding Agent Runtime，而不是工具合集 |
| P0 | Agent 和普通 Chatbot 的区别 | 简历写了 ReAct / Tool Calling，必追 | 能讲清模型决策、工具执行、Observation 回写的闭环 |
| P0 | 4 层上下文压缩怎么设计 | 这是最像 Agent 长任务的亮点 | 能讲清 token、信息保留、最近结果、summary 的取舍 |
| P0 | 自动代码编辑安全怎么做 | Coding Agent 项目最核心的工程风险 | 能讲清 read-before-edit、mtime、old_text、diff 分别防什么 |
| P0 | MCP + streaming + ModelResult 怎么抽象 | 简历里最像工程深度的协议点 | 能讲清外部工具协议、流式 tool call 组装、后端统一 |
| P0 | 这个项目和 Claude Code 的差距 | 面试官会防止候选人夸大项目 | 能主动讲边界，说明是核心机制复现和工程化增强 |
| P1 | Sub-agent 和 Skills 区别 | 简历写了两个概念，容易被混淆追问 | 能区分任务隔离和知识按需注入 |
| P1 | session resume / cost budget | 长任务 Agent 必备状态管理 | 能讲清 messages、usage、权限、文件读取状态为什么要保存 |
| P1 | 权限模式和危险 shell 检测 | 安全意识加分项 | 能承认当前不是生产级沙箱，并给生产化方案 |
| P1 | 离线测试怎么证明项目可运行 | 面试官看不到代码时最需要证据 | 能说出测试覆盖路径，而不是泛泛说“我测试过” |
| P2 | semantic sideQuery / memory candidates | 可作为扩展亮点 | 能讲清检索式上下文供给，但别当主线 |
| P2 | OpenAI-compatible message 转换细节 | 只有面试官深入协议才会问 | 能说明不同模型 API 的 tool call 格式差异 |
| P2 | v0-v6 每个版本的递进 | 可用于证明学习和拆解能力 | 能讲清每一版为什么增加一个机制 |

准备时先把 P0 背熟，再准备 P1。P2 只用于加分，不要在开场主动展开太多。

### 三、P0 必备问题准备卡

#### P0-1：请你介绍一下这个项目

为什么会问：这是项目面开场题。面试官用它判断你是否能抓住项目本质。如果你一上来只罗列“文件读写、命令执行、Todo”，项目会显得像功能堆砌。

高分回答必须包含：项目定位、核心问题、关键方案、验证结果。建议用一句话先定性：这是一个轻量级 Coding Agent Runtime，而不是普通 Chatbot。然后再说它通过 ReAct Agent Loop 实现模型决策、Tool Calling、工具执行和 Observation 回写，并围绕长任务补了上下文压缩、文件安全、Sub-agent、Skills、MCP、streaming 和 session resume。

推荐回答：

这个项目是我基于 Python 复现并扩展的 Claude Code 类 Coding Agent 核心机制。它不是一个普通 Chatbot，而是一个轻量级 Coding Agent Runtime，核心是构建“模型决策 - Tool Calling - 工具执行 - Observation 回写”的 ReAct 闭环。围绕这个闭环，我进一步补了长任务场景里比较关键的工程能力，包括 4 层上下文压缩、read-before-edit 和 mtime 文件安全机制、Sub-agent 任务隔离、Skills 按需知识注入、MCP JSON-RPC stdio 工具接入，以及 Anthropic / OpenAI-compatible 双后端 streaming 抽象。最后通过离线测试覆盖 streaming tool assembly、MCP 调用、文件安全、上下文压缩和 session 恢复，证明这些机制不是只停留在设计层面。

可能追问：为什么这叫 Agent？为什么不是普通 LLM 应用？哪一部分最难？你自己主要做了哪些增强？

#### P0-2：Agent Loop 具体怎么跑？

为什么会问：简历里写了 ReAct 和 Tool Calling，面试官一定会验证你是否真正理解闭环，而不是只知道名词。

高分回答必须包含：用户输入进入 messages，模型返回 assistant message 和 tool_use，Agent 执行工具，tool_result 作为 Observation 回写 messages，模型继续下一轮决策，直到没有 tool call 或达到 max_turns / budget。回答里要突出“状态流转”，不要只说“调用工具”。

推荐回答：

Agent Loop 的核心是让模型从“直接回答者”变成“任务决策者”。用户请求进入 messages 后，模型先基于当前上下文判断是否需要调用工具，如果需要，就返回带有 tool_use 的 assistant message。Agent Runtime 解析 tool_use，执行对应工具，比如读文件、搜索代码、运行命令或调用 MCP 工具。工具执行结果会作为 tool_result，也就是 Observation，回写到下一轮 messages 里。模型再根据新的 Observation 继续判断下一步，直到不再产生 tool call，或者触发 max_turns、cost budget 等停止条件。这个闭环就是 ReAct 在 Coding Agent 里的工程化形态。

可能追问：tool result 为什么作为 user 侧消息回写？如果模型一直调用工具怎么办？工具失败怎么处理？schema 对模型行为有什么影响？

#### P0-3：为什么需要 4 层上下文压缩？

为什么会问：上下文治理是 Coding Agent 区别于简单 demo 的关键。长任务里读文件、搜索、测试都会产生大量工具结果，不压缩就会带来 token 成本、延迟和信息污染。

高分回答必须包含：大结果落盘是为了可恢复，旧结果 snip 是为了降低噪声，最近 Observation 保留是为了保证下一步决策质量，LLM summary 是最后兜底，压缩目标不是简单变短，而是在成本、可恢复性和模型注意力之间做取舍。

推荐回答：

Coding Agent 的上下文膨胀主要来自工具结果，比如代码搜索、文件读取、测试日志和命令输出。如果这些内容全部长期留在 messages 里，token 成本和延迟会上升，模型注意力也会被旧信息污染。我这里不是简单截断，而是做了 4 层压缩：第一层是大工具结果落盘，上下文里保留路径、长度和预览，保证后续还能恢复完整信息；第二层是旧结果 snip，把很早的 Observation 缩短，降低噪声；第三层是最近结果保留，因为最近的文件内容或测试错误通常直接影响下一步决策；第四层是 LLM 摘要压缩，在上下文压力更高时把用户目标、约束、读写文件、关键错误和未完成事项总结出来。这个设计的核心取舍是：既要降 token，又不能让 Agent 丢失任务状态。

可能追问：为什么不能直接截断？summary 会不会丢信息？压缩后如何 resume？有没有压缩效果指标？没有指标时要回答当前重点是机制正确性，后续用 benchmark 评估 token、成功率和恢复率，不能编数字。

#### P0-4：自动代码编辑的可靠性怎么保证？

为什么会问：Coding Agent 会自动改代码，面试官最关心误改、覆盖用户改动和高风险命令。

高分回答必须包含：`read-before-edit` 防止模型没观察真实文件就修改，`mtime` 防止文件被外部改动后 stale edit，`old_text` 唯一性检查防止误替换，`unified diff` 让修改可审计，危险 shell 检测降低高风险命令执行风险。

推荐回答：

自动代码编辑最大的风险是模型基于旧上下文或幻觉去改文件，所以我做了几层保护。第一是 read-before-edit，要求修改已有文件前必须先读这个文件，确保模型观察过真实内容。第二是 mtime 追踪，读取文件时记录修改时间，编辑前再检查当前 mtime 是否一致，避免用户或其他进程改过文件后 Agent 继续用旧内容覆盖。第三是 old_text 唯一性检查，如果要替换的文本在文件里出现多次，就拒绝修改，要求提供更精确上下文，避免误替换。第四是 unified diff，修改后返回差异，让用户和模型都能审计具体改了什么。对于 shell，我也做了危险命令检测，用来拦截常见高风险命令。这里我会强调它是学习/面试级防护，生产环境还需要容器沙箱、命令 allowlist、权限审批和审计日志。

可能追问：mtime 和 hash 哪个更稳？old_text 出现多次怎么办？危险 shell 检测能不能绕过？生产环境怎么做？这里一定要承认当前是学习/面试级防护，生产级要容器沙箱、权限隔离、allowlist、审计和人工审批。

#### P0-5：MCP、streaming 和 ModelResult 解决了什么？

为什么会问：这是简历里最能体现协议理解和工程抽象的部分。面试官会用它判断你是不是只会写本地函数。

高分回答必须包含：MCP 用 JSON-RPC over stdio 做外部工具发现和调用，`tools/list` 发现工具，`tools/call` 执行工具，工具映射成 `mcp__server__tool` 避免命名冲突。Anthropic streaming 是 content block 事件模型，tool 参数是 partial_json，需要在 `content_block_stop` 后解析；OpenAI-compatible streaming 是 SSE delta，需要累积 arguments。`ModelResult` 把不同后端统一成 content、stop_reason、usage，让 Agent Loop 不关心底层 API。

推荐回答：

MCP 解决的是 Agent 的外部工具生态问题。如果所有工具都写死在本地，扩展成本很高；MCP 通过 JSON-RPC over stdio 让外部 server 提供工具，Agent 可以通过 `tools/list` 动态发现工具，再通过 `tools/call` 调用。我把 MCP 工具映射成 `mcp__server__tool`，这样既能避免不同 server 或内置工具重名，也能在调用时根据前缀路由到正确连接。streaming 这块主要解决不同模型协议差异：Anthropic 是 content block 事件模型，工具参数以 partial_json 片段流式返回，必须等 `content_block_stop` 后才能解析完整 JSON；OpenAI-compatible / DashScope 是 SSE delta，需要按 tool call index 累积 name、id 和 arguments。为了让上层 Agent Loop 不关心这些差异，我把不同后端统一成内部 `ModelResult`，里面只暴露 content、stop_reason 和 usage。

可能追问：为什么用 stdio 而不是 HTTP？MCP 工具怎么路由？partial_json 为什么不能边收边 parse？当前是否实现真正早期执行？回答边界要稳：当前实现了工具块组装和 ready 前置条件，Agent 层仍偏教学实现，生产级可扩展异步提前执行。

#### P0-6：你和 Claude Code 的差距是什么？

为什么会问：面试官会防止项目描述夸大，也会看你是否有工程边界感。

高分回答必须包含：这是核心机制复现和工程化增强，不是完整生产级 Claude Code。差距在安全沙箱、权限系统、真实并发调度、长期记忆、终端 UI、企业级审计、工具生态规模和评测体系。你的价值是把核心链路做成可运行、可测试、可解释的最小系统。

推荐回答：

我不会把这个项目说成完整生产级 Claude Code。更准确的定位是：它复现并扩展了 Claude Code 类 Coding Agent 的核心机制，重点是 Agent Loop、工具调用、上下文压缩、文件安全、Sub-agent、Skills、MCP 和 streaming 抽象。和真正生产级 Claude Code 相比，它还缺少更完整的安全沙箱、权限审批、真实异步并发调度、终端交互体验、长期记忆、企业级审计、规模化工具生态和系统化 benchmark。这个项目的价值是把 Coding Agent 的核心链路做成了一个可运行、可测试、可解释的最小系统，让我能从工程原理上讲清楚这类 Agent 怎么工作。

可能追问：如果生产化优先做什么？建议回答模块拆分、安全沙箱、任务评测、观测审计、异步工具调度。

### 四、P1 准备问题

Sub-agent 和 Skills 是高频 P1。面试官问它们，是因为这两个词听起来都像“扩展能力”，容易混淆。回答时要区分：Sub-agent 解决任务上下文隔离，适合探索、规划、实现拆分；Skills 解决领域流程按需注入，适合把 PDF 处理、代码审查、MCP 构建等知识放进 `SKILL.md`，需要时再加载。

推荐回答：

Sub-agent 和 Skills 解决的是两个不同层面的问题。Sub-agent 解决执行上下文隔离，比如主 Agent 要做一个代码修改任务，前面可能需要探索很多文件，如果这些中间结果都进入主上下文，会污染后续决策，所以我用独立 Agent 实例执行 explore、plan、code 等子任务，最后只把摘要返回主 Agent。Skills 解决的是知识和流程的按需注入，比如某类任务需要一套固定流程，不应该一开始全部塞进 system prompt，而是把流程写进 `SKILL.md`，匹配到任务时再加载。简单说，Sub-agent 解决“任务怎么拆”，Skills 解决“专业流程怎么按需给模型”。

session resume 是 P1。面试官问它，是因为长任务 Agent 不可能每次从零开始。回答要说保存 messages、token usage、权限状态、文件读取状态，尤其是 read-before-edit 依赖文件读取状态，否则恢复后可能误判文件是否读过。

推荐回答：

session resume 的意义是让长任务 Agent 可以中断后继续执行，而不是每次从零开始。我保存的不只是 messages，还包括 token usage、权限模式、文件读取状态等。文件读取状态很关键，因为 read-before-edit 依赖它判断某个文件是否已经被读过，以及读取时的 mtime。如果恢复时只恢复对话，不恢复这些工程状态，Agent 可能会误判权限或误判文件安全状态。所以 session resume 本质上保存的是 Agent Runtime 的执行状态，而不只是聊天记录。

权限模式是 P1。回答要讲 plan/default/acceptEdits/bypassPermissions/dontAsk 是不同信任级别下的工具策略。关键不是背名字，而是说明 Agent 在分析、编辑、测试、子任务阶段应该有不同权限边界。

推荐回答：

权限模式的核心是让 Agent 在不同任务阶段有不同工具边界。比如 plan 模式适合只读分析，不应该允许写文件和执行高风险 shell；default 模式允许常规工具，但需要拦截危险命令；acceptEdits 更偏向允许文件编辑；bypassPermissions 适合可信测试或受控子任务，但风险最高；dontAsk 更保守，会阻断写操作和 shell。这个设计说明 Coding Agent 不能默认拥有无限权限，尤其是涉及文件修改和命令执行时，必须有清晰的信任分级。

离线测试是 P1。回答要明确：测试不依赖真实 API key，覆盖 streaming tool assembly、MCP stdio discovery/call、文件安全、压缩和 session resume。面试官看不到代码时，测试就是最强证据。

推荐回答：

离线测试的价值是把 Agent 里确定性的工程逻辑固定住，而不是依赖真实模型随机发挥。我写的测试不需要 API key，主要覆盖 Anthropic streaming tool assembly、MCP stdio discovery/call、read-before-edit、edit diff、大结果落盘压缩、session save/load 和危险 shell segment 检测。这样即使面试现场没有网络或 API，也能说明这些关键机制是能运行和验证的。真实模型调用可以作为演示，但核心协议解析、安全检查和状态恢复应该先能离线验证。

### 五、面试官追问链路图

如果你开场说“这是 Claude Code 类 Agent”，面试官大概率追问：它和 Chatbot 区别是什么 -> Agent Loop 怎么跑 -> tool result 怎么回写 -> 如果工具失败或循环怎么办。

如果你说“解决上下文膨胀”，面试官大概率追问：为什么会膨胀 -> 为什么不直接截断 -> 四层压缩顺序是什么 -> summary 丢信息怎么办 -> 有没有评估指标。

如果你说“保证自动编辑安全”，面试官大概率追问：为什么要 read-before-edit -> mtime 解决什么 -> old_text 多处匹配怎么办 -> diff 有什么用 -> shell 检测是否足够。

如果你说“支持 MCP”，面试官大概率追问：MCP 和普通 tool function 区别 -> JSON-RPC stdio 怎么通信 -> tools/list 和 tools/call 怎么映射 -> mcp 前缀为什么需要。

如果你说“支持 streaming”，面试官大概率追问：Anthropic 和 OpenAI-compatible 差异 -> partial_json 怎么组装 -> 为什么抽象 ModelResult -> 是否支持工具早期执行。

如果你说“写了离线测试”，面试官大概率追问：测了哪些路径 -> 为什么不依赖真实模型 -> 哪些还没测 -> 怎么做 benchmark。

### 六、最佳准备顺序

第一轮先背 P0 六题，目标是任何一道都能在 60-90 秒内讲清楚。P0 不熟，后面的细节再多也救不了。

第二轮准备 P1 四题，目标是能接住 2-3 层追问。重点是 Sub-agent/Skills、session resume、权限模式、离线测试。

第三轮准备 P2 扩展，目标是遇到强面试官时能加分。比如 semantic sideQuery、OpenAI message 转换、v0-v6 演进、cost budget。

第四轮做反向自查：每个简历关键词都要能回答三个问题：为什么需要它？你怎么实现？它有什么边界？

### 七、开场回答模板

30 秒版本：

> 这个项目是我基于 Python 复现并扩展的 Claude Code 类 Coding Agent 核心机制。它不是普通 Chatbot，而是围绕 ReAct Agent Loop 构建“模型决策、Tool Calling、工具执行、Observation 回写”的闭环。在这个闭环上，我重点补了长任务上下文压缩、自动代码编辑安全、Sub-agent/Skills 任务隔离与知识注入、MCP 工具接入，以及 Anthropic/OpenAI-compatible 双后端 streaming 抽象，并用离线测试验证关键机制。

90 秒版本：

> 我做这个项目的目标是理解 Claude Code 类 Coding Agent 背后的运行时机制。普通 LLM 应用通常是一次输入一次输出，但 Coding Agent 要能持续执行任务，所以我先实现 ReAct Agent Loop：模型根据 messages 决策是否调用工具，工具执行后把 Observation 回写上下文，再进入下一轮决策。随后我围绕长任务补了几类工程能力：第一是 4 层上下文压缩，解决工具结果膨胀和信息污染；第二是 read-before-edit、mtime、old_text 唯一性和 unified diff，降低自动编辑代码的误改风险；第三是 Sub-agent 和 Skills，分别解决任务隔离和领域流程按需注入；第四是 MCP JSON-RPC stdio 和双后端 streaming，通过 `ModelResult` 把不同模型协议统一到同一个 Agent Loop。最后我写了离线测试覆盖 streaming tool assembly、MCP 调用、文件安全、上下文压缩和 session 恢复。这个项目不是完整生产级 Claude Code，而是核心机制可运行、可测试、可解释的面试版 Agent Runtime。

### 八、什么样的回答会显得资料优秀

优秀回答不是堆名词，而是每个技术点都能讲出“问题、方案、取舍、边界、验证”。比如讲上下文压缩时，要说清楚为什么压缩、每层保留什么、损失什么、如何恢复、怎么评估；讲文件安全时，要说清楚每个机制防哪类错误；讲 MCP 时，要说清楚协议、路由、命名冲突和统一抽象；讲 streaming 时，要说清楚事件模型差异和 partial_json 组装。

面试官看不到代码时，最能打动他的不是“我实现了某某功能”，而是你能把一个简历关键词背后的追问链路讲完整。准备时一定要避免只背定义，要用“为什么会问 -> 我怎么证明 -> 如果继续追问我怎么接”的方式准备。

最终判断标准：

> P0 问题答得稳，说明你理解 Agent 主线；P1 问题接得住，说明你有工程细节；P2 问题能补充，说明你有扩展视野。这样的项目材料才像 AI 研发候选人的简历准备文档。
