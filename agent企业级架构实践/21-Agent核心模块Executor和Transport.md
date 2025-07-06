21-Agent核心模块Executor和Transport
-------------------------------------

* * *

Runtime Executor 与 Transport 模块源码解析：智能体任务调度的核心引擎
------------------------------------------------

* * *

### 🔍 摘要

在一个 Agentic AI 系统中，ACP 中控协议负责任务调度和状态同步，但真正驱动 Agent 行为执行的，是 **ADK 中的 Runtime Executor 模块**。它负责将接收到的任务分发到回调函数、处理异常、管理上下文与输出结果。与此同时，**Transport 模块**作为连接外部系统或其他 Agent 的通信层，负责在任务链之间实现真正的"Agent-to-Agent"消息流转。  
本篇将深入解析 Runtime 与 Transport 模块的源码架构、核心逻辑与使用方式，逐行讲解执行引擎如何构建一个稳定、高并发、可追踪的智能体任务调度核心。

* * *

### 📘 目录

* * *

#### 一、模块职责与系统结构总览

*   1.1 Runtime 在 ADK 中的位置与职责
*   1.2 Executor、Transport、Callback 三大模块协作关系
*   1.3 调用链结构图：从 ACP 消息到 Callback 输出

* * *

#### 二、Runtime Executor 源码详解

*   2.1 `RuntimeExecutor` 的接口设计与构造逻辑
*   2.2 回调注册/调度流程源码逐行解析
*   2.3 同步与异步执行支持机制（async/await 动态调度）
*   2.4 执行上下文与中间状态缓存的处理策略

* * *

#### 三、Transport 模块实战解析

*   3.1 为什么需要 Transport 模块？解决什么问题？
*   3.2 面向 Agent-to-Agent 通信的消息格式封装
*   3.3 HTTP / WebSocket / LLM-RPC 支持的可插拔设计
*   3.4 Transport 与 Executor 的融合逻辑

* * *

#### 四、故障容错与异常追踪机制

*   4.1 回调失败后的自动重试策略
*   4.2 上下文错误传播与错误日志存档
*   4.3 如何集成链路追踪（Tracing ID + 日志注入）

* * *

#### 五、扩展方向与集成建议

*   5.1 向多 Agent 并发执行演进（RuntimePool 架构）
*   5.2 与 ACP、Context、Memory 模块的整合策略
*   5.3 如何为 Runtime 加入限流、优先级队列、任务标签等高级能力

* * *

### ✅ 第一章：模块职责与系统结构总览

* * *

#### 1.1 Runtime 在 ADK 架构中的核心地位

在 Agentic AI 的整体系统架构中，**Runtime Executor 是连接 ACP 协议与具体 Agent 行为的中枢逻辑模块**。其核心职责如下：

角色

职责描述

Dispatcher（ACP）

接收外部任务，分发给指定 Agent

RuntimeExecutor

在 Agent 内部负责任务的执行与上下文管理

Callback Registry

注册任务名与具体行为函数的映射

Memory / Context

存储任务执行过程中的中间状态与历史

Transport（可选）

处理跨 Agent 或对外服务调用的封装

* * *

#### 1.2 三大核心模块关系图

              来自 ACP 的任务 (TASK)
                        │
                        ▼
          ┌─────────────────────────┐
          │     RuntimeExecutor     │ ←←←←←←←←←←←←←┐
          └──────────┬──────────────┘              │
                     ▼                             │
             ┌──────────────┐                      │
             │ CallbackRegistry │ ←←←←←←←←←←←←←←←←←┘
             └──────┬─────────┘
                    ▼
              ┌───────────┐
              │ Transport │ ←→（调用其他 Agent / 工具 / HTTP / LLM）
              └───────────┘
    

* * *

#### 1.3 调用链时序图（从 ACP 到回调结果）

    [ACP Server] → TASK → [Agent] RuntimeExecutor.run(task)
                                   │
                                   ├─ 查找 Callback（如 "debug_code"）
                                   ├─ 执行回调函数（可能异步）
                                   ├─ 写入 Memory/Context
                                   └─ 返回结果 → 由 ACP Client 回传 RESULT
    

* * *

### ✅ 第二章：Runtime Executor 源码详解

我们现在将逐行分析一个典型的 `RuntimeExecutor` 实现，全部基于真实可运行结构设计。

* * *

#### 📁 项目结构参考

    agent_adk/
    ├── adk/
    │   ├── executor.py         # RuntimeExecutor 实现
    │   ├── callback.py         # 回调注册中心
    │   ├── memory.py           # 上下文/状态容器
    │   └── transport.py        # 可选的外部任务执行模块
    

* * *

#### 2.1 executor.py — RuntimeExecutor 接口与构造逻辑

    # adk/executor.py
    
    class RuntimeExecutor:
        def __init__(self, callback_registry, memory):
            self.callbacks = callback_registry
            self.memory = memory
    

📌 说明：

*   **callback\_registry**：维护任务名与函数的映射关系
*   **memory**：用于任务间状态共享与上下文传递

* * *

#### 2.2 run\_task 方法源码逐行解析

    def run_task(self, task_name: str, *args, **kwargs):
        if task_name not in self.callbacks:
            raise ValueError(f"Task '{task_name}' is not registered.")
    
        func = self.callbacks[task_name]
    
        try:
            print(f"[Executor] Running: {task_name}")
            result = func(self.memory, *args, **kwargs)
            return result
    
        except Exception as e:
            print(f"[Executor ERROR] Task '{task_name}' failed: {e}")
            return {"error": str(e)}
    

📌 拆解重点：

*   检查任务是否已注册
*   将 `self.memory` 传入回调，允许函数使用状态存储
*   捕获异常防止崩溃，确保系统稳定性

* * *

#### 2.3 支持异步回调（推荐实践）

    import asyncio
    
    async def run_task_async(self, task_name: str, *args, **kwargs):
        if task_name not in self.callbacks:
            raise ValueError(f"Task '{task_name}' is not registered.")
    
        func = self.callbacks[task_name]
    
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(self.memory, *args, **kwargs)
            else:
                result = func(self.memory, *args, **kwargs)
            return result
    
        except Exception as e:
            print(f"[Executor ERROR] Task '{task_name}' failed: {e}")
            return {"error": str(e)}
    

📌 拆解重点：

*   自动判断是 `async def` 或普通函数
*   兼容 async 回调的任务执行逻辑（适用于 LLM、IO-bound 调用）

* * *

#### 2.4 支持上下文注入与状态标识

在执行函数前，可以注入额外的上下文（如任务来源、优先级等）：

    def run_task(self, task_name: str, *args, meta=None, **kwargs):
        if meta:
            self.memory.remember("meta", meta)
    
        ...
    

* * *

✅ 本章总结：

模块

说明

Executor

核心执行器，管理回调调度与异常捕获

CallbackMap

任务注册中心，提供任务路由

Memory

共享状态容器，跨任务数据支持

异步支持

支持 async/await 回调（强烈推荐）

* * *

### ✅ 第三章：Transport 模块实战解析

* * *

#### 🎯 为什么需要 Transport 模块？

在实际项目中，Agent 的任务往往不仅限于本地逻辑：

*   ✅ 需要调用外部 HTTP 接口（如调用一个服务、数据库 API）
*   ✅ 与其他 Agent 通信（Agent-to-Agent 协调）
*   ✅ 请求 LLM 模型进行推理、问答、翻译等任务

为了解耦这些调用逻辑，ADK 中通常引入 **Transport 模块** 作为抽象层，提供：

*   标准化的调用封装
*   支持多协议（HTTP / WebSocket / 本地调用）
*   返回格式一致（支持链式处理、日志跟踪）

* * *

#### 📁 transport.py — Transport 接口与默认实现

    # adk/transport.py
    
    import requests
    
    class HTTPTransport:
        def __init__(self, base_url):
            self.base_url = base_url
    
        def post(self, route, data):
            url = f"{self.base_url}{route}"
            try:
                response = requests.post(url, json=data, timeout=10)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                return {"error": str(e)}
    

📌 拆解说明：

*   简单封装 HTTP POST 接口
*   提供错误返回（不会抛异常）

* * *

#### 🔁 与 Executor 融合：回调内部使用 Transport

在你的 `callbacks.py` 中：

    from adk.transport import HTTPTransport
    
    transport = HTTPTransport("http://localhost:7001")
    
    def ask_llm(memory, prompt):
        payload = {"input": prompt}
        result = transport.post("/api/llm", payload)
        memory.remember("llm_response", result)
        return result.get("answer", "No answer.")
    

📌 拆解说明：

*   回调内部调用 Transport，返回结构可统一处理
*   可在回调后输出 RESULT → 自动返回至 ACP

* * *

#### 📌 高级建议：Transport 抽象接口设计

    class BaseTransport:
        def call(self, method, data): ...
    

支持：

*   `HTTPTransport` → 调用 RESTful 接口
*   `LLMTransport` → 调用 OpenAI API
*   `AgentBridgeTransport` → 调用其他 Agent 实例

允许按需注入进 `RuntimeExecutor` 或回调函数中。

* * *

### ✅ 第四章：故障容错与异常追踪机制

* * *

#### 🧱 4.1 回调失败自动重试（推荐结合 Retry Decorator）

    from tenacity import retry, stop_after_attempt, wait_fixed
    
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def unstable_task(memory, *args):
        ...
    

📌 拆解说明：

*   对非确定性调用（如 LLM/远端 API）非常有效
*   防止偶发网络抖动导致 Agent 异常退出

* * *

#### 🔍 4.2 上下文中的错误记录

当任务失败时记录错误信息，方便调试与回放：

    try:
        result = func(self.memory, *args, **kwargs)
        return result
    except Exception as e:
        self.memory.remember("last_error", str(e))
        return {"error": str(e)}
    

📌 可结合 `task_id` 做错误对账或日志聚合。

* * *

#### 🧬 4.3 链路追踪与日志注入

每个任务链建议带上统一的 `trace_id`：

    import uuid
    trace_id = str(uuid.uuid4())
    
    self.memory.remember("trace_id", trace_id)
    logger.info(f"[TRACE {trace_id}] Running: {task_name}")
    

最终可以配合：

*   ELK（Elastic Stack）收集日志链路
*   Prometheus → 自定义 metrics
*   Jaeger → 分布式调用追踪（可选集成）

* * *

### 🎯 总结

能力

状态

实现方式

外部调用封装

✅

Transport 模块

错误重试与兜底

✅

`tenacity` 自动重试封装

异常日志与链路记录

✅

日志注入 + Memory 存储

可扩展多协议调用支持

✅

统一抽象接口，多实现可切换

* * *

### ✅ 第五章：扩展方向与集成建议

* * *

#### 🔁 5.1 向多智能体并发执行演进：RuntimePool 架构

##### 问题背景：

当前 `RuntimeExecutor` 是单实例同步执行，面对多个任务时性能瓶颈明显。

##### ✅ 推荐扩展方案：RuntimePool

    class RuntimePool:
        def __init__(self, agent_pool):
            self.agents = agent_pool  # {"pm": PMExecutor(), "qa": QAExecutor()}
    
        async def run_chain(self, task_chain, input_data):
            ctx = input_data
            for step in task_chain:
                agent = self.agents[step["agent"]]
                ctx = await agent.run_task_async(step["task"], ctx)
            return ctx
    

📌 优点：

*   多 Agent 协同任务链调用清晰可控
*   支持异步并发（如多个 Agent 并发分支任务）

* * *

#### 🔀 5.2 Runtime 与 ACP、Memory 的整合策略

模块

整合方式

ACP

ACP Client 收到任务 → 调用 RuntimeExecutor

Memory

每个 Executor 持有独立 `AgentMemory` 实例

GlobalCtx

支持上下文共享，可由 Transport 触发广播或传参

    # 回调内部
    def generate_report(memory, content):
        memory.remember("report", content)
        return f"📄 报告已生成：{content[:50]}..."
    

* * *

#### 🚦 5.3 Runtime 扩展能力建议清单

能力

说明

✅ 任务优先级支持

任务加入 `priority`，调度器可排序处理

✅ 任务队列标签机制

支持任务分类执行，如 `{"tag": "docgen"}`

✅ 限流执行

每个 Agent 的 Executor 每秒最大任务数

✅ 调度窗口策略

支持任务批量执行、合并执行等优化

##### 示例：

    task_meta = {
        "priority": 5,
        "source": "ACP",
        "tag": "generate_summary"
    }
    executor.run_task("summarize", doc, meta=task_meta)
    

* * *

#### 🔧 推荐模块化封装建议（接口抽象）

抽象组件

建议定义

`BaseExecutor`

所有执行器基类

`CallbackRouter`

支持多路径动态注册

`TransportLayer`

抽象远程调用行为

`MemoryStore`

支持换 Redis 或向量存储

* * *

#### 🧩 与系统架构深度融合建议

##### ✅ 构建「智能体子系统模板」：

每个 Agent 模块按如下划分：

    pm_agent/
    ├── executor.py      ← RuntimeExecutor 派生
    ├── callbacks.py     ← 角色专属行为
    ├── memory.py        ← 私有状态空间
    └── acp_client.py    ← 内置通信模块
    

部署上支持：

*   多 Agent 容器并行部署
*   每个 Agent 独立运行、注册、调用、反馈

* * *

### 🎯 总结

模块

工程建议

RuntimeExecutor

支持 async、状态隔离、trace

Transport

支持多协议、统一异常结构

异常与容错

tenacity + 记忆日志

多 Agent 并发支持

RuntimePool、task\_chain DAG

工程结构推荐

按 Agent 分模块、可容器化

* * *

* * *

### 🌟 如果本文对你有帮助，欢迎三连支持！

👍 点个赞，给我一些反馈动力  
⭐ 收藏起来，方便之后复习查阅  
🔔 关注我，后续还有更多实战内容持续更新

* * *

> 写系统，也写秩序；写代码，也写世界。  
> 观熵出品，皆为实战沉淀。