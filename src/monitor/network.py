import asyncio
import aiohttp
import time
import statistics
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urlparse
import socket
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


@dataclass
class PingResult:
    """Ping测试结果"""
    timestamp: float
    host: str
    ip_address: str
    response_time: float
    success: bool
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NetworkStats:
    """网络统计信息"""
    host: str
    total_pings: int
    successful_pings: int
    failed_pings: int
    success_rate: float
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    std_response_time: float
    packet_loss: float
    jitter: float
    ping_results: List[PingResult]

    def to_dict(self) -> Dict[str, Any]:
        result_dict = asdict(self)
        result_dict['ping_results'] = [r.to_dict() for r in self.ping_results]
        return result_dict


class NetworkMonitor:
    """网络监控器"""

    def __init__(self, ping_interval: int = 5, timeout: int = 10):
        self.ping_interval = ping_interval
        self.timeout = timeout
        self.monitoring = False
        self.ping_results: Dict[str, List[PingResult]] = {}
        self.executor = ThreadPoolExecutor(max_workers=10)

    def _resolve_hostname(self, hostname: str) -> str:
        """解析主机名到IP地址"""
        try:
            return socket.gethostbyname(hostname)
        except socket.gaierror:
            return hostname

    async def _tcp_ping(self, host: str, port: int = 80) -> PingResult:
        """TCP连接测试"""
        timestamp = time.time()
        ip_address = self._resolve_hostname(host)

        try:
            start_time = time.time()

            # 使用asyncio进行TCP连接测试
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip_address, port),
                    timeout=self.timeout
                )
                writer.close()
                await writer.wait_closed()

                response_time = (time.time() - start_time) * 1000  # 转换为毫秒

                return PingResult(
                    timestamp=timestamp,
                    host=host,
                    ip_address=ip_address,
                    response_time=response_time,
                    success=True
                )

            except asyncio.TimeoutError:
                response_time = self.timeout * 1000
                return PingResult(
                    timestamp=timestamp,
                    host=host,
                    ip_address=ip_address,
                    response_time=response_time,
                    success=False,
                    error_message="连接超时"
                )

        except Exception as e:
            return PingResult(
                timestamp=timestamp,
                host=host,
                ip_address=ip_address,
                response_time=0,
                success=False,
                error_message=str(e)
            )

    async def _http_ping(self, url: str) -> PingResult:
        """HTTP健康检查"""
        timestamp = time.time()
        parsed_url = urlparse(url)
        host = parsed_url.hostname
        ip_address = self._resolve_hostname(host) if host else "unknown"

        try:
            start_time = time.time()

            timeout_obj = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                async with session.head(url) as response:
                    response_time = (time.time() - start_time) * 1000
                    success = 200 <= response.status < 400

                    return PingResult(
                        timestamp=timestamp,
                        host=host,
                        ip_address=ip_address,
                        response_time=response_time,
                        success=success,
                        error_message=None if success else f"HTTP {response.status}"
                    )

        except asyncio.TimeoutError:
            response_time = self.timeout * 1000
            return PingResult(
                timestamp=timestamp,
                host=host,
                ip_address=ip_address,
                response_time=response_time,
                success=False,
                error_message="HTTP请求超时"
            )
        except Exception as e:
            return PingResult(
                timestamp=timestamp,
                host=host,
                ip_address=ip_address,
                response_time=0,
                success=False,
                error_message=str(e)
            )

    async def ping_host(self, target: str, method: str = "tcp") -> PingResult:
        """单次ping测试"""
        if method == "http" or target.startswith(("http://", "https://")):
            return await self._http_ping(target)
        else:
            # 解析主机和端口
            if ":" in target and not target.startswith("http"):
                host, port = target.rsplit(":", 1)
                port = int(port)
            else:
                host = target
                port = 80

            return await self._tcp_ping(host, port)

    async def start_monitoring(self, targets: List[str], method: str = "tcp"):
        """开始监控"""
        self.monitoring = True
        self.ping_results = {target: [] for target in targets}

        logger.info(f"开始监控 {len(targets)} 个目标")

        try:
            while self.monitoring:
                # 并发ping所有目标
                tasks = [self.ping_host(target, method) for target in targets]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # 保存结果
                for target, result in zip(targets, results):
                    if isinstance(result, Exception):
                        logger.error(f"监控异常 {target}: {result}")
                        continue

                    self.ping_results[target].append(result)

                    # 限制保存的结果数量（避免内存过载）
                    if len(self.ping_results[target]) > 1000:
                        self.ping_results[target] = self.ping_results[target][-500:]

                # 等待下次监控
                await asyncio.sleep(self.ping_interval)

        except Exception as e:
            logger.error(f"监控过程中发生异常: {e}")
        finally:
            logger.info("网络监控已停止")

    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False

    def get_network_stats(self, target: str) -> Optional[NetworkStats]:
        """获取网络统计信息"""
        if target not in self.ping_results:
            return None

        results = self.ping_results[target]
        if not results:
            return None

        total_pings = len(results)
        successful_results = [r for r in results if r.success]
        successful_pings = len(successful_results)
        failed_pings = total_pings - successful_pings
        success_rate = successful_pings / total_pings if total_pings > 0 else 0
        packet_loss = failed_pings / total_pings if total_pings > 0 else 0

        if successful_results:
            response_times = [r.response_time for r in successful_results]
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            std_response_time = statistics.stdev(response_times) if len(response_times) > 1 else 0

            # 计算抖动（相邻测量值的平均差异）
            if len(response_times) > 1:
                jitter = statistics.mean(
                    abs(response_times[i] - response_times[i-1])
                    for i in range(1, len(response_times))
                )
            else:
                jitter = 0
        else:
            avg_response_time = min_response_time = max_response_time = 0
            std_response_time = jitter = 0

        return NetworkStats(
            host=target,
            total_pings=total_pings,
            successful_pings=successful_pings,
            failed_pings=failed_pings,
            success_rate=success_rate,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            std_response_time=std_response_time,
            packet_loss=packet_loss,
            jitter=jitter,
            ping_results=results
        )

    def get_all_stats(self) -> Dict[str, NetworkStats]:
        """获取所有目标的统计信息"""
        stats = {}
        for target in self.ping_results.keys():
            stat = self.get_network_stats(target)
            if stat:
                stats[target] = stat
        return stats

    def clear_results(self, target: Optional[str] = None):
        """清除结果"""
        if target:
            if target in self.ping_results:
                self.ping_results[target] = []
        else:
            self.ping_results = {}


class LatencyObserver:
    """延时观测器"""

    def __init__(self):
        self.observations: List[Dict[str, Any]] = []

    def record_latency(
        self,
        operation: str,
        latency: float,
        timestamp: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """记录延时"""
        observation = {
            'timestamp': timestamp or time.time(),
            'operation': operation,
            'latency': latency,
            'metadata': metadata or {}
        }
        self.observations.append(observation)

    def get_latency_stats(
        self,
        operation: Optional[str] = None,
        time_window: Optional[float] = None
    ) -> Dict[str, Any]:
        """获取延时统计"""
        # 过滤观测数据
        filtered_observations = self.observations

        if operation:
            filtered_observations = [
                obs for obs in filtered_observations
                if obs['operation'] == operation
            ]

        if time_window:
            cutoff_time = time.time() - time_window
            filtered_observations = [
                obs for obs in filtered_observations
                if obs['timestamp'] >= cutoff_time
            ]

        if not filtered_observations:
            return {
                'count': 0,
                'avg_latency': 0,
                'min_latency': 0,
                'max_latency': 0,
                'p50_latency': 0,
                'p95_latency': 0,
                'p99_latency': 0
            }

        latencies = [obs['latency'] for obs in filtered_observations]
        latencies.sort()

        def percentile(data, p):
            k = (len(data) - 1) * p / 100
            f = int(k)
            c = k - f
            if f < len(data) - 1:
                return data[f] * (1 - c) + data[f + 1] * c
            return data[f]

        return {
            'count': len(latencies),
            'avg_latency': statistics.mean(latencies),
            'min_latency': min(latencies),
            'max_latency': max(latencies),
            'p50_latency': percentile(latencies, 50),
            'p95_latency': percentile(latencies, 95),
            'p99_latency': percentile(latencies, 99)
        }

    def clear_observations(self, operation: Optional[str] = None):
        """清除观测数据"""
        if operation:
            self.observations = [
                obs for obs in self.observations
                if obs['operation'] != operation
            ]
        else:
            self.observations = []