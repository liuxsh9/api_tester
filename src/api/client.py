import aiohttp
import asyncio
import time
import json
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, asdict
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

logger = logging.getLogger(__name__)


@dataclass
class RequestResult:
    """单次请求结果"""
    timestamp: float
    prompt: str
    response_time: float
    status_code: int
    success: bool
    response_content: str
    error_message: Optional[str]
    input_tokens: int
    output_tokens: int
    total_tokens: int
    content_length: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class APIClient:
    """API客户端"""

    def __init__(self, session: aiohttp.ClientSession):
        self.session = session

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def make_request(
        self,
        url: str,
        headers: Dict[str, str],
        body: Dict[str, Any],
        timeout: int = 30
    ) -> Tuple[int, str, float]:
        """
        发送HTTP请求

        Returns:
            Tuple[status_code, response_text, response_time]
        """
        start_time = time.time()

        try:
            timeout_obj = aiohttp.ClientTimeout(total=timeout)
            async with self.session.post(
                url,
                headers=headers,
                json=body,
                timeout=timeout_obj
            ) as response:
                response_text = await response.text()
                response_time = time.time() - start_time
                return response.status, response_text, response_time

        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"请求失败: {e}")
            raise


class APIRequestManager:
    """API请求管理器"""

    def __init__(self, api_config, prompt_manager):
        self.api_config = api_config
        self.prompt_manager = prompt_manager
        self.session = None

    async def __aenter__(self):
        connector = aiohttp.TCPConnector(limit=1000, limit_per_host=100)
        self.session = aiohttp.ClientSession(connector=connector)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _extract_token_info(self, response_content: str) -> Tuple[int, int, int]:
        """从响应中提取token信息"""
        input_tokens = 0
        output_tokens = 0
        total_tokens = 0

        try:
            response_data = json.loads(response_content)

            if 'usage' in response_data:
                usage = response_data['usage']

                # OpenAI格式 (also used by Volcano Cloud)
                if 'prompt_tokens' in usage:
                    input_tokens = usage.get('prompt_tokens', 0)
                    output_tokens = usage.get('completion_tokens', 0)
                    total_tokens = usage.get('total_tokens', 0)

                # Claude格式
                elif 'input_tokens' in usage:
                    input_tokens = usage.get('input_tokens', 0)
                    output_tokens = usage.get('output_tokens', 0)
                    total_tokens = input_tokens + output_tokens

        except (json.JSONDecodeError, KeyError):
            pass

        return input_tokens, output_tokens, total_tokens

    async def send_single_request(
        self,
        api_key: str,
        endpoint: str = "chat",
        timeout: int = 30,
        **api_kwargs
    ) -> RequestResult:
        """发送单次请求"""

        prompt = self.prompt_manager.get_next_prompt()
        timestamp = time.time()

        try:
            # 构建请求参数
            url = self.api_config.format_url(endpoint, **api_kwargs)
            headers = self.api_config.format_headers(api_key=api_key, **api_kwargs)
            body = self.api_config.format_request_body(prompt, **api_kwargs)

            # 发送请求
            client = APIClient(self.session)
            status_code, response_content, response_time = await client.make_request(
                url, headers, body, timeout
            )

            # 提取token信息
            input_tokens, output_tokens, total_tokens = self._extract_token_info(response_content)

            return RequestResult(
                timestamp=timestamp,
                prompt=prompt,
                response_time=response_time,
                status_code=status_code,
                success=200 <= status_code < 300,
                response_content=response_content,
                error_message=None,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                content_length=len(response_content)
            )

        except Exception as e:
            error_message = str(e)
            logger.error(f"请求异常: {error_message}")

            return RequestResult(
                timestamp=timestamp,
                prompt=prompt,
                response_time=time.time() - timestamp,
                status_code=0,
                success=False,
                response_content="",
                error_message=error_message,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                content_length=0
            )

    async def send_batch_requests(
        self,
        request_count: int,
        api_key: str,
        endpoint: str = "chat",
        timeout: int = 30,
        **api_kwargs
    ) -> List[RequestResult]:
        """发送批量请求"""

        tasks = []
        for _ in range(request_count):
            task = self.send_single_request(
                api_key=api_key,
                endpoint=endpoint,
                timeout=timeout,
                **api_kwargs
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常结果
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"批量请求中的异常: {result}")
                processed_results.append(RequestResult(
                    timestamp=time.time(),
                    prompt="",
                    response_time=0,
                    status_code=0,
                    success=False,
                    response_content="",
                    error_message=str(result),
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                    content_length=0
                ))
            else:
                processed_results.append(result)

        return processed_results