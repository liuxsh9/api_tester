import asyncio
import time
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import logging
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from ..api.client import APIRequestManager, RequestResult

logger = logging.getLogger(__name__)
console = Console()


@dataclass
class LoadTestResult:
    """负载测试结果"""
    concurrent_level: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    total_test_time: float
    error_rate: float
    timeout_count: int
    total_tokens: int
    avg_tokens_per_request: float
    tokens_per_second: float
    results: List[RequestResult]

    def to_dict(self) -> Dict[str, Any]:
        result_dict = asdict(self)
        result_dict['results'] = [r.to_dict() for r in self.results]
        return result_dict


class LoadTestEngine:
    """负载测试引擎"""

    def __init__(self, request_manager: APIRequestManager):
        self.request_manager = request_manager
        self.progress_callback: Optional[Callable] = None

    def set_progress_callback(self, callback: Callable):
        """设置进度回调函数"""
        self.progress_callback = callback

    async def run_concurrent_requests(
        self,
        concurrent_level: int,
        total_requests: int,
        api_key: str,
        endpoint: str = "chat",
        timeout: int = 30,
        **api_kwargs
    ) -> List[RequestResult]:
        """运行并发请求"""

        # 创建信号量控制并发数
        semaphore = asyncio.Semaphore(concurrent_level)

        async def bounded_request():
            async with semaphore:
                return await self.request_manager.send_single_request(
                    api_key=api_key,
                    endpoint=endpoint,
                    timeout=timeout,
                    **api_kwargs
                )

        # 创建任务列表
        tasks = [bounded_request() for _ in range(total_requests)]

        # 执行所有任务
        results = []
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task_id = progress.add_task(
                f"[green]并发 {concurrent_level} | 总计 {total_requests} 请求",
                total=total_requests
            )

            # 分批执行以避免内存过载
            batch_size = min(concurrent_level * 2, 100)
            for i in range(0, len(tasks), batch_size):
                batch_tasks = tasks[i:i + batch_size]
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"请求异常: {result}")
                        # 创建失败的结果记录
                        failed_result = RequestResult(
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
                        )
                        results.append(failed_result)
                    else:
                        results.append(result)

                    progress.update(task_id, advance=1)

                    # 调用进度回调
                    if self.progress_callback:
                        self.progress_callback(len(results), total_requests)

        return results

    def analyze_results(self, results: List[RequestResult], concurrent_level: int) -> LoadTestResult:
        """分析测试结果"""

        if not results:
            return LoadTestResult(
                concurrent_level=concurrent_level,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                avg_response_time=0,
                min_response_time=0,
                max_response_time=0,
                p50_response_time=0,
                p95_response_time=0,
                p99_response_time=0,
                requests_per_second=0,
                total_test_time=0,
                error_rate=0,
                timeout_count=0,
                total_tokens=0,
                avg_tokens_per_request=0,
                tokens_per_second=0,
                results=results
            )

        # 基本统计
        total_requests = len(results)
        successful_requests = sum(1 for r in results if r.success)
        failed_requests = total_requests - successful_requests
        error_rate = failed_requests / total_requests if total_requests > 0 else 0

        # 响应时间统计（只考虑成功的请求）
        successful_results = [r for r in results if r.success and r.response_time > 0]
        response_times = [r.response_time for r in successful_results]

        if response_times:
            response_times.sort()
            avg_response_time = sum(response_times) / len(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)

            # 百分位数计算
            def percentile(data, p):
                k = (len(data) - 1) * p / 100
                f = int(k)
                c = k - f
                if f < len(data) - 1:
                    return data[f] * (1 - c) + data[f + 1] * c
                return data[f]

            p50_response_time = percentile(response_times, 50)
            p95_response_time = percentile(response_times, 95)
            p99_response_time = percentile(response_times, 99)
        else:
            avg_response_time = min_response_time = max_response_time = 0
            p50_response_time = p95_response_time = p99_response_time = 0

        # 计算测试总时间
        timestamps = [r.timestamp for r in results]
        if timestamps:
            test_start_time = min(timestamps)
            test_end_times = [r.timestamp + r.response_time for r in results]
            test_end_time = max(test_end_times)
            total_test_time = test_end_time - test_start_time
        else:
            total_test_time = 0

        # 吞吐量计算
        requests_per_second = successful_requests / total_test_time if total_test_time > 0 else 0

        # 超时统计
        timeout_count = sum(1 for r in results if r.response_time > 1200)

        # Token统计
        total_tokens = sum(r.total_tokens for r in successful_results)
        avg_tokens_per_request = total_tokens / len(successful_results) if successful_results else 0
        tokens_per_second = total_tokens / total_test_time if total_test_time > 0 else 0

        return LoadTestResult(
            concurrent_level=concurrent_level,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p50_response_time=p50_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=requests_per_second,
            total_test_time=total_test_time,
            error_rate=error_rate,
            timeout_count=timeout_count,
            total_tokens=total_tokens,
            avg_tokens_per_request=avg_tokens_per_request,
            tokens_per_second=tokens_per_second,
            results=results
        )

    async def run_load_test(
        self,
        concurrent_levels: List[int],
        requests_per_level: int,
        api_key: str,
        endpoint: str = "chat",
        timeout: int = 30,
        ramp_up_time: int = 5,
        cool_down_time: int = 10,
        **api_kwargs
    ) -> List[LoadTestResult]:
        """运行完整的负载测试"""

        results = []

        console.print(f"[bold green]开始负载测试[/bold green]")
        console.print(f"并发级别: {concurrent_levels}")
        console.print(f"每级别请求数: {requests_per_level}")
        console.print(f"预热时间: {ramp_up_time}s")
        console.print(f"冷却时间: {cool_down_time}s")
        console.print()

        for i, concurrent_level in enumerate(concurrent_levels):
            console.print(f"[bold yellow]第 {i + 1}/{len(concurrent_levels)} 轮测试[/bold yellow]")
            console.print(f"并发数: {concurrent_level}")

            # 预热
            if ramp_up_time > 0:
                console.print(f"预热中 ({ramp_up_time}s)...")
                await asyncio.sleep(ramp_up_time)

            # 执行测试
            start_time = time.time()
            request_results = await self.run_concurrent_requests(
                concurrent_level=concurrent_level,
                total_requests=requests_per_level,
                api_key=api_key,
                endpoint=endpoint,
                timeout=timeout,
                **api_kwargs
            )

            # 分析结果
            load_test_result = self.analyze_results(request_results, concurrent_level)
            results.append(load_test_result)

            # 显示结果摘要
            console.print(f"[green]✓[/green] 完成 - "
                         f"成功: {load_test_result.successful_requests}/{load_test_result.total_requests} "
                         f"({(1-load_test_result.error_rate)*100:.1f}%) | "
                         f"平均响应时间: {load_test_result.avg_response_time:.2f}s | "
                         f"RPS: {load_test_result.requests_per_second:.1f}")

            # 冷却
            if cool_down_time > 0 and i < len(concurrent_levels) - 1:
                console.print(f"冷却中 ({cool_down_time}s)...")
                await asyncio.sleep(cool_down_time)

            console.print()

        console.print(f"[bold green]负载测试完成！[/bold green]")
        return results


class StressTestEngine(LoadTestEngine):
    """压力测试引擎（继承自负载测试引擎）"""

    async def run_stress_test(
        self,
        max_concurrent: int,
        duration_seconds: int,
        api_key: str,
        endpoint: str = "chat",
        timeout: int = 30,
        **api_kwargs
    ) -> LoadTestResult:
        """运行压力测试（在指定时间内持续发送请求）"""

        console.print(f"[bold red]开始压力测试[/bold red]")
        console.print(f"最大并发数: {max_concurrent}")
        console.print(f"持续时间: {duration_seconds}s")
        console.print()

        results = []
        start_time = time.time()
        end_time = start_time + duration_seconds

        # 创建信号量控制并发数
        semaphore = asyncio.Semaphore(max_concurrent)

        async def continuous_request():
            while time.time() < end_time:
                async with semaphore:
                    if time.time() >= end_time:
                        break
                    result = await self.request_manager.send_single_request(
                        api_key=api_key,
                        endpoint=endpoint,
                        timeout=timeout,
                        **api_kwargs
                    )
                    results.append(result)

        # 启动多个持续请求任务
        tasks = [continuous_request() for _ in range(max_concurrent)]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task_id = progress.add_task(
                f"[red]压力测试进行中...",
                total=duration_seconds
            )

            # 监控进度
            while time.time() < end_time:
                elapsed = time.time() - start_time
                progress.update(task_id, completed=elapsed)
                await asyncio.sleep(0.1)

            # 等待所有任务完成
            await asyncio.gather(*tasks, return_exceptions=True)

        # 分析结果
        stress_result = self.analyze_results(results, max_concurrent)
        console.print(f"[green]✓[/green] 压力测试完成 - "
                     f"总请求: {stress_result.total_requests} | "
                     f"成功率: {(1-stress_result.error_rate)*100:.1f}% | "
                     f"平均RPS: {stress_result.requests_per_second:.1f}")

        return stress_result