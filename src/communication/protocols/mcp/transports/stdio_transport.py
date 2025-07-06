"""
Stdio传输协议实现

通过标准输入输出与MCP服务器通信
"""

import asyncio
import json
import os
from typing import Dict, List, Optional
import structlog

from .base_transport import BaseTransport
from ..mcp_types import MCPMessage, ConnectionStatus, StdioTransportConfig

logger = structlog.get_logger(__name__)


class StdioTransport(BaseTransport):
    """Stdio传输协议"""
    
    def __init__(self, config: StdioTransportConfig):
        """
        初始化Stdio传输
        
        Args:
            config: Stdio传输配置
        """
        super().__init__(config.timeout)
        self.config = config
        self.process: Optional[asyncio.subprocess.Process] = None
        self._pending_responses = {}
        
    async def connect(self) -> bool:
        """建立连接 - 启动MCP服务器进程"""
        try:
            self.status = ConnectionStatus.CONNECTING
            
            # 构建命令
            cmd = self.config.command + self.config.args
            if not cmd:
                raise ValueError("No command specified for stdio transport")
            
            # 准备环境变量
            env = os.environ.copy()
            env.update(self.config.env)
            
            logger.info(
                "Starting MCP server process",
                command=cmd,
                env_vars=list(self.config.env.keys())
            )
            
            # 启动进程
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            # 验证进程是否正常启动
            await asyncio.sleep(0.1)  # 给进程一点启动时间
            if self.process.returncode is not None:
                raise RuntimeError(f"MCP server process exited with code {self.process.returncode}")
            
            self.status = ConnectionStatus.CONNECTED
            logger.info("MCP server process started successfully", pid=self.process.pid)
            
            # 开始读取消息
            await self.start_reading()
            
            return True
            
        except Exception as e:
            self.status = ConnectionStatus.ERROR
            logger.error("Failed to start MCP server process", error=str(e))
            await self._cleanup_process()
            return False
    
    async def disconnect(self) -> bool:
        """断开连接 - 终止MCP服务器进程"""
        try:
            self.status = ConnectionStatus.DISCONNECTED
            
            # 停止读取消息
            await self.stop_reading()
            
            # 清理进程
            await self._cleanup_process()
            
            logger.info("MCP server process disconnected")
            return True
            
        except Exception as e:
            logger.error("Error during disconnect", error=str(e))
            return False
    
    async def send_message(self, message: MCPMessage) -> bool:
        """发送消息到MCP服务器"""
        if not self.process or not self.process.stdin:
            logger.error("No active process to send message")
            return False
        
        try:
            # 序列化消息
            message_json = message.to_json()
            message_bytes = (message_json + '\n').encode('utf-8')
            
            # 发送消息
            self.process.stdin.write(message_bytes)
            await self.process.stdin.drain()
            
            logger.debug(
                "Sent MCP message",
                message_id=message.id,
                method=message.method,
                size=len(message_bytes)
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to send MCP message",
                message_id=message.id,
                error=str(e)
            )
            return False
    
    async def _read_messages(self) -> None:
        """读取来自MCP服务器的消息"""
        if not self.process or not self.process.stdout:
            logger.error("No process stdout to read from")
            return
        
        logger.debug("Started reading MCP messages")
        
        try:
            while self.status == ConnectionStatus.CONNECTED:
                # 读取一行消息
                line_bytes = await self.process.stdout.readline()
                
                if not line_bytes:
                    # 进程可能已关闭
                    logger.warning("No more data from MCP server")
                    break
                
                line = line_bytes.decode('utf-8').strip()
                if not line:
                    continue
                
                try:
                    # 解析消息
                    message = MCPMessage.from_json(line)
                    
                    logger.debug(
                        "Received MCP message",
                        message_id=message.id,
                        method=message.method,
                        has_result=message.result is not None,
                        has_error=message.error is not None
                    )
                    
                    # 处理消息
                    self._handle_message(message)
                    
                except Exception as e:
                    logger.warning(
                        "Failed to parse MCP message",
                        line=line[:100],  # 只记录前100个字符
                        error=str(e)
                    )
                    continue
                    
        except asyncio.CancelledError:
            logger.debug("Message reading cancelled")
            raise
        except Exception as e:
            logger.error("Error reading MCP messages", error=str(e))
        finally:
            logger.debug("Stopped reading MCP messages")
    
    async def _cleanup_process(self) -> None:
        """清理进程资源"""
        if not self.process:
            return
        
        try:
            # 关闭stdin
            if self.process.stdin:
                self.process.stdin.close()
                await self.process.stdin.wait_closed()
            
            # 等待进程结束（超时）
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("MCP server process did not exit gracefully, terminating")
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    logger.warning("MCP server process did not terminate, killing")
                    self.process.kill()
                    await self.process.wait()
            
            logger.debug("MCP server process cleaned up", return_code=self.process.returncode)
            
        except Exception as e:
            logger.error("Error cleaning up MCP server process", error=str(e))
        finally:
            self.process = None
    
    def is_alive(self) -> bool:
        """检查进程是否仍在运行"""
        return (
            self.process is not None and 
            self.process.returncode is None and
            self.status == ConnectionStatus.CONNECTED
        )
    
    async def get_stderr_output(self) -> Optional[str]:
        """获取进程的错误输出"""
        if not self.process or not self.process.stderr:
            return None
        
        try:
            # 非阻塞读取stderr
            stderr_data = b""
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        self.process.stderr.read(1024), 
                        timeout=0.1
                    )
                    if not chunk:
                        break
                    stderr_data += chunk
                except asyncio.TimeoutError:
                    break
            
            if stderr_data:
                return stderr_data.decode('utf-8', errors='replace')
            
        except Exception as e:
            logger.warning("Error reading stderr", error=str(e))
        
        return None 