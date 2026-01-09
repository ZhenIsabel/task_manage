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
        schema:dict
    ) -> Optional[str]:
        """
        发送消息并获取响应（异步）
        
        Args:
            messages: 消息列表，格式为 [{"role": "system/user/assistant", "content": "..."}]
            temperature: 温度参数，控制生成的随机性 (0-1)
            max_tokens: 最大生成token数
            
        Returns:
            LLM的响应文本，失败返回None
        """
        if not self.client:
            logger.error("LLM客户端未初始化，无法发送消息")
            return None
        
        if not messages:
            logger.warning("消息列表为空")
            return None
        
        try:
            logger.debug(f"发送消息到LLM，消息数量: {len(messages)}")
            
            # 构建JSON Schema格式的response_format
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "summary",
                    "schema": schema,
                    "strict": True
                }
            }
            
            # 调用API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format=response_format
            )
            
            # 获取响应内容
            content = response.choices[0].message.content
            logger.debug(f"LLM响应内容长度: {len(content) if content else 0} 字符")
            
            return content
                
        except Exception as e:
            logger.error(f"LLM API调用失败: {str(e)}", exc_info=True)
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
        # #region agent log
        import json as _json; _log_file = r"d:\solutions\task_manage\.cursor\debug.log"; _log_data = {"sessionId":"debug-session","runId":"initial","hypothesisId":"A","location":"LLMService.py:101","message":"generate_response_sync entry","data":{"thread_id":__import__('threading').current_thread().ident,"has_client":self.client is not None},"timestamp":__import__('time').time()*1000}
        try:
            with open(_log_file, "a", encoding="utf-8") as _f: _f.write(_json.dumps(_log_data, ensure_ascii=False) + "\n")
        except: pass
        # #endregion
        
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # #region agent log
            import json as _json; _log_file = r"d:\solutions\task_manage\.cursor\debug.log"; _log_data = {"sessionId":"debug-session","runId":"initial","hypothesisId":"A","location":"LLMService.py:120","message":"event loop created","data":{"loop_id":id(loop),"is_running":loop.is_running(),"is_closed":loop.is_closed()},"timestamp":__import__('time').time()*1000}
            try:
                with open(_log_file, "a", encoding="utf-8") as _f: _f.write(_json.dumps(_log_data, ensure_ascii=False) + "\n")
            except: pass
            # #endregion
            
            try:
                result = loop.run_until_complete(
                    self.generate_response(messages, schema)
                )
                
                # #region agent log
                import json as _json; _log_file = r"d:\solutions\task_manage\.cursor\debug.log"; _log_data = {"sessionId":"debug-session","runId":"initial","hypothesisId":"A","location":"LLMService.py:130","message":"API call completed","data":{"loop_id":id(loop),"has_result":result is not None,"result_length":len(result) if result else 0},"timestamp":__import__('time').time()*1000}
                try:
                    with open(_log_file, "a", encoding="utf-8") as _f: _f.write(_json.dumps(_log_data, ensure_ascii=False) + "\n")
                except: pass
                # #endregion
                
                # 确保客户端的所有待处理任务都已完成
                if self.client and hasattr(self.client, '_client'):
                    # #region agent log
                    import json as _json; _log_file = r"d:\solutions\task_manage\.cursor\debug.log"; _log_data = {"sessionId":"debug-session","runId":"initial","hypothesisId":"D","location":"LLMService.py:138","message":"before client cleanup","data":{"loop_id":id(loop),"client_type":type(self.client).__name__},"timestamp":__import__('time').time()*1000}
                    try:
                        with open(_log_file, "a", encoding="utf-8") as _f: _f.write(_json.dumps(_log_data, ensure_ascii=False) + "\n")
                    except: pass
                    # #endregion
                    
                    # 关闭底层的httpx客户端
                    try:
                        loop.run_until_complete(self.client._client.aclose())
                    except Exception as cleanup_error:
                        logger.warning(f"清理httpx客户端时出错: {str(cleanup_error)}")
                    
                    # #region agent log
                    import json as _json; _log_file = r"d:\solutions\task_manage\.cursor\debug.log"; _log_data = {"sessionId":"debug-session","runId":"initial","hypothesisId":"D","location":"LLMService.py:150","message":"after client cleanup","data":{"loop_id":id(loop)},"timestamp":__import__('time').time()*1000}
                    try:
                        with open(_log_file, "a", encoding="utf-8") as _f: _f.write(_json.dumps(_log_data, ensure_ascii=False) + "\n")
                    except: pass
                    # #endregion
                
                # 等待所有待处理的任务完成
                pending = asyncio.all_tasks(loop)
                if pending:
                    # #region agent log
                    import json as _json; _log_file = r"d:\solutions\task_manage\.cursor\debug.log"; _log_data = {"sessionId":"debug-session","runId":"initial","hypothesisId":"C","location":"LLMService.py:161","message":"pending tasks found","data":{"loop_id":id(loop),"pending_count":len(pending),"tasks":[str(t) for t in pending]},"timestamp":__import__('time').time()*1000}
                    try:
                        with open(_log_file, "a", encoding="utf-8") as _f: _f.write(_json.dumps(_log_data, ensure_ascii=False) + "\n")
                    except: pass
                    # #endregion
                    
                    for task in pending:
                        task.cancel()
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                
                return result
            finally:
                # #region agent log
                import json as _json; _log_file = r"d:\solutions\task_manage\.cursor\debug.log"; _log_data = {"sessionId":"debug-session","runId":"initial","hypothesisId":"C","location":"LLMService.py:175","message":"before loop close","data":{"loop_id":id(loop),"is_running":loop.is_running(),"is_closed":loop.is_closed()},"timestamp":__import__('time').time()*1000}
                try:
                    with open(_log_file, "a", encoding="utf-8") as _f: _f.write(_json.dumps(_log_data, ensure_ascii=False) + "\n")
                except: pass
                # #endregion
                
                loop.close()
                
                # #region agent log
                import json as _json; _log_file = r"d:\solutions\task_manage\.cursor\debug.log"; _log_data = {"sessionId":"debug-session","runId":"initial","hypothesisId":"C","location":"LLMService.py:185","message":"after loop close","data":{"loop_id":id(loop),"is_closed":loop.is_closed()},"timestamp":__import__('time').time()*1000}
                try:
                    with open(_log_file, "a", encoding="utf-8") as _f: _f.write(_json.dumps(_log_data, ensure_ascii=False) + "\n")
                except: pass
                # #endregion
                
        except Exception as e:
            # #region agent log
            import json as _json; _log_file = r"d:\solutions\task_manage\.cursor\debug.log"; _log_data = {"sessionId":"debug-session","runId":"initial","hypothesisId":"E","location":"LLMService.py:195","message":"exception in generate_response_sync","data":{"error_type":type(e).__name__,"error_msg":str(e),"thread_id":__import__('threading').current_thread().ident},"timestamp":__import__('time').time()*1000}
            try:
                with open(_log_file, "a", encoding="utf-8") as _f: _f.write(_json.dumps(_log_data, ensure_ascii=False) + "\n")
            except: pass
            # #endregion
            
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
