import asyncio
import time
import logging
from src.communication.protocols.acp import ACPServer, ACPClient, ControlDispatcher, APIControlAdapter, ToolControlAdapter, ModelControlAdapter
from src.monitoring.tracing.trace_writer import TraceWriter
from src.communication.protocols.acp.message_schema import ACPMessageBuilder

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler("examples/acp_full_stack_test_result.txt", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

RESULT_FILE = "examples/acp_full_stack_test_result.txt"

def log(msg):
    print(msg)
    with open(RESULT_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

async def main():
    # 清空结果文件
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        f.write("=== ACP协议全链路端到端测试 ===\n\n")

    log("[1] 启动TraceWriter和ACPServer...")
    trace_writer = TraceWriter()
    server = ACPServer(host="localhost", port=9002, trace_writer=trace_writer)
    await server.start()
    log("[1] ACPServer启动成功 (localhost:9002)")

    log("[2] 启动ACPClient并连接...")
    client = ACPClient("ws://localhost:9002", trace_writer)
    success = await client.connect()
    log(f"[2] ACPClient连接结果: {'成功' if success else '失败'}")
    if not success:
        await server.stop()
        return

    log("[3] 初始化ControlDispatcher和适配器...")
    dispatcher = ControlDispatcher(trace_writer=trace_writer)
    dispatcher.register_adapter(APIControlAdapter())
    dispatcher.register_adapter(ToolControlAdapter())
    dispatcher.register_adapter(ModelControlAdapter())
    log("[3] ControlDispatcher和适配器注册完成")

    builder = ACPMessageBuilder(sender_id="test_client")
    tasks = [
        ("API", builder.create_tool_call_message(
            receiver_id="test_agent", tool_name="api_test", tool_args={"endpoint": "https://api.example.com/test", "method": "POST", "params": {"key": "value"}}, context_id="ctx_api", trace_id="trace_api")),
        ("TOOL", builder.create_tool_call_message(
            receiver_id="test_agent", tool_name="text_processor", tool_args={"text": "Hello, ACP!"}, context_id="ctx_tool", trace_id="trace_tool")),
        ("MODEL", builder.create_tool_call_message(
            receiver_id="test_agent", tool_name="gpt-4", tool_args={"prompt": "请生成一个关于ACP协议的简短描述"}, context_id="ctx_model", trace_id="trace_model")),
    ]

    for task_type, acp_msg in tasks:
        log(f"[4] 发送{task_type}任务...")
        # 通过dispatcher分发（模拟本地适配器执行）
        action_type = "api_call" if task_type == "API" else ("tool_exec" if task_type == "TOOL" else "model_call")
        # 构造payload给dispatcher
        payload = acp_msg.payload
        payload.action_type = action_type
        # dispatcher分发
        result = await dispatcher.dispatch(payload)
        log(f"[4] {task_type}适配器分发结果: {result.status}")
        log(f"[4] {task_type}适配器输出: {result.output}")
        # 客户端发送到服务端
        send_result = await asyncio.get_event_loop().run_in_executor(None, client._send_payload, acp_msg)
        log(f"[4] {task_type}任务发送到服务端: {'成功' if send_result else '失败'}")
        await asyncio.sleep(0.5)

    log("[5] 输出trace链路:")
    for trace_id in ["trace_api", "trace_tool", "trace_model"]:
        chain = trace_writer.get_trace_chain(trace_id)
        log(f"--- trace_id={trace_id} ---")
        for entry in chain:
            log(f"  [{entry.timestamp}] {entry.trace_type.value} | {entry.message} | data={entry.data}")

    await client.disconnect()
    await server.stop()
    log("[6] 测试完成，所有资源已释放。\n")
    log("=== 端到端ACP协议全链路测试结束 ===")

if __name__ == "__main__":
    asyncio.run(main())
