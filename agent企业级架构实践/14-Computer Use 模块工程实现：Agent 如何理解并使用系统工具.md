14-Computer Use 模块工程实现：Agent 如何理解并使用系统工具
-------------------------------------

* * *

### 🔍 摘要

让智能体理解并执行系统工具（Computer Use），是 Agent 从语言执行器进化为**具备真实行为能力体**的关键步骤。  
不是写死调用接口，不是模拟 prompt 指令，而是构建一套**工具注册 → 工具感知 → 工具选择 → 工具执行**的完整模块体系。  
本篇从系统视角出发，讲清楚：

*   如何构建一个标准的 `ComputerUseTool` 工程模块
*   如何让 Reasoner 判断任务目标并匹配合适工具
*   如何封装系统指令/Shell/HTTP/文件操作为统一行为接口
*   如何做调用安全、权限隔离与行为 trace

* * *

### 📘 目录

#### 一、Computer Use 模块的系统定位与职责划分

*   1.1 工具模块在 Agent 执行链中的作用
*   1.2 LLM vs 工具：语言与动作的协同结构
*   1.3 推荐模块划分结构（tool interface + executor + registry）

* * *

#### 二、工具封装标准接口结构设计

*   2.1 定义统一 Tool 接口（register\_tool + execute(ctx)）
*   2.2 支持 Shell / 文件 / API / Python 调用的统一封装方式
*   2.3 工具参数规范与输入格式标准化建议

* * *

#### 三、Reasoner 如何理解工具任务与触发调用

*   3.1 工具选择型 Prompt 模板（LLM）
*   3.2 工具索引 / Tool Selector 模块设计
*   3.3 RL 推理策略中的工具动作空间结构

* * *

#### 四、工具执行层设计：安全控制与运行轨迹管理

*   4.1 ToolChain 执行框架 + 异常封装 + 超时限制
*   4.2 高风险工具的权限审计（如 Shell / 删除操作）
*   4.3 TraceWriter 集成工具调用链结构

* * *

#### 五、从任务到执行的完整路径案例拆解

*   5.1 输入 → Reasoner 推理 → Tool 调用 → 输出写入
*   5.2 多工具组合场景示例：总结报告 → 调用翻译 → 上传云端
*   5.3 支持回放与 Debug 的调用链结构复原方法

* * *

#### 六、可扩展方向：向通用 ToolOS 架构演进

*   6.1 多语言工具支持（如 Bash + Python + PowerShell）
*   6.2 Agent 工具链分级设计（内置工具 vs 外部系统）
*   6.3 工具行为训练与元行为学习方向

* * *

### ✅ 第一章：Computer Use 模块的系统定位与职责划分

* * *

#### 1.1 工具模块在 Agent 执行链中的作用

在一个完整的 Agent 执行路径中：

    输入 → Reasoner 推理 → 工具调用 → 状态记录 → 输出
    

其中**Tool（工具调用）模块**是唯一具备**真实外部行为能力**的部分，作用包括：

功能项

说明

执行系统指令

如 Shell 操作、Python 调用、本地函数封装

操作外部接口

各类 HTTP / RPC API

文件读写

访问、解析、存储本地或远程文件

管理系统资源

如检查 CPU 使用率、上传文件、运行脚本

Agent 若无 Tool，仅依赖 LLM，就是个"聊天助手"；引入 Tool，才是真正具备"任务执行力"的 Agent。

* * *

#### 1.2 LLM vs 工具：语言与动作的协同结构

模块

职责

LLM 推理器

决定"做什么"，如选择哪个 Tool

Tool 模块

执行"具体怎么做"，真正完成任务行为

AgentBase

管控整体行为链（感知 → 推理 → 执行）

建议结构中，LLM 只产出工具调用意图，而不直接操作系统：

    # Reasoner 输出
    {
      "action": "read_file",
      "params": {"path": "/data/report.txt"}
    }
    

* * *

#### 1.3 推荐模块划分结构

    tools/
    ├── __init__.py            # 注册中心
    ├── shell_exec.py          # 执行系统指令
    ├── file_io.py             # 文件读写
    ├── translate_api.py       # 接外部翻译服务
    ├── screenshot_tool.py     # 调用截图程序
    └── chain.py               # ToolChain 总调度器
    

每一个工具模块都应：

*   封装成标准函数
*   可注册到 `TOOL_REGISTRY`
*   接收统一 context 结构
*   支持 trace + 安全审计

* * *

### ✅ 第二章：工具封装标准接口结构设计

* * *

#### 2.1 Tool 接口标准定义

所有工具模块都应符合统一结构：

    # tools/__init__.py
    TOOL_REGISTRY = {}
    
    def register_tool(name):
        def wrapper(fn):
            TOOL_REGISTRY[name] = fn
            return fn
        return wrapper
    

##### ✅ 示例：注册 Shell 执行工具

    # tools/shell_exec.py
    from tools import register_tool
    import subprocess
    
    @register_tool("shell_exec")
    def shell_exec_tool(ctx):
        cmd = ctx["input"].get("cmd", "")
        try:
            result = subprocess.check_output(cmd, shell=True, timeout=5)
            return result.decode()
        except Exception as e:
            return f"[ERROR] {e}"
    

* * *

#### 2.2 工具统一封装结构（ToolChain）

    # tools/chain.py
    from tools import TOOL_REGISTRY
    
    class ToolChain:
        def execute(self, action, context):
            fn = TOOL_REGISTRY.get(action)
            if not fn:
                raise Exception(f"Tool '{action}' not found")
            return fn(context)
    

Agent 调用：

    result = self.toolchain.execute("shell_exec", context)
    

* * *

#### 2.3 参数传递规范建议

为了统一 Reasoner 与 Tool 之间的交互：

字段名

类型

说明

`input`

dict

工具接收的参数字典

`task_id`

str

当前任务标识

`trace`

list

当前行为链

`memory`

dict

当前任务上下文状态

Reasoner 应返回如下结构：

    {
      "action": "shell_exec",
      "params": {"cmd": "df -h"}
    }
    

Agent 执行时打包成：

    context = {
      "input": decision["params"],
      "task_id": ...,
      "trace": ...,
      "memory": ...
    }
    

* * *

### ✅ 第三章：Reasoner 如何理解工具任务并触发调用

* * *

#### 🤔 3.1 工具选择型 Prompt 设计（LLM 模式）

LLM Reasoner 在处理"工具调用型任务"时，其核心逻辑是：

1.  理解当前输入目标
2.  从可用工具列表中选择一个
3.  输出对应的 `action + params`

* * *

##### ✅ Prompt 模板建议（Tool Selector Prompt）

    你是一个系统行为决策器，请根据任务内容选择一个要使用的工具，并给出参数。
    
    工具列表如下：
    - shell_exec(cmd): 执行系统命令
    - read_file(path): 读取文件内容
    - upload_file(path): 上传文件至云端
    - translate(text): 翻译输入文本
    
    任务输入：{{ input_text }}
    
    请返回如下 JSON 格式：
    {
      "action": "...",
      "params": { ... }
    }
    

* * *

##### ✅ 实例输出：

    {
      "action": "read_file",
      "params": {"path": "/data/report.txt"}
    }
    

* * *

#### 🔎 3.2 工具索引模块：基于工具定义构建可查询列表

Reasoner 可结合工具注册表生成 prompt 工具说明段：

    def generate_tool_description():
        return {
            name: fn.__doc__ or "No description"
            for name, fn in TOOL_REGISTRY.items()
        }
    

✅ 工具文档自动生成 → 可用作 LLM Prompt 中的工具菜单

* * *

#### 🧠 3.3 RL 推理策略中的工具选择动作空间

当 Reasoner 使用 RLPolicy（如 PPO/DPO）进行行为选择时，工具调用应被建模为**离散动作空间的一部分**。

##### ✅ 示例动作空间结构：

    ACTIONS = [
        "shell_exec",
        "read_file",
        "translate",
        "submit_api",
        "terminate"
    ]
    

* * *

##### ✅ RLPolicyReasoner 示例：

    class RLPolicyReasoner(BaseReasoner):
        def __init__(self, model, tokenizer):
            self.model = model
            self.tokenizer = tokenizer
    
        def decide(self, context):
            prompt = f"任务内容：{context['input']}"
            input_ids = self.tokenizer(prompt, return_tensors="pt").input_ids
            logits = self.model(input_ids)[0][:, -1, :]
            action_id = torch.argmax(logits, dim=-1).item()
            action_name = ACTIONS[action_id]
    
            return {
                "action": action_name,
                "params": context["input"]
            }
    

* * *

#### 🧩 推荐组合方式：ReasonerRouter + Tool Selector 模式

你可以组合三种 Reasoner：

*   `RuleReasoner`: 显式规则（如 high risk → 审计工具）
*   `LLMReasoner`: 语言推理决定工具
*   `RLPolicyReasoner`: 学习优化决策路径

通过 Router 封装组合：

    class ReasonerRouter(BaseReasoner):
        def decide(self, context):
            if context["input"].get("risk", "") == "high":
                return self.rule.decide(context)
            if context.get("use_rl"):
                return self.rl.decide(context)
            return self.llm.decide(context)
    

* * *

### ✅ 第四章：工具执行层设计 —— 安全控制与行为轨迹管理

* * *

#### 🔧 4.1 ToolChain 执行框架设计（统一封装工具调用）

所有工具最终都通过 `ToolChain` 执行。这个模块的职责是：

*   调用对应工具函数
*   捕获执行异常
*   限制运行时间 / 参数风险
*   标准化返回结果
*   写入行为 Trace

* * *

##### ✅ 工程结构推荐（`tools/chain.py`）

    from tools import TOOL_REGISTRY
    import traceback
    import time
    
    class ToolChain:
        def __init__(self, trace_writer=None):
            self.trace_writer = trace_writer
    
        def execute(self, action, context):
            fn = TOOL_REGISTRY.get(action)
            if not fn:
                raise Exception(f"Tool '{action}' not registered")
    
            start = time.time()
            try:
                result = fn(context)
                success = True
            except Exception as e:
                result = f"[ToolError] {str(e)}\n{traceback.format_exc()}"
                success = False
    
            end = time.time()
    
            # 记录 trace
            if self.trace_writer:
                self.trace_writer.append({
                    "tool": action,
                    "agent": context.get("agent", "unknown"),
                    "input": context["input"],
                    "result": str(result)[:200],
                    "duration": round(end - start, 3),
                    "success": success,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
                })
    
            return result
    

* * *

#### 🛡️ 4.2 高风险工具的权限控制与审计机制

##### ✅ 封装建议：为高风险操作加"审计拦截器"

    def secure_tool(fn):
        def wrapper(ctx):
            user = ctx.get("user")
            if user not in ["admin", "ops"]:
                raise PermissionError("Unauthorized tool usage")
            return fn(ctx)
        return wrapper
    
    @register_tool("shutdown_server")
    @secure_tool
    def shutdown_tool(ctx):
        return os.system("shutdown now")
    

✅ 所有危险级操作都必须明确用户权限  
✅ 可与上下文结合识别：任务 ID、来源 IP、调用 Agent 等

* * *

#### ⏱️ 4.3 加入超时控制（避免工具 hang 死）

以 `subprocess` 为例：

    import subprocess
    
    @register_tool("shell_exec")
    def shell_exec(ctx):
        cmd = ctx["input"]["cmd"]
        result = subprocess.check_output(cmd, shell=True, timeout=5)
        return result.decode()
    

✅ 建议所有工具执行加 timeout  
✅ 可结合 async + watchdog 更强控制执行资源

* * *

#### 🧾 4.4 TraceWriter 集成工具行为链结构

建议工具执行行为统一写入 TraceWriter：

    # trace/trace_writer.py
    class TraceWriter:
        def __init__(self):
            self.logs = {}
    
        def append(self, trace_obj):
            task_id = trace_obj.get("task_id", "default")
            self.logs.setdefault(task_id, []).append(trace_obj)
    
        def get(self, task_id):
            return self.logs.get(task_id, [])
    

* * *

##### ✅ Trace 内容结构建议

字段

含义

`tool`

执行工具名称

`input`

调用参数（已脱敏）

`result`

返回摘要或调用结果

`duration`

执行时长

`success`

是否成功执行

`timestamp`

执行时间

* * *

### ✅ 第五章：从任务到执行的完整路径案例拆解

* * *

#### 🧩 5.1 输入 → 推理 → 工具调用 → 输出写入：完整链演示

构造一个典型任务：

> 用户输入："请读取 `/data/summary.txt` 内容，并将其翻译成英文。"

* * *

##### ✅ Reasoner 推理输出：

    {
      "action": "read_file",
      "params": {"path": "/data/summary.txt"}
    }
    

Agent 执行：

    step1_result = toolchain.execute("read_file", ctx)
    

* * *

##### ✅ 二级任务构造（嵌套任务）：

将 step1 的结果作为二次输入，生成下一个工具行为：

    step2_ctx = {
      "input": {"text": step1_result},
      "task_id": ctx["task_id"],
      "trace": ctx["trace"]
    }
    step2_result = toolchain.execute("translate", step2_ctx)
    

* * *

##### ✅ 最终行为 trace 示例：

    [
      {"tool": "read_file", "duration": 0.08, "success": true},
      {"tool": "translate", "duration": 0.21, "success": true}
    ]
    

✅ 具备完整链式结构，便于追踪、回放、性能监控。

* * *

#### 🔗 5.2 多工具组合场景结构设计

构造一个"自动日报生成"任务链：

    PlanAgent:
      - 读取日报数据源
      - 调用分析工具
      - 生成摘要
      - 翻译摘要
      - 提交 API 调用
    

对应工具序列：

    steps = [
      ("read_file", {"path": "/data/report.json"}),
      ("summarize", {"length": "short"}),
      ("translate", {"lang": "en"}),
      ("submit_api", {"url": "http://api.submit/report"})
    ]
    

用 `ToolChain.execute()` 顺序调用完成任务闭环。

* * *

#### 🧪 5.3 调用链复原：用于回放、调试、任务失败重启

结合 TraceWriter 可实现：

*   **Trace 回放器**：按 trace log 重演行为链
*   **Debug 工具**：断点在某一 Tool，打印上下文
*   **任务恢复器**：从中断位置恢复任务继续执行

建议构建：

    scripts/
    ├── replay_trace.py         # 读取 trace 日志逐步重放任务
    

* * *

### ✅ 第六章：可扩展方向 —— 向通用 ToolOS 架构演进

* * *

#### 🌍 6.1 多语言工具执行支持

将工具执行语言拓展为：

工具语言

说明

Shell

系统指令执行

Python 函数

内部脚本行为封装

PowerShell

Windows 系统指令支持

JavaScript

用于浏览器 Agent 或 Node 应用

建议结构：

    @register_tool("exec_js")
    def js_tool(ctx):
        return run_nodejs_code(ctx["input"]["script"])
    

* * *

#### 🧱 6.2 工具链分级结构（内置 vs 系统 vs 第三方）

将工具按用途做分级管理：

工具类型

管理策略

内置工具

系统默认启用，提供基础读写/翻译等能力

系统工具

操作资源类，建议有权限封装 + 调用审计

外部服务工具

统一用 ToolProxy 结构接 API / 服务

封装建议：

    class ToolProxy:
        def __init__(self, endpoint):
            self.endpoint = endpoint
    
        def __call__(self, ctx):
            return requests.post(self.endpoint, json=ctx).json()
    

* * *

#### 🧠 6.3 工具行为训练与元行为学习

可将 Tool 使用行为转为「策略优化问题」：

*   多工具调用顺序优化（RL）
*   Agent 自主发起组合工具（Planner+ToolDSL）
*   多 Agent 工具链复用 → 形成共享技能网格

将来建议引入：

模块

实现方向

ToolPolicy

工具选择 + 调用策略模型（PPO/DPO）

ToolDSL

多工具编排语法描述器

Skill Registry

多 Agent 可复用的"工具技能层"

* * *

