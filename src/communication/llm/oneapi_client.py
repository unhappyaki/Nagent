import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from src.infrastructure.config.unified_config import UnifiedConfigManager
import structlog

logger = structlog.get_logger(__name__)

@dataclass
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    model: str
    timestamp: str

@dataclass
class OneAPIConfig:
    base_url: str = "http://localhost:3000"
    api_key: str = ""
    timeout: int = 60
    max_retries: int = 3

class OneAPIClient:
    def __init__(self, config: OneAPIConfig):
        self.config = config
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=config.timeout))
        logger.info("OneAPI client initialized", base_url=config.base_url, timeout=config.timeout)

    async def chat_completion(self, messages: List[Dict[str, str]], model: str = "gpt-3.5-turbo", **kwargs) -> Dict[str, Any]:
        payload = {"model": model, "messages": messages, **kwargs}
        url = f"{self.config.base_url}/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.config.api_key}", "Content-Type": "application/json"}
        async with self.session.post(url, json=payload, headers=headers) as response:
            return await response.json()

    async def close(self):
        await self.session.close()

_oneapi_client: Optional[OneAPIClient] = None

def get_llm_client() -> OneAPIClient:
    global _oneapi_client
    if _oneapi_client is None:
        config = UnifiedConfigManager().get_llm_gateway_config().get("oneapi", {})
        oneapi_config = OneAPIConfig(
            base_url=config.get("base_url", "http://localhost:3000"),
            api_key=config.get("api_key", ""),
            timeout=config.get("timeout", 60),
            max_retries=config.get("max_retries", 3)
        )
        _oneapi_client = OneAPIClient(oneapi_config)
    return _oneapi_client 