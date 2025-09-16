import sqlite3
import json
import time
import statistics
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import asdict
import pandas as pd
import numpy as np

from ..engine.load_test import LoadTestResult, RequestResult
from ..monitor.network import NetworkStats


class TestDatabase:
    """测试结果数据库"""

    def __init__(self, db_path: str = "data/test_results.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS test_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE,
                    api_name TEXT,
                    test_config TEXT,
                    start_time REAL,
                    end_time REAL,
                    total_requests INTEGER,
                    successful_requests INTEGER,
                    failed_requests INTEGER,
                    avg_response_time REAL,
                    max_concurrent INTEGER,
                    metadata TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS load_test_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    concurrent_level INTEGER,
                    total_requests INTEGER,
                    successful_requests INTEGER,
                    failed_requests INTEGER,
                    avg_response_time REAL,
                    min_response_time REAL,
                    max_response_time REAL,
                    p50_response_time REAL,
                    p95_response_time REAL,
                    p99_response_time REAL,
                    requests_per_second REAL,
                    total_test_time REAL,
                    error_rate REAL,
                    timeout_count INTEGER,
                    total_tokens INTEGER,
                    avg_tokens_per_request REAL,
                    tokens_per_second REAL,
                    FOREIGN KEY (session_id) REFERENCES test_sessions (session_id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS request_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    concurrent_level INTEGER,
                    timestamp REAL,
                    prompt TEXT,
                    response_time REAL,
                    status_code INTEGER,
                    success BOOLEAN,
                    error_message TEXT,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    total_tokens INTEGER,
                    content_length INTEGER,
                    FOREIGN KEY (session_id) REFERENCES test_sessions (session_id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS network_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    host TEXT,
                    timestamp REAL,
                    total_pings INTEGER,
                    successful_pings INTEGER,
                    success_rate REAL,
                    avg_response_time REAL,
                    packet_loss REAL,
                    jitter REAL,
                    FOREIGN KEY (session_id) REFERENCES test_sessions (session_id)
                )
            """)

    def save_test_session(
        self,
        session_id: str,
        api_name: str,
        test_config: str,
        start_time: float,
        end_time: float,
        load_results: List[LoadTestResult],
        network_stats: Optional[Dict[str, NetworkStats]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """保存完整的测试会话"""

        # 计算汇总统计
        total_requests = sum(r.total_requests for r in load_results)
        successful_requests = sum(r.successful_requests for r in load_results)
        failed_requests = sum(r.failed_requests for r in load_results)
        avg_response_time = statistics.mean([r.avg_response_time for r in load_results if r.avg_response_time > 0])
        max_concurrent = max([r.concurrent_level for r in load_results]) if load_results else 0

        with sqlite3.connect(self.db_path) as conn:
            # 保存测试会话
            conn.execute("""
                INSERT OR REPLACE INTO test_sessions
                (session_id, api_name, test_config, start_time, end_time,
                 total_requests, successful_requests, failed_requests,
                 avg_response_time, max_concurrent, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, api_name, test_config, start_time, end_time,
                total_requests, successful_requests, failed_requests,
                avg_response_time, max_concurrent, json.dumps(metadata or {})
            ))

            # 保存负载测试结果
            for result in load_results:
                conn.execute("""
                    INSERT INTO load_test_results
                    (session_id, concurrent_level, total_requests, successful_requests,
                     failed_requests, avg_response_time, min_response_time, max_response_time,
                     p50_response_time, p95_response_time, p99_response_time,
                     requests_per_second, total_test_time, error_rate, timeout_count,
                     total_tokens, avg_tokens_per_request, tokens_per_second)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id, result.concurrent_level, result.total_requests,
                    result.successful_requests, result.failed_requests,
                    result.avg_response_time, result.min_response_time, result.max_response_time,
                    result.p50_response_time, result.p95_response_time, result.p99_response_time,
                    result.requests_per_second, result.total_test_time, result.error_rate,
                    result.timeout_count, result.total_tokens, result.avg_tokens_per_request,
                    result.tokens_per_second
                ))

                # 保存详细的请求结果
                for req_result in result.results:
                    conn.execute("""
                        INSERT INTO request_results
                        (session_id, concurrent_level, timestamp, prompt, response_time,
                         status_code, success, error_message, input_tokens, output_tokens,
                         total_tokens, content_length)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        session_id, result.concurrent_level, req_result.timestamp,
                        req_result.prompt, req_result.response_time, req_result.status_code,
                        req_result.success, req_result.error_message, req_result.input_tokens,
                        req_result.output_tokens, req_result.total_tokens, req_result.content_length
                    ))

            # 保存网络统计
            if network_stats:
                for host, stats in network_stats.items():
                    conn.execute("""
                        INSERT INTO network_stats
                        (session_id, host, timestamp, total_pings, successful_pings,
                         success_rate, avg_response_time, packet_loss, jitter)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        session_id, host, time.time(), stats.total_pings,
                        stats.successful_pings, stats.success_rate, stats.avg_response_time,
                        stats.packet_loss, stats.jitter
                    ))

    def get_test_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取测试会话列表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM test_sessions
                ORDER BY start_time DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_load_test_results(self, session_id: str) -> List[LoadTestResult]:
        """获取指定会话的负载测试结果"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM load_test_results
                WHERE session_id = ?
                ORDER BY concurrent_level
            """, (session_id,))

            results = []
            for row in cursor.fetchall():
                row_dict = dict(row)

                # 获取详细的请求结果
                req_cursor = conn.execute("""
                    SELECT * FROM request_results
                    WHERE session_id = ? AND concurrent_level = ?
                """, (session_id, row_dict['concurrent_level']))

                request_results = []
                for req_row in req_cursor.fetchall():
                    req_dict = dict(req_row)
                    request_results.append(RequestResult(
                        timestamp=req_dict['timestamp'],
                        prompt=req_dict['prompt'],
                        response_time=req_dict['response_time'],
                        status_code=req_dict['status_code'],
                        success=bool(req_dict['success']),
                        response_content="",  # 不保存响应内容以节省空间
                        error_message=req_dict['error_message'],
                        input_tokens=req_dict['input_tokens'],
                        output_tokens=req_dict['output_tokens'],
                        total_tokens=req_dict['total_tokens'],
                        content_length=req_dict['content_length']
                    ))

                # 重构LoadTestResult
                row_dict['results'] = request_results
                results.append(LoadTestResult(**row_dict))

            return results


class DataAnalyzer:
    """数据分析器"""

    def __init__(self, database: TestDatabase):
        self.database = database

    def analyze_performance_trends(
        self,
        api_name: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """分析性能趋势"""

        cutoff_time = time.time() - (days * 24 * 3600)

        with sqlite3.connect(self.database.db_path) as conn:
            query = """
                SELECT
                    DATE(start_time, 'unixepoch') as test_date,
                    api_name,
                    AVG(avg_response_time) as avg_response_time,
                    AVG(total_requests) as avg_total_requests,
                    AVG(CAST(successful_requests AS FLOAT) / total_requests) as avg_success_rate,
                    COUNT(*) as test_count
                FROM test_sessions
                WHERE start_time >= ?
            """

            params = [cutoff_time]
            if api_name:
                query += " AND api_name = ?"
                params.append(api_name)

            query += """
                GROUP BY test_date, api_name
                ORDER BY test_date DESC
            """

            df = pd.read_sql_query(query, conn, params=params)

            if df.empty:
                return {"message": "没有找到数据"}

            # 计算趋势
            trends = {}

            if len(df) > 1:
                # 响应时间趋势
                response_time_trend = np.polyfit(range(len(df)), df['avg_response_time'], 1)[0]
                trends['response_time_trend'] = 'improving' if response_time_trend < 0 else 'degrading'

                # 成功率趋势
                success_rate_trend = np.polyfit(range(len(df)), df['avg_success_rate'], 1)[0]
                trends['success_rate_trend'] = 'improving' if success_rate_trend > 0 else 'degrading'

            return {
                'data': df.to_dict('records'),
                'trends': trends,
                'summary': {
                    'avg_response_time': df['avg_response_time'].mean(),
                    'avg_success_rate': df['avg_success_rate'].mean(),
                    'total_tests': df['test_count'].sum()
                }
            }

    def compare_apis(self, days: int = 30) -> Dict[str, Any]:
        """比较不同API的性能"""

        cutoff_time = time.time() - (days * 24 * 3600)

        with sqlite3.connect(self.database.db_path) as conn:
            query = """
                SELECT
                    api_name,
                    AVG(avg_response_time) as avg_response_time,
                    AVG(CAST(successful_requests AS FLOAT) / total_requests) as avg_success_rate,
                    COUNT(*) as test_count,
                    SUM(total_requests) as total_requests,
                    MIN(avg_response_time) as min_response_time,
                    MAX(avg_response_time) as max_response_time
                FROM test_sessions
                WHERE start_time >= ?
                GROUP BY api_name
                ORDER BY avg_response_time
            """

            df = pd.read_sql_query(query, conn, params=[cutoff_time])

            if df.empty:
                return {"message": "没有找到数据"}

            # 性能排名
            df['response_time_rank'] = df['avg_response_time'].rank()
            df['success_rate_rank'] = df['avg_success_rate'].rank(ascending=False)
            df['overall_rank'] = (df['response_time_rank'] + df['success_rate_rank']) / 2

            return {
                'comparison': df.to_dict('records'),
                'best_performance': df.loc[df['overall_rank'].idxmin()].to_dict(),
                'fastest_api': df.loc[df['avg_response_time'].idxmin()].to_dict(),
                'most_reliable': df.loc[df['avg_success_rate'].idxmax()].to_dict()
            }

    def analyze_concurrency_impact(self, session_id: str) -> Dict[str, Any]:
        """分析并发级别对性能的影响"""

        with sqlite3.connect(self.database.db_path) as conn:
            query = """
                SELECT
                    concurrent_level,
                    avg_response_time,
                    requests_per_second,
                    error_rate,
                    p95_response_time,
                    total_tokens,
                    tokens_per_second
                FROM load_test_results
                WHERE session_id = ?
                ORDER BY concurrent_level
            """

            df = pd.read_sql_query(query, conn, params=[session_id])

            if df.empty:
                return {"message": "没有找到数据"}

            # 寻找最优并发数
            # 综合考虑吞吐量和响应时间
            df['efficiency_score'] = df['requests_per_second'] / (df['avg_response_time'] + 0.1)
            optimal_concurrency = df.loc[df['efficiency_score'].idxmax()]

            # 分析性能拐点
            performance_analysis = {
                'optimal_concurrency': optimal_concurrency.to_dict(),
                'max_throughput': df.loc[df['requests_per_second'].idxmax()].to_dict(),
                'min_latency': df.loc[df['avg_response_time'].idxmin()].to_dict(),
                'data': df.to_dict('records')
            }

            # 查找性能下降点
            if len(df) > 2:
                throughput_decline_point = None
                for i in range(1, len(df)):
                    if df.iloc[i]['requests_per_second'] < df.iloc[i-1]['requests_per_second'] * 0.95:
                        throughput_decline_point = df.iloc[i-1].to_dict()
                        break

                if throughput_decline_point:
                    performance_analysis['throughput_decline_point'] = throughput_decline_point

            return performance_analysis

    def generate_summary_stats(self, session_id: str) -> Dict[str, Any]:
        """生成测试摘要统计"""

        with sqlite3.connect(self.database.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # 获取会话信息
            session_cursor = conn.execute("""
                SELECT * FROM test_sessions WHERE session_id = ?
            """, (session_id,))
            session_info = dict(session_cursor.fetchone() or {})

            # 获取负载测试统计
            load_cursor = conn.execute("""
                SELECT
                    SUM(total_requests) as total_requests,
                    SUM(successful_requests) as successful_requests,
                    SUM(failed_requests) as failed_requests,
                    AVG(avg_response_time) as avg_response_time,
                    MIN(min_response_time) as min_response_time,
                    MAX(max_response_time) as max_response_time,
                    AVG(p95_response_time) as avg_p95_response_time,
                    SUM(total_tokens) as total_tokens,
                    SUM(timeout_count) as total_timeouts
                FROM load_test_results
                WHERE session_id = ?
            """, (session_id,))
            load_stats = dict(load_cursor.fetchone() or {})

            # 获取错误分布
            error_cursor = conn.execute("""
                SELECT
                    error_message,
                    COUNT(*) as count
                FROM request_results
                WHERE session_id = ? AND success = 0 AND error_message IS NOT NULL
                GROUP BY error_message
                ORDER BY count DESC
            """, (session_id,))
            error_distribution = [dict(row) for row in error_cursor.fetchall()]

            # 计算性能指标
            success_rate = 0
            if load_stats.get('total_requests', 0) > 0:
                success_rate = load_stats['successful_requests'] / load_stats['total_requests']

            summary = {
                'session_info': session_info,
                'performance_metrics': {
                    'total_requests': load_stats.get('total_requests', 0),
                    'successful_requests': load_stats.get('successful_requests', 0),
                    'failed_requests': load_stats.get('failed_requests', 0),
                    'success_rate': success_rate,
                    'avg_response_time': load_stats.get('avg_response_time', 0),
                    'min_response_time': load_stats.get('min_response_time', 0),
                    'max_response_time': load_stats.get('max_response_time', 0),
                    'avg_p95_response_time': load_stats.get('avg_p95_response_time', 0),
                    'total_tokens': load_stats.get('total_tokens', 0),
                    'total_timeouts': load_stats.get('total_timeouts', 0)
                },
                'error_distribution': error_distribution
            }

            return summary