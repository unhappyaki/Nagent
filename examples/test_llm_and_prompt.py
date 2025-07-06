import asyncio
import sys
import os

# 添加项目根目录和src目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = os.path.join(project_root, 'src')
sys.path.append(project_root)
sys.path.append(src_path)

from src.communication.llm.oneapi_client import get_llm_client
from src.core.reasoning.llm_reasoner import LLMReasoner

async def test_llm_direct():
    """测试直接LLM调用"""
    print("=== 开始测试直接LLM调用 ===")
    try:
        llm_client = get_llm_client()
        messages = [
            {"role": "user", "content": "你好，帮我写一个Python打印九九乘法表的代码。"}
        ]
        response = await llm_client.chat_completion(messages=messages, model="qwen-turbo")
        print("【直接LLM调用结果】\n", response["choices"][0]["message"]["content"])
        print("=== 直接LLM调用测试完成 ===\n")
    except Exception as e:
        print(f"直接LLM调用测试失败: {e}")

async def test_llm_reasoner():
    """测试LLM推理器+Prompt注入"""
    print("=== 开始测试LLM推理器+Prompt注入 ===")
    try:
        reasoner = LLMReasoner(model="qwen-turbo")
        task = "请帮我写一个Python打印九九乘法表的代码。"
        context = [
            {"role": "user", "content": "我想要一个简单的Python代码示例。"}
        ]
        result = await reasoner.reason(task=task, context=context)
        print("【Reasoner推理器+Prompt注入结果】\n", result)
        print("=== LLM推理器测试完成 ===\n")
    except Exception as e:
        print(f"LLM推理器测试失败: {e}")

async def main():
    await test_llm_direct()
    await test_llm_reasoner()
    # 关闭 OneAPIClient 的 session，避免 Unclosed client session 警告
    llm_client = get_llm_client()
    await llm_client.close()

if __name__ == "__main__":
    print("开始运行LLM调用和Prompt注入测试...\n")
    asyncio.run(main())
    print("所有测试完成！") 