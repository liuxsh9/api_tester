#!/usr/bin/env python3
"""
大模型API压力测试系统示例
"""

import asyncio
import time
from src.api.config import ConfigManager, PromptManager
from src.api.client import APIRequestManager
from src.engine.load_test import LoadTestEngine
from src.monitor.network import NetworkMonitor
from src.stats.analyzer import TestDatabase, DataAnalyzer
from src.report.generator import ReportManager


async def run_example_test():
    """运行示例测试"""

    # 注意：这里使用的是示例API密钥，实际使用时请替换为真实的API密钥
    # 本示例不会实际发送请求，仅用于演示系统架构

    print("🚀 大模型API压力测试系统示例")
    print("=" * 50)

    try:
        # 1. 初始化配置
        print("📋 加载配置...")
        config_manager = ConfigManager()
        prompt_manager = PromptManager()

        # 获取第一个可用的API配置
        api_names = config_manager.list_api_configs()
        if not api_names:
            print("❌ 没有找到API配置")
            return

        api_name = api_names[0]  # 使用第一个API配置
        api_config = config_manager.get_api_config(api_name)

        # 获取默认测试配置
        test_config = config_manager.get_test_config('default')

        print(f"✅ 使用API配置: {api_config.name}")
        print(f"✅ 使用测试配置: {test_config.name}")
        print(f"✅ 加载了 {prompt_manager.get_prompt_count()} 个测试提示词")

        # 2. 模拟测试（不发送真实请求）
        print("\n🧪 开始模拟测试...")
        session_id = f"example_test_{int(time.time())}"

        # 模拟一些测试结果数据
        from src.engine.load_test import LoadTestResult, RequestResult

        mock_results = []
        for concurrent_level in [1, 5, 10]:
            mock_request_results = []
            for i in range(20):  # 每个并发级别20个请求
                mock_request_results.append(RequestResult(
                    timestamp=time.time() - (20 - i),
                    prompt=prompt_manager.get_next_prompt(),
                    response_time=0.5 + (concurrent_level * 0.1) + (i * 0.01),
                    status_code=200,
                    success=True,
                    response_content="Mock response",
                    error_message=None,
                    input_tokens=50,
                    output_tokens=100,
                    total_tokens=150,
                    content_length=200
                ))

            # 分析模拟结果
            engine = LoadTestEngine(None)  # 不需要真实的request_manager用于分析
            load_result = engine.analyze_results(mock_request_results, concurrent_level)
            mock_results.append(load_result)

            print(f"  📊 并发 {concurrent_level}: 平均响应时间 {load_result.avg_response_time:.2f}s, "
                  f"RPS {load_result.requests_per_second:.1f}")

        # 3. 保存测试结果
        print("\n💾 保存测试结果...")
        database = TestDatabase()

        start_time = time.time() - 300  # 5分钟前开始
        end_time = time.time()

        database.save_test_session(
            session_id=session_id,
            api_name=api_name,
            test_config='default',
            start_time=start_time,
            end_time=end_time,
            load_results=mock_results,
            metadata={'example': True}
        )

        print(f"✅ 测试结果已保存，会话ID: {session_id}")

        # 4. 生成分析报告
        print("\n📈 生成分析报告...")
        analyzer = DataAnalyzer(database)
        report_manager = ReportManager(analyzer)

        generated_reports = report_manager.generate_comprehensive_report(
            session_id=session_id,
            formats=['html', 'excel']
        )

        print("✅ 报告生成完成:")
        for format_type, path in generated_reports.items():
            print(f"  📄 {format_type.upper()}: {path}")

        # 5. 显示摘要统计
        print("\n📊 测试摘要:")
        summary_stats = analyzer.generate_summary_stats(session_id)
        perf_metrics = summary_stats.get('performance_metrics', {})

        print(f"  总请求数: {perf_metrics.get('total_requests', 0)}")
        print(f"  成功率: {perf_metrics.get('success_rate', 0) * 100:.1f}%")
        print(f"  平均响应时间: {perf_metrics.get('avg_response_time', 0):.2f}s")
        print(f"  总Token数: {perf_metrics.get('total_tokens', 0)}")

        # 6. 并发性能分析
        print("\n🎯 并发性能分析:")
        concurrency_analysis = analyzer.analyze_concurrency_impact(session_id)
        if 'optimal_concurrency' in concurrency_analysis:
            optimal = concurrency_analysis['optimal_concurrency']
            print(f"  推荐并发数: {optimal['concurrent_level']}")
            print(f"  预期RPS: {optimal['requests_per_second']:.1f}")
            print(f"  预期响应时间: {optimal['avg_response_time']:.2f}s")

        print(f"\n🎉 示例测试完成！报告已生成到 reports/ 目录")
        print(f"💡 提示：使用 'python main.py --help' 查看完整的命令行选项")

    except Exception as e:
        print(f"❌ 示例测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_example_test())