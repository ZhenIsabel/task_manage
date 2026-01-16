"""LLM服务 - 通用的LLM消息收发和解析服务"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, Union
from config.config_manager import load_config

try:
    from volcenginesdkarkruntime import AsyncArk
except ImportError:
    AsyncArk = None

logger = logging.getLogger(__name__)


class LLMService:
    """通用LLM服务类 - 只负责消息收发和响应解析"""
    
    def __init__(self):
        """初始化LLM服务"""
        self.config = load_config()
        
        # 获取LLM配置
        llm_config = self.config.get("LLM_CONFIG", {})
        self.api_key = llm_config.get("api_key", "")
        self.model = llm_config.get("model", "ep-20250103125953-fwvmj")  # 默认模型
        self.base_url = llm_config.get("base_url", "https://ark.cn-beijing.volces.com/api/v3")
        
        # 初始化客户端
        self.client = None
        if AsyncArk and self.api_key:
            try:
                self.client = AsyncArk(
                    base_url=self.base_url,
                    api_key=self.api_key,
                )
                logger.info("LLM服务初始化成功")
            except Exception as e:
                logger.error(f"初始化LLM客户端失败: {str(e)}")
        else:
            if not AsyncArk:
                logger.warning("未安装volcenginesdkarkruntime，LLM功能将不可用")
            if not self.api_key:
                logger.warning("未配置API Key，LLM功能将不可用")
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        schema:dict,
        max_retries: int = 2
    ) -> Optional[str]:
        """
        发送消息并获取响应（异步）
        
        Args:
            messages: 消息列表，格式为 [{"role": "system/user/assistant", "content": "..."}]
            schema: JSON Schema配置
            max_retries: 最大重试次数
            
        Returns:
            LLM的响应文本，失败返回None
        """
        if not self.client:
            logger.error("LLM客户端未初始化，无法发送消息")
            return None
        
        if not messages:
            logger.warning("消息列表为空")
            return None
        
        # 构建JSON Schema格式的response_format
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "summary",
                "schema": schema,
                "strict": True
            }
        }
        
        # 重试逻辑
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    # 重试前等待一小段时间
                    await asyncio.sleep(1 * attempt)
                    logger.info(f"第 {attempt + 1} 次尝试调用LLM API")
                else:
                    logger.debug(f"发送消息到LLM，消息数量: {len(messages)}")
                
                # 调用API
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format=response_format
                )
                
                # 获取响应内容
                content = response.choices[0].message.content
                logger.debug(f"LLM响应内容长度: {len(content) if content else 0} 字符")
                
                if attempt > 0:
                    logger.info(f"重试成功，第 {attempt + 1} 次尝试获得响应")
                
                return content
                    
            except Exception as e:
                last_exception = e
                error_str = str(e)
                
                # 判断是否是可重试的错误
                is_retryable = (
                    "Connection error" in error_str or
                    "timeout" in error_str.lower() or
                    "Timeout" in error_str
                )
                
                if is_retryable and attempt < max_retries:
                    logger.warning(f"LLM API调用失败(第 {attempt + 1} 次): {error_str}，将重试")
                    continue
                else:
                    logger.error(f"LLM API调用失败: {str(e)}", exc_info=True)
                    break
        
        return None
    
    def generate_response_sync(
        self,
        messages: List[Dict[str, str]],
        schema:dict
    ) -> Optional[str]:
        """
        发送消息并获取响应（同步版本，用于非异步环境）
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大生成token数
            
        Returns:
            LLM的响应文本，失败返回None
        """
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    self.generate_response(messages, schema)
                )
                
                # 等待当前事件循环中所有待处理的任务完成
                pending = asyncio.all_tasks(loop)
                if pending:
                    for task in pending:
                        task.cancel()
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                
                return result
            finally:
                # 只关闭事件循环,不关闭共享的httpx客户端
                # 因为LLMService是单例,多个线程共享同一个客户端
                loop.close()
                
        except Exception as e:
            logger.error(f"同步调用LLM失败: {str(e)}", exc_info=True)
            return None
    
    @staticmethod
    def parse_json_response(content: str) -> Optional[Union[Dict, List]]:
        """
        解析LLM返回的JSON内容
        
        Args:
            content: LLM返回的文本内容
            
        Returns:
            解析后的Python对象（dict或list），失败返回None
        """
        if not content:
            logger.warning("响应内容为空")
            return None
        
        try:
            # 清理可能的markdown代码块标记
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            
            if content.endswith("```"):
                content = content[:-3]
            
            content = content.strip()
            
            # 解析JSON
            result = json.loads(content)
            logger.debug(f"成功解析JSON，类型: {type(result)}")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"解析JSON失败: {str(e)}\n内容: {content[:200]}...")
            return None
    
    def is_available(self) -> bool:
        """检查LLM服务是否可用"""
        return self.client is not None


# 全局单例
_llm_service_instance = None


def get_llm_service() -> LLMService:
    """获取LLM服务单例"""
    global _llm_service_instance
    if _llm_service_instance is None:
        _llm_service_instance = LLMService()
    return _llm_service_instance
