 # ADK（Agent Development Kit）开发包设计文档

## 一、定位与目标

ADK（Agent Development Kit）是企业级多智能体系统的开发基础包，旨在为业务层屏蔽底层智能体生命周期、回调、任务调度、状态管理、通信等复杂性，提供一套“注册-调度-回调-状态-扩展”一站式API。业务开发者可像用SDK一样，专注于业务逻辑和智能体行为，无需关心底层实现。

---

## 二、架构与目录结构

推荐目录结构如下：

```
src/adk/
├── __init__.py
├── agent_base.py         # Agent基类/生命周期
├── callback.py           # 回调注册与分发
├── executor.py           # 任务调度/执行器
├── memory.py             # 状态/记忆容器
├── registry.py           # Agent/任务注册中心
├── context.py            # 上下文/Session管理
├── runtime.py            # 运行时/主引擎
├── logger.py             # 日志
├── config.py             # 配置加载
└── types.py              # 统一类型定义
```

---

## 三、核心模块设计说明

### 1. Agent基类（agent_base.py）
- 提供生命周期钩子（on_start、on_task、on_finish等）
- 支持自定义回调注册
- 业务层继承后只需实现核心逻辑

### 2. 回调注册与分发（callback.py）
- 支持唯一性校验、事件钩子、异步/同步兼容
- 支持链式/多级回调

### 3. 任务调度/执行器（executor.py）
- 支持同步/异步任务调度
- 支持异常捕获、重试、回调链
- 可扩展为多Agent/多任务并发

### 4. 状态/记忆容器（memory.py）
- 支持短期（Context）、长期（Memory）、Session等多级状态
- 支持快照/恢复

### 5. Agent/任务注册中心（registry.py）
- 支持多Agent注册、按名称/类型查找
- 支持任务/回调批量注册

### 6. 上下文/Session管理（context.py）
- 支持多会话、跨任务状态隔离
- 支持业务自定义扩展

### 7. 运行时/主引擎（runtime.py）
- 提供统一启动、调度、事件分发入口
- 支持与ACP/BIR等外部协议对接

### 8. 日志与配置（logger.py, config.py）
- 统一日志、支持多级别
- 支持YAML/ENV/代码配置

### 9. 类型定义（types.py）
- 统一回调、任务、状态等类型，便于类型安全和IDE提示

---

## 四、业务层集成方式（用法示例）

### 1. 注册Agent与任务

```python
from adk.agent_base import AgentBase
from adk.executor import RuntimeExecutor

class MyAgent(AgentBase):
    def __init__(self, name):
        super().__init__(name)
        self.register_callback("say_hello", self.say_hello)
        self.register_callback("reflect", self.reflect)

    def say_hello(self, memory, name):
        greeting = f"Hello, {name}!"
        memory.remember("last_greeting", greeting)
        return greeting

    def reflect(self, memory):
        return memory.recall("last_greeting")

# 注册到运行时
agent = MyAgent("demo")
executor = RuntimeExecutor(agent)
result = executor.run_task("say_hello", "Alice")
print(result)
```

### 2. 多Agent/多任务/并发
- 业务层只需注册多个Agent，ADK自动调度
- 支持API/消息/定时等多种触发方式

---

## 五、最佳实践与护栏

- 注册回调/任务时做唯一性校验，防止覆盖
- 任务执行异常要有兜底（回调/日志/快照）
- 状态/Session/Memory分层，便于业务隔离
- 提供单元测试/集成测试用例

---

## 六、进阶与扩展建议

- 支持多Agent注册、分布式调度、API/消息队列对接
- 支持回调链、任务链、状态快照、权限控制
- 支持与LLM/ToolChain/外部API无缝集成
- 提供插件/扩展机制，业务可自定义回调、状态存储、日志等

---

## 七、结论

ADK开发包将企业级多智能体系统的核心能力抽象为易用、可扩展的开发接口。业务开发者只需专注于“注册Agent/任务→调度→回调→状态”，无需关心底层细节。推荐先在 `src/adk/` 下实现上述核心模块，逐步将现有能力抽象进来。

如需具体代码骨架/模板，或要将现有某个模块抽象进ADK包，请联系架构师或核心开发团队。

## Graph Engine（推理流/状态机/流程图）能力

- 已将原 src/graph_engine/ 下的所有能力集成到 adk.graph_engine.* 下，业务层可直接通过 adk.graph_engine.node、adk.graph_engine.edge、adk.graph_engine.state、adk.graph_engine.graph 等模块调用。
- 支持节点-边-状态-图的推理流、分支、回环、终止、trace、快照、diff、replay等。
- 推荐业务层统一通过 adk.graph_engine 进行流程编排和推理流控制，便于后续维护和升级。

## LangGraph 推理流/状态机能力

- 已集成 LangGraph（业界主流图结构推理流框架），可通过 `adk.langgraph_engine` 进行节点-边-状态-图的推理流编排。
- 支持自定义节点函数、条件分支、回环、终止节点、全链路trace等。
- 推荐业务层统一通过 `adk.langgraph_engine.StateGraph` 进行流程图式智能体推理流控制。

### 快速上手示例

```python
from adk.langgraph_engine import StateGraph

def reasoner_node(state):
    # 决策逻辑
    ...
    return state

def tool_node(state):
    # 工具执行逻辑
    ...
    return state

g = StateGraph()
g.add_node("reasoner", reasoner_node)
g.add_node("tool", tool_node)
g.add_edge("reasoner", "tool")
g.set_entry("reasoner")

result = g.run(initial_state)
print(result)
```

## PromptManager（提示词模板管理）

- 支持多类型、多版本、多Agent/多场景的提示词模板注册、查找、渲染、标签管理。
- 支持Jinja2风格参数化渲染，便于上下文注入。
- 业务层可通过`adk.prompt_manager`一站式调用。

### 快速上手示例

```python
from adk.prompt_manager import prompt_manager

# 注册模板
tpl = """你是一个助手，请用{{ lang }}回答：{{ question }}"""
prompt_manager.register_template("qa", tpl, version="v1", meta={"scene": "qa"})

# 渲染模板
context = {"lang": "中文", "question": "什么是LangGraph？"}
prompt = prompt_manager.render_template("qa", context, version="v1")
print(prompt)

# 列出所有模板
print(prompt_manager.list_templates())
```
