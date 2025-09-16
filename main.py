import asyncio
import click
import uuid
import time
import json
from rich.console import Console
from rich.table import Table
from pathlib import Path

from src.api.config import ConfigManager, PromptManager
from src.api.client import APIRequestManager
from src.engine.load_test import LoadTestEngine, StressTestEngine
from src.monitor.network import NetworkMonitor
from src.stats.analyzer import TestDatabase, DataAnalyzer
from src.report.generator import ReportManager

console = Console()


@click.group()
def cli():
    """大模型API压力测试系统"""
    pass


@cli.command()
@click.option('--api', '-a', required=True, help='API配置名称')
@click.option('--test-config', '-t', default='default', help='测试配置名称')
@click.option('--api-key', '-k', required=True, help='API密钥')
@click.option('--endpoint', '-e', default='chat', help='API端点')
@click.option('--resource-name', help='Azure资源名称（仅Azure OpenAI需要）')
@click.option('--deployment-name', help='Azure部署名称（仅Azure OpenAI需要）')
@click.option('--concurrent-levels', help='自定义并发级别，用逗号分隔，如：1,5,10,20')
@click.option('--requests-per-level', type=int, help='每个并发级别的请求数')
@click.option('--timeout', type=int, help='请求超时时间（秒）')
@click.option('--report-formats', default='html,excel', help='报告格式，用逗号分隔：html,excel,pdf')
@click.option('--session-id', help='自定义会话ID')
def test(api, test_config, api_key, endpoint, resource_name, deployment_name,
         concurrent_levels, requests_per_level, timeout, report_formats, session_id):
    """运行负载测试"""

    asyncio.run(_run_load_test(
        api=api,
        test_config=test_config,
        api_key=api_key,
        endpoint=endpoint,
        resource_name=resource_name,
        deployment_name=deployment_name,
        concurrent_levels=concurrent_levels,
        requests_per_level=requests_per_level,
        timeout=timeout,
        report_formats=report_formats,
        session_id=session_id
    ))


async def _run_load_test(api, test_config, api_key, endpoint, resource_name,
                        deployment_name, concurrent_levels, requests_per_level,
                        timeout, report_formats, session_id):
    """运行负载测试的异步函数"""

    try:
        # 初始化配置
        config_manager = ConfigManager()
        prompt_manager = PromptManager()

        api_config = config_manager.get_api_config(api)
        if not api_config:
            console.print(f"[red]错误: 找不到API配置 '{api}'[/red]")
            console.print(f"可用配置: {', '.join(config_manager.list_api_configs())}")
            return

        test_cfg = config_manager.get_test_config(test_config)
        if not test_cfg:
            console.print(f"[red]错误: 找不到测试配置 '{test_config}'[/red]")
            console.print(f"可用配置: {', '.join(config_manager.list_test_configs())}")
            return

        # 应用自定义参数
        if concurrent_levels:
            test_cfg.concurrent_levels = [int(x.strip()) for x in concurrent_levels.split(',')]

        if requests_per_level:
            test_cfg.requests_per_level = requests_per_level

        if timeout:
            test_cfg.timeout = timeout

        # 生成会话ID
        if not session_id:
            session_id = f"test_{int(time.time())}_{uuid.uuid4().hex[:8]}"

        console.print(f"[bold green]开始API压力测试[/bold green]")
        console.print(f"会话ID: {session_id}")
        console.print(f"API: {api_config.name}")
        console.print(f"测试配置: {test_cfg.name}")
        console.print()

        # 构建API参数
        api_kwargs = {}
        if resource_name:
            api_kwargs['resource_name'] = resource_name
        if deployment_name:
            api_kwargs['deployment_name'] = deployment_name

        # 初始化组件
        database = TestDatabase()
        monitor = NetworkMonitor()

        start_time = time.time()

        # 启动网络监控
        monitor_task = None
        if api_config.base_url:
            from urllib.parse import urlparse
            host = urlparse(api_config.base_url).hostname
            if host:
                console.print(f"[yellow]启动网络监控: {host}[/yellow]")
                monitor_task = asyncio.create_task(
                    monitor.start_monitoring([host], method="http")
                )

        # 运行负载测试
        async with APIRequestManager(api_config, prompt_manager) as request_manager:
            engine = LoadTestEngine(request_manager)

            results = await engine.run_load_test(
                concurrent_levels=test_cfg.concurrent_levels,
                requests_per_level=test_cfg.requests_per_level,
                api_key=api_key,
                endpoint=endpoint,
                timeout=test_cfg.timeout,
                ramp_up_time=test_cfg.ramp_up_time,
                cool_down_time=test_cfg.cool_down_time,
                **api_kwargs
            )

        end_time = time.time()

        # 停止网络监控
        if monitor_task:
            monitor.stop_monitoring()
            await asyncio.sleep(1)  # 等待监控停止
            monitor_task.cancel()

        # 获取网络统计
        network_stats = monitor.get_all_stats()

        # 保存测试结果
        database.save_test_session(
            session_id=session_id,
            api_name=api,
            test_config=test_config,
            start_time=start_time,
            end_time=end_time,
            load_results=results,
            network_stats=network_stats,
            metadata={
                'endpoint': endpoint,
                'api_kwargs': api_kwargs,
                'prompt_count': prompt_manager.get_prompt_count()
            }
        )

        # 生成报告
        analyzer = DataAnalyzer(database)
        report_manager = ReportManager(analyzer)

        formats = [f.strip() for f in report_formats.split(',')]
        generated_reports = report_manager.generate_comprehensive_report(
            session_id=session_id,
            formats=formats
        )

        # 显示结果摘要
        console.print("\n[bold green]测试完成！[/bold green]")
        console.print(f"总测试时间: {end_time - start_time:.1f}秒")

        # 显示性能摘要表格
        summary_table = Table(title="性能摘要")
        summary_table.add_column("并发数", style="cyan")
        summary_table.add_column("总请求", style="magenta")
        summary_table.add_column("成功率", style="green")
        summary_table.add_column("平均响应时间", style="yellow")
        summary_table.add_column("RPS", style="red")

        for result in results:
            summary_table.add_row(
                str(result.concurrent_level),
                str(result.total_requests),
                f"{(1-result.error_rate)*100:.1f}%",
                f"{result.avg_response_time:.2f}s",
                f"{result.requests_per_second:.1f}"
            )

        console.print(summary_table)

        # 显示生成的报告
        console.print("\n[bold blue]生成的报告:[/bold blue]")
        for format_type, path in generated_reports.items():
            console.print(f"  {format_type.upper()}: {path}")

        # 自动打开HTML报告
        if 'html' in generated_reports:
            console.print(f"\n[green]正在打开HTML报告...[/green]")
            report_manager.generator.open_report(generated_reports['html'])

    except Exception as e:
        console.print(f"[red]测试过程中发生错误: {e}[/red]")
        raise


@cli.command()
@click.option('--api', '-a', required=True, help='API配置名称')
@click.option('--api-key', '-k', required=True, help='API密钥')
@click.option('--max-concurrent', '-c', default=50, help='最大并发数')
@click.option('--duration', '-d', default=300, help='持续时间（秒）')
@click.option('--endpoint', '-e', default='chat', help='API端点')
@click.option('--resource-name', help='Azure资源名称（仅Azure OpenAI需要）')
@click.option('--deployment-name', help='Azure部署名称（仅Azure OpenAI需要）')
def stress(api, api_key, max_concurrent, duration, endpoint, resource_name, deployment_name):
    """运行压力测试"""

    asyncio.run(_run_stress_test(
        api=api,
        api_key=api_key,
        max_concurrent=max_concurrent,
        duration=duration,
        endpoint=endpoint,
        resource_name=resource_name,
        deployment_name=deployment_name
    ))


async def _run_stress_test(api, api_key, max_concurrent, duration, endpoint,
                          resource_name, deployment_name):
    """运行压力测试的异步函数"""

    try:
        # 初始化配置
        config_manager = ConfigManager()
        prompt_manager = PromptManager()

        api_config = config_manager.get_api_config(api)
        if not api_config:
            console.print(f"[red]错误: 找不到API配置 '{api}'[/red]")
            return

        # 构建API参数
        api_kwargs = {}
        if resource_name:
            api_kwargs['resource_name'] = resource_name
        if deployment_name:
            api_kwargs['deployment_name'] = deployment_name

        console.print(f"[bold red]开始压力测试[/bold red]")
        console.print(f"API: {api_config.name}")
        console.print(f"最大并发数: {max_concurrent}")
        console.print(f"持续时间: {duration}秒")
        console.print()

        # 运行压力测试
        async with APIRequestManager(api_config, prompt_manager) as request_manager:
            engine = StressTestEngine(request_manager)

            result = await engine.run_stress_test(
                max_concurrent=max_concurrent,
                duration_seconds=duration,
                api_key=api_key,
                endpoint=endpoint,
                **api_kwargs
            )

        # 显示结果
        console.print(f"\n[bold green]压力测试完成！[/bold green]")
        console.print(f"总请求数: {result.total_requests}")
        console.print(f"成功请求: {result.successful_requests}")
        console.print(f"成功率: {(1-result.error_rate)*100:.1f}%")
        console.print(f"平均响应时间: {result.avg_response_time:.2f}s")
        console.print(f"平均RPS: {result.requests_per_second:.1f}")
        console.print(f"超时请求数: {result.timeout_count}")

    except Exception as e:
        console.print(f"[red]压力测试过程中发生错误: {e}[/red]")
        raise


@cli.command()
def list_configs():
    """列出所有可用的配置"""

    try:
        config_manager = ConfigManager()

        console.print("[bold blue]可用的API配置:[/bold blue]")
        for name in config_manager.list_api_configs():
            api_config = config_manager.get_api_config(name)
            console.print(f"  {name}: {api_config.name}")

        console.print("\n[bold blue]可用的测试配置:[/bold blue]")
        for name in config_manager.list_test_configs():
            test_config = config_manager.get_test_config(name)
            console.print(f"  {name}: {test_config.name}")
            console.print(f"    并发级别: {test_config.concurrent_levels}")
            console.print(f"    每级别请求数: {test_config.requests_per_level}")

    except Exception as e:
        console.print(f"[red]读取配置时发生错误: {e}[/red]")


@cli.command()
@click.option('--limit', '-l', default=10, help='显示的测试会话数量')
def history(limit):
    """显示测试历史"""

    try:
        database = TestDatabase()
        sessions = database.get_test_sessions(limit)

        if not sessions:
            console.print("[yellow]没有找到测试历史[/yellow]")
            return

        table = Table(title=f"最近 {len(sessions)} 次测试")
        table.add_column("会话ID", style="cyan")
        table.add_column("API", style="magenta")
        table.add_column("开始时间", style="green")
        table.add_column("总请求", style="yellow")
        table.add_column("成功率", style="red")
        table.add_column("平均响应时间", style="blue")

        for session in sessions:
            from datetime import datetime
            start_time = datetime.fromtimestamp(session['start_time']).strftime('%Y-%m-%d %H:%M:%S')
            success_rate = f"{session['successful_requests'] / session['total_requests'] * 100:.1f}%" if session['total_requests'] > 0 else "0%"

            table.add_row(
                session['session_id'][:16] + "...",
                session['api_name'],
                start_time,
                str(session['total_requests']),
                success_rate,
                f"{session['avg_response_time']:.2f}s"
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]读取历史记录时发生错误: {e}[/red]")


@cli.command()
@click.argument('session_id')
@click.option('--formats', default='html', help='报告格式，用逗号分隔：html,excel,pdf')
def report(session_id, formats):
    """为指定会话生成报告"""

    try:
        database = TestDatabase()
        analyzer = DataAnalyzer(database)
        report_manager = ReportManager(analyzer)

        format_list = [f.strip() for f in formats.split(',')]
        generated_reports = report_manager.generate_comprehensive_report(
            session_id=session_id,
            formats=format_list
        )

        console.print(f"[bold green]为会话 {session_id} 生成报告:[/bold green]")
        for format_type, path in generated_reports.items():
            console.print(f"  {format_type.upper()}: {path}")

        # 自动打开HTML报告
        if 'html' in generated_reports:
            report_manager.generator.open_report(generated_reports['html'])

    except Exception as e:
        console.print(f"[red]生成报告时发生错误: {e}[/red]")


if __name__ == '__main__':
    cli()