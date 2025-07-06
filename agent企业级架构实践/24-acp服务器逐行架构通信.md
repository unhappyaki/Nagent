
* * *

ACP Server/Client 源码逐行拆解：构建稳定可控的智能体通信协议
---------------------------------------

* * *

### 🔍 摘要

在 Agentic AI 系统中，智能体的调度与状态管理依赖于稳定的通信协议支持。ACP（Middle Control Protocol）不仅是任务流的传递中枢，更是系统稳定性的保证。本篇将从源码层面深入剖析 **ACP Server 与 Client 的全链路实现**，逐行讲解注册、任务派发、心跳同步、ACK 反馈等机制，帮助你彻底掌握构建高可用 Agent 通信架构的底层逻辑。

* * *

### 📘 目录

#### 一、项目结构与模块职责总览

*   1.1 ACP Server 模块组织与调用链图
*   1.2 ACP Client 模块封装与生命周期
*   1.3 Server-Client 调度流程时序图

#### 二、ACP Server 源码拆解

*   2.1 `agent_registry.py`：连接注册与心跳管理
*   2.2 `message_schema.py`：任务与响应结构定义
*   2.3 `dispatcher.py`：任务投递逻辑与异常保护
*   2.4 `app.py`：主服务端逻辑与异步处理机制

#### 三、ACP Client 源码逐行讲解

*   3.1 注册与能力声明（REGISTER）
*   3.2 任务接收与回调触发（TASK）
*   3.3 状态心跳与断线重连逻辑（STATE）
*   3.4 ACK 与 RESULT 的生成与回传

#### 四、源码调试技巧与测试建议

*   4.1 如何模拟多 Agent 与并发任务
*   4.2 如何打印任务流日志与上下文调试
*   4.3 如何写测试用例验证通信流程

#### 五、系统工程建议与模块演化方向

*   5.1 分布式 ACP Server 架构改造方案
*   5.2 持久化日志与中间任务缓存机制设计
*   5.3 接入链路追踪与异常回溯分析工具推荐

* * *

### ✅ 第一章：项目结构与模块职责总览

* * *

#### 1.1 ACP Server 模块组织与职责清单

    acp_server/
    ├── app.py                # Flask + WebSocket 服务入口
    ├── agent_registry.py     # 存储 agent 的注册信息与连接状态
    ├── dispatcher.py         # 接收 HTTP 任务请求并转发给目标 agent
    ├── message_schema.py     # 标准消息格式构建工具（TASK / ACK / RESULT）
    ├── utils.py              # 辅助模块（日志、时间戳等）
    

* * *

#### 1.2 ACP Client 模块组织与封装目标

    agent_adk/
    ├── acp_client/
    │   ├── client.py         # 核心通信逻辑（连接、接收、回传）
    │   ├── callbacks.py      # 本地任务处理器
    

目标是实现：

*   WebSocket 连接与注册
*   接收任务 → 执行 → 反馈 ACK/RESULT
*   定时发送心跳，保持在线状态

* * *

#### 1.3 Server 与 Client 调度流程时序图

    Client                 ACP Server
       │                        │
       │──── REGISTER ────────▶│
       │                        │
       │←──── ACK: REGISTER ───│
       │                        │
       │                        │
    User ──(POST TASK)──────▶ ACP
       │                        │
       │                        │
       │←───── TASK ───────────│
       │                        │
       │── ACK + RESULT ──────▶│
    

* * *

### ✅ 第二章：ACP Server 源码逐行拆解

* * *

#### 2.1 `agent_registry.py` — Agent 注册与状态管理

    # agent_registry.py
    
    import time
    
    # 全局 Agent 注册表：agent_id -> websocket + metadata
    AGENTS = {}
    
    def register_agent(agent_id, websocket):
        AGENTS[agent_id] = {
            "ws": websocket,
            "last_seen": time.time()
        }
    
    def get_agent_ws(agent_id):
        return AGENTS.get(agent_id, {}).get("ws")
    
    def update_heartbeat(agent_id):
        if agent_id in AGENTS:
            AGENTS[agent_id]["last_seen"] = time.time()
    
    def get_all_agents():
        return list(AGENTS.keys())
    

🔍 拆解说明：

*   注册信息不仅包含连接对象，还记录最后一次“心跳时间”
*   后续可用于断线检测、在线监控、状态追踪

* * *

#### 2.2 `message_schema.py` — 消息格式生成工具

    # message_schema.py
    
    import uuid
    import time
    
    def build_task(agent_id, action, params):
        return {
            "type": "TASK",
            "agent_id": agent_id,
            "task_id": str(uuid.uuid4()),
            "payload": {
                "action": action,
                "params": params
            },
            "timestamp": int(time.time())
        }
    

🔍 拆解说明：

*   所有任务都有 `type / agent_id / task_id / payload / timestamp`
*   保证统一结构，方便前端、日志平台、追踪系统消费

* * *

#### 2.3 `dispatcher.py` — 任务下发核心逻辑

    # dispatcher.py
    
    import json
    from message_schema import build_task
    from agent_registry import get_agent_ws
    
    async def send_task(agent_id, action, params):
        ws = get_agent_ws(agent_id)
        if not ws:
            raise Exception(f"Agent '{agent_id}' 不在线")
        msg = build_task(agent_id, action, params)
        await ws.send(json.dumps(msg))
        return msg
    

🔍 拆解说明：

*   `send_task` 方法是 Server 对外提供的“任务入口”
*   实际内部就是构造 TASK 消息 → 通过 WebSocket 推送

* * *

#### 2.4 `app.py` — 主服务端入口（Flask + WebSocket）

    # app.py
    
    from flask import Flask, request, jsonify
    from flask_sock import Sock
    import asyncio
    import json
    
    from agent_registry import register_agent, update_heartbeat
    from dispatcher import send_task
    
    app = Flask(__name__)
    sock = Sock(app)
    
    @app.route("/")
    def index():
        return "✅ ACP Server Ready"
    
    @app.route("/send", methods=["POST"])
    async def api_send_task():
        data = request.json
        agent_id = data["agent"]
        action = data["action"]
        params = data.get("params", {})
        msg = await send_task(agent_id, action, params)
        return jsonify(msg)
    

🔍 拆解说明：

*   `/send` 是外部平台发送任务的 HTTP 接口
*   实际调用内部 `dispatcher.send_task()` 向目标 Agent 投送任务

* * *

继续部分：WebSocket 消息处理循环

    @sock.route("/ws")
    async def handle_ws(ws):
        while True:
            try:
                msg = json.loads(await ws.receive())
                msg_type = msg.get("type")
                agent_id = msg.get("agent_id")
    
                if msg_type == "REGISTER":
                    register_agent(agent_id, ws)
                    await ws.send(json.dumps({"type": "ACK", "msg": "REGISTERED"}))
    
                elif msg_type == "STATE":
                    update_heartbeat(agent_id)
    
                elif msg_type == "ACK":
                    print(f"[ACK] Agent {agent_id} acked {msg.get('task_id')}")
    
                elif msg_type == "RESULT":
                    print(f"[RESULT] Agent {agent_id} → {msg.get('task_id')} = {msg['payload']}")
    
            except Exception as e:
                print(f"[Error] WebSocket error: {e}")
                break
    

🔍 拆解说明：

*   WebSocket 实现完整协议解析：
    *   REGISTER → 建立连接映射
    *   STATE → 心跳更新时间戳
    *   ACK / RESULT → 控制台记录、可接日志平台
*   可扩展为接入 Prometheus/Grafana 监控、Elastic 日志采集等

* * *

### ✅ 第三章：ACP Client 源码逐行讲解

* * *

#### 🎯 功能目标

客户端需要具备如下能力：

功能

描述

注册

启动时连接 ACP Server 并发送 REGISTER 消息

接收任务

通过 WebSocket 接收 TASK 消息

回调触发

调用本地函数处理任务，生成结果

状态心跳

定时向 ACP Server 发送 STATE 消息维持在线状态

结果回传

向 Server 回传 ACK 和 RESULT 消息

* * *

#### 📁 文件结构

    agent_adk/
    ├── acp_client/
    │   ├── client.py           # 主 WebSocket 连接逻辑
    │   ├── callbacks.py        # 本地任务回调函数注册表
    

* * *

### 🔍 逐行拆解

* * *

#### ✅ callbacks.py — 回调行为封装

    # acp_client/callbacks.py
    
    def debug_code(params):
        repo = params.get("repo", "unknown")
        return f"✅ 调试完成：分析了『{repo}』仓库的问题"
    
    def translate_doc(params):
        text = params.get("text", "")
        return f"✅ 翻译完成：'{text}' -> 『翻译结果』"
    
    CALLBACKS = {
        "debug_code": debug_code,
        "translate_doc": translate_doc,
    }
    

📌 拆解说明：

*   每个方法接收任务参数，返回文本结果
*   注册表 `CALLBACKS` 用于动态分发任务处理器（类似 API 路由）

* * *

#### ✅ client.py — 核心连接逻辑实现

##### 连接配置与导入

    # acp_client/client.py
    
    import asyncio
    import json
    import time
    import websockets
    from acp_client.callbacks import CALLBACKS
    
    ACP_URL = "ws://localhost:5000/ws"
    AGENT_ID = "agent_rd_001"
    

* * *

##### 注册消息

    async def send_register(ws):
        msg = {
            "type": "REGISTER",
            "agent_id": AGENT_ID,
            "capabilities": list(CALLBACKS.keys())
        }
        await ws.send(json.dumps(msg))
    

📌 拆解说明：

*   发送 REGISTER 消息，声明身份与支持的任务能力（自动生成）

* * *

##### 心跳机制（保持在线）

    async def send_heartbeat(ws):
        while True:
            msg = {"type": "STATE", "agent_id": AGENT_ID}
            await ws.send(json.dumps(msg))
            await asyncio.sleep(5)
    

📌 拆解说明：

*   每 5 秒一次向 ACP Server 上报心跳状态
*   Server 端会更新 `last_seen` 用于状态监控

* * *

##### 主消息接收循环

    async def handle_messages(ws):
        while True:
            data = await ws.recv()
            msg = json.loads(data)
    
            if msg["type"] == "TASK":
                task_id = msg["task_id"]
                payload = msg["payload"]
                action = payload["action"]
                params = payload.get("params", {})
    
                print(f"[TASK] {task_id} => {action}({params})")
    
                func = CALLBACKS.get(action)
                if not func:
                    print(f"[ERROR] Unknown action: {action}")
                    continue
    
                # 执行任务
                result = func(params)
    
                # 回传 ACK + RESULT
                await ws.send(json.dumps({
                    "type": "ACK",
                    "agent_id": AGENT_ID,
                    "task_id": task_id
                }))
                await ws.send(json.dumps({
                    "type": "RESULT",
                    "agent_id": AGENT_ID,
                    "task_id": task_id,
                    "payload": result
                }))
    

📌 拆解说明：

*   接收 TASK → 根据 `action` 查找本地函数 → 执行 → 返回结果
*   消息格式全程与 Server 对接一致

* * *

##### 启动主流程

    async def start_agent():
        async with websockets.connect(ACP_URL) as ws:
            await send_register(ws)
            asyncio.create_task(send_heartbeat(ws))
            await handle_messages(ws)
    

📌 拆解说明：

*   启动时执行三件事：
    1.  注册自身
    2.  后台循环心跳
    3.  主动接收并处理任务

* * *

#### ✅ 启动脚本 run\_agent.py

    # run_agent.py
    import asyncio
    from acp_client.client import start_agent
    
    if __name__ == "__main__":
        print("🚀 Agent 客户端启动中...")
        asyncio.run(start_agent())
    

* * *

#### 🧪 示例运行效果（控制台）

    $ python run_agent.py
    
    🚀 Agent 客户端启动中...
    [TASK] 872a... => debug_code({'repo': 'agentic-core'})
    

* * *

#### ✅ 本章总结

能力模块

状态

注册能力声明

✅

任务接收触发

✅

回调机制

✅

心跳状态

✅

结果回传

✅

这一 Client 模块可直接集成进任意 ADK Agent，作为任务接入主入口，也支持自定义封装为 MicroService。

* * *

### ✅ 第四章：源码调试技巧与测试建议

* * *

#### 🧪 4.1 如何模拟多 Agent 并发测试场景

##### ✅ 方法 1：多个终端启动不同 Agent ID

    $ AGENT_ID=agent_rd_001 python run_agent.py
    $ AGENT_ID=agent_rd_002 python run_agent.py
    $ AGENT_ID=agent_rd_003 python run_agent.py
    

在 `client.py` 中读取环境变量注入：

    import os
    AGENT_ID = os.getenv("AGENT_ID", "agent_rd_001")
    

* * *

##### ✅ 方法 2：自动批量创建模拟 Agent（集成测试）

可在测试脚本中创建多个 `asyncio.create_task(start_agent("agent_id"))` 实例，模拟负载压力。

* * *

#### 📋 4.2 单元测试 + 通信链测试建议

##### ✅ 重点测试点：

测试点

验证目标

注册成功

Server 是否记录 agent\_id

TASK 下发/回执完整

Server 是否正确接收 ACK 与 RESULT

异常 action 是否忽略

Client 回调函数未注册如何处理

心跳中断检测

Server 是否感知超时无心跳的断线 agent

* * *

#### ✅ 4.3 增加任务流追踪日志（建议写入 log 文件）

    import logging
    
    logging.basicConfig(filename="acp.log", level=logging.INFO)
    
    # 在任务执行、ACK、RESULT、STATE 时记录
    logging.info(f"[TASK] {agent_id} <- {action}")
    logging.info(f"[RESULT] {agent_id} => {result}")
    

结合 `task_id` 可构建完整链路追踪信息，支持任务排障与溯源。

* * *

#### ✅ 4.4 使用调试工具推荐：

工具名

用途说明

Postman

模拟 HTTP 任务派发接口

WebSocket UI

调试 Agent 与 ACP Server 的消息交互

ngrok / frp

远程代理本地测试端口（异地协同）

mitmproxy

拦截 & 可视化 WebSocket 消息流

* * *

### ✅ 第五章：系统工程建议与模块演化方向

* * *

#### 🧠 5.1 ACP Server 分布式演进结构

目标：让 ACP Server 支持多节点、任务可重分发、支持断点续传。

##### ✅ 架构图建议：

           +-----------+           +-----------+
           |  Client A | <──┐      |  Client B |
           +-----------+    │      +-----------+
                            ▼
                        ┌────────────┐
                        │  Nginx WS  │ ← TLS / LB / 限流
                        └─────┬──────┘
               ┌──────────────▼──────────────┐
               │   ACP Server (Gunicorn)     │
               └──────────────┬──────────────┘
                              ▼
                     ┌───────────────┐
                     │ Redis Broker  │ ← 任务队列、缓存、状态管理
                     └───────────────┘
    

* * *

#### 💾 5.2 引入任务持久化缓存机制（Redis or SQLite）

避免断连导致任务丢失：

    # dispatcher.py
    import redis
    r = redis.Redis()
    
    def queue_task(agent_id, action, params):
        task = build_task(agent_id, action, params)
        r.lpush(f"tasks:{agent_id}", json.dumps(task))
    

Agent 重连后可自动取回任务队列：

    def load_pending_tasks(agent_id):
        return [json.loads(t) for t in r.lrange(f"tasks:{agent_id}", 0, -1)]
    

* * *

#### 🔒 5.3 安全机制建议（上线部署前必加）

安全策略

说明

Token 鉴权

每个 Agent 注册前验证令牌合法性

HMAC 消息签名

所有发送/接收消息加入签名字段防篡改

限流机制

WebSocket 连接频次/速率控制

TLS 通信加密

使用 Nginx 或 WS-SSL 代理加密传输

* * *

#### 📊 日志 & 监控拓展建议

*   使用 `Prometheus + Grafana` 接入 ACP Server 各类指标：
    *   在线 Agent 数
    *   平均任务响应时延
    *   TASK/ACK/RESULT 成功率
*   使用 `Elastic + Filebeat` 做结构化日志收集

* * *

### 🎯 总结回顾

内容板块

实战完成情况

ACP Server 架构设计

✅ 全模块源码讲解 + 调度流程

Client 接入实现

✅ 注册、任务、反馈、心跳

调试与测试实践

✅ 多 Agent 模拟 + 日志打印

工程化建议

✅ 分布式结构 + Redis 缓存 + 安全机制

* * *
