# Mini Claude Code 当前项目面试题汇总

> 基于当前仓库 `v0_bash_agent.py` 到 `v6_full_agent.py` 的真实实现整理。
> 原 PDF 中的题目方向被保留，但回答口径已改成当前项目可运行、可追源码、可测试的版本。

## 使用口径

面试时建议这样介绍：

> Mini Claude Code 是一个从零实现 coding agent 的渐进式 Python 项目。v0-v4 用最少代码讲清 Agent Loop、工具调用、Todo、Sub-agent 和 Skills；v5/v6 在教学版基础上对齐面试材料，补充文件安全、权限系统、上下文压缩、语义记忆、MCP、双后端 streaming、session resume 和 cost budget 等工程机制。它不是 Claude Code 50 万行生产代码的完整复刻，而是核心机制可运行、可演示、可追源码的学习/面试复现版。

不要说：

> 我完整复刻了 Claude Code 的全部生产能力。

建议说：

> 我复现并验证了 Claude Code 类 coding agent 的关键机制，并用 v6 做成了一个可运行的 Python 面试完整版。

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
