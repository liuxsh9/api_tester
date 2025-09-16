from jinja2 import Template
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import time
from datetime import datetime
import webbrowser
import pandas as pd
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

from .charts import ChartGenerator
from ..stats.analyzer import DataAnalyzer


class ReportGenerator:
    """测试报告生成器"""

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.chart_generator = ChartGenerator(self.output_dir / "charts")

    def generate_html_report(
        self,
        session_id: str,
        summary_stats: Dict[str, Any],
        load_results: List[Dict[str, Any]],
        network_stats: Optional[Dict[str, Any]] = None,
        concurrency_analysis: Optional[Dict[str, Any]] = None
    ) -> str:
        """生成HTML报告"""

        # 生成图表
        charts = {}
        if load_results:
            charts['response_time'] = self.chart_generator.create_response_time_chart(
                load_results, chart_type="plotly"
            )
            charts['throughput'] = self.chart_generator.create_throughput_chart(
                load_results, chart_type="plotly"
            )
            charts['error_rate'] = self.chart_generator.create_error_rate_chart(
                load_results, chart_type="plotly"
            )

        if network_stats:
            charts['network'] = self.chart_generator.create_network_stats_chart(
                network_stats, chart_type="plotly"
            )

        # HTML模板
        html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>大模型API压力测试报告</title>
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            border-bottom: 3px solid #007bff;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #007bff;
            margin-bottom: 10px;
        }
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .metric-card h3 {
            margin: 0 0 10px 0;
            font-size: 1.2em;
        }
        .metric-card .value {
            font-size: 2em;
            font-weight: bold;
        }
        .section {
            margin-bottom: 40px;
        }
        .section h2 {
            color: #333;
            border-left: 4px solid #007bff;
            padding-left: 15px;
            margin-bottom: 20px;
        }
        .chart-container {
            margin: 20px 0;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
        }
        .table-container {
            overflow-x: auto;
            margin: 20px 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #f8f9fa;
            font-weight: bold;
            color: #333;
        }
        tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        .status-success {
            color: #28a745;
            font-weight: bold;
        }
        .status-warning {
            color: #ffc107;
            font-weight: bold;
        }
        .status-danger {
            color: #dc3545;
            font-weight: bold;
        }
        .recommendation {
            background: #e7f3ff;
            border-left: 4px solid #007bff;
            padding: 15px;
            margin: 20px 0;
            border-radius: 0 8px 8px 0;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>大模型API压力测试报告</h1>
            <p>测试会话ID: {{ session_id }}</p>
            <p>生成时间: {{ report_time }}</p>
            <p>API名称: {{ api_name }}</p>
        </div>

        <div class="section">
            <h2>📊 测试概览</h2>
            <div class="summary">
                <div class="metric-card">
                    <h3>总请求数</h3>
                    <div class="value">{{ total_requests }}</div>
                </div>
                <div class="metric-card">
                    <h3>成功率</h3>
                    <div class="value">{{ success_rate }}%</div>
                </div>
                <div class="metric-card">
                    <h3>平均响应时间</h3>
                    <div class="value">{{ avg_response_time }}s</div>
                </div>
                <div class="metric-card">
                    <h3>总Token数</h3>
                    <div class="value">{{ total_tokens }}</div>
                </div>
                <div class="metric-card">
                    <h3>超时请求数</h3>
                    <div class="value">{{ total_timeouts }}</div>
                </div>
            </div>
        </div>

        {% if charts.response_time %}
        <div class="section">
            <h2>⏱️ 响应时间分析</h2>
            <div class="chart-container">
                {{ charts.response_time | safe }}
            </div>
        </div>
        {% endif %}

        {% if charts.throughput %}
        <div class="section">
            <h2>🚀 吞吐量分析</h2>
            <div class="chart-container">
                {{ charts.throughput | safe }}
            </div>
        </div>
        {% endif %}

        {% if charts.error_rate %}
        <div class="section">
            <h2>❌ 错误率分析</h2>
            <div class="chart-container">
                {{ charts.error_rate | safe }}
            </div>
        </div>
        {% endif %}

        <div class="section">
            <h2>📈 详细测试结果</h2>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>并发数</th>
                            <th>总请求</th>
                            <th>成功率</th>
                            <th>平均响应时间</th>
                            <th>P95响应时间</th>
                            <th>RPS</th>
                            <th>Token/s</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for result in load_results %}
                        <tr>
                            <td>{{ result.concurrent_level }}</td>
                            <td>{{ result.total_requests }}</td>
                            <td class="{% if result.error_rate < 0.01 %}status-success{% elif result.error_rate < 0.05 %}status-warning{% else %}status-danger{% endif %}">
                                {{ "%.1f"|format((1-result.error_rate)*100) }}%
                            </td>
                            <td>{{ "%.2f"|format(result.avg_response_time) }}s</td>
                            <td>{{ "%.2f"|format(result.p95_response_time) }}s</td>
                            <td>{{ "%.1f"|format(result.requests_per_second) }}</td>
                            <td>{{ "%.1f"|format(result.tokens_per_second) }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        {% if concurrency_analysis %}
        <div class="section">
            <h2>🎯 并发性能建议</h2>
            <div class="recommendation">
                <h3>最优并发数配置</h3>
                <p><strong>推荐并发数:</strong> {{ concurrency_analysis.optimal_concurrency.concurrent_level }}</p>
                <p><strong>预期RPS:</strong> {{ "%.1f"|format(concurrency_analysis.optimal_concurrency.requests_per_second) }}</p>
                <p><strong>预期响应时间:</strong> {{ "%.2f"|format(concurrency_analysis.optimal_concurrency.avg_response_time) }}s</p>

                {% if concurrency_analysis.throughput_decline_point %}
                <p><strong>性能下降点:</strong> 并发数超过 {{ concurrency_analysis.throughput_decline_point.concurrent_level }} 时性能开始下降</p>
                {% endif %}
            </div>
        </div>
        {% endif %}

        {% if charts.network %}
        <div class="section">
            <h2>🌐 网络质量监控</h2>
            <div class="chart-container">
                {{ charts.network | safe }}
            </div>
        </div>
        {% endif %}

        {% if error_distribution %}
        <div class="section">
            <h2>🐛 错误分布分析</h2>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>错误类型</th>
                            <th>出现次数</th>
                            <th>占比</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for error in error_distribution %}
                        <tr>
                            <td>{{ error.error_message }}</td>
                            <td>{{ error.count }}</td>
                            <td>{{ "%.2f"|format(error.percentage) }}%</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        {% endif %}

        <div class="footer">
            <p>报告由 API 压力测试系统 生成</p>
            <p>测试时间: {{ test_duration }}s | 生成时间: {{ report_time }}</p>
        </div>
    </div>
</body>
</html>
        """

        # 准备模板数据
        template_data = {
            'session_id': session_id,
            'report_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'api_name': summary_stats.get('session_info', {}).get('api_name', 'Unknown'),
            'total_requests': summary_stats.get('performance_metrics', {}).get('total_requests', 0),
            'success_rate': f"{summary_stats.get('performance_metrics', {}).get('success_rate', 0) * 100:.1f}",
            'avg_response_time': f"{summary_stats.get('performance_metrics', {}).get('avg_response_time', 0):.2f}",
            'total_tokens': summary_stats.get('performance_metrics', {}).get('total_tokens', 0),
            'total_timeouts': summary_stats.get('performance_metrics', {}).get('total_timeouts', 0),
            'load_results': load_results,
            'charts': charts,
            'concurrency_analysis': concurrency_analysis,
            'network_stats': network_stats,
            'test_duration': summary_stats.get('session_info', {}).get('end_time', 0) -
                           summary_stats.get('session_info', {}).get('start_time', 0)
        }

        # 添加错误分布数据
        error_distribution = summary_stats.get('error_distribution', [])
        if error_distribution:
            total_errors = sum(err['count'] for err in error_distribution)
            for error in error_distribution:
                error['percentage'] = (error['count'] / total_errors) * 100
        template_data['error_distribution'] = error_distribution

        # 渲染模板
        template = Template(html_template)
        html_content = template.render(**template_data)

        # 保存HTML文件
        report_path = self.output_dir / f"test_report_{session_id}.html"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return str(report_path)

    def generate_excel_report(
        self,
        session_id: str,
        summary_stats: Dict[str, Any],
        load_results: List[Dict[str, Any]],
        detailed_results: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """生成Excel报告"""

        report_path = self.output_dir / f"test_report_{session_id}.xlsx"

        with pd.ExcelWriter(report_path, engine='openpyxl') as writer:
            # 摘要页
            summary_data = {
                '指标': ['总请求数', '成功请求数', '失败请求数', '成功率(%)',
                        '平均响应时间(s)', '最小响应时间(s)', '最大响应时间(s)',
                        '总Token数', '超时请求数'],
                '值': [
                    summary_stats.get('performance_metrics', {}).get('total_requests', 0),
                    summary_stats.get('performance_metrics', {}).get('successful_requests', 0),
                    summary_stats.get('performance_metrics', {}).get('failed_requests', 0),
                    f"{summary_stats.get('performance_metrics', {}).get('success_rate', 0) * 100:.2f}",
                    f"{summary_stats.get('performance_metrics', {}).get('avg_response_time', 0):.3f}",
                    f"{summary_stats.get('performance_metrics', {}).get('min_response_time', 0):.3f}",
                    f"{summary_stats.get('performance_metrics', {}).get('max_response_time', 0):.3f}",
                    summary_stats.get('performance_metrics', {}).get('total_tokens', 0),
                    summary_stats.get('performance_metrics', {}).get('total_timeouts', 0)
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='测试摘要', index=False)

            # 负载测试结果页
            if load_results:
                load_df = pd.DataFrame(load_results)
                load_df.to_excel(writer, sheet_name='负载测试结果', index=False)

            # 详细结果页（如果提供）
            if detailed_results:
                detailed_df = pd.DataFrame(detailed_results)
                detailed_df.to_excel(writer, sheet_name='详细结果', index=False)

            # 错误分布页
            error_distribution = summary_stats.get('error_distribution', [])
            if error_distribution:
                error_df = pd.DataFrame(error_distribution)
                error_df.to_excel(writer, sheet_name='错误分布', index=False)

        return str(report_path)

    def generate_pdf_report(
        self,
        session_id: str,
        summary_stats: Dict[str, Any],
        load_results: List[Dict[str, Any]]
    ) -> str:
        """生成PDF报告"""

        report_path = self.output_dir / f"test_report_{session_id}.pdf"
        doc = SimpleDocTemplate(str(report_path), pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # 标题
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            spaceAfter=30,
            alignment=1  # 居中
        )
        story.append(Paragraph("大模型API压力测试报告", title_style))
        story.append(Spacer(1, 12))

        # 基本信息
        info_data = [
            ['测试会话ID', session_id],
            ['API名称', summary_stats.get('session_info', {}).get('api_name', 'Unknown')],
            ['生成时间', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['测试开始时间', datetime.fromtimestamp(
                summary_stats.get('session_info', {}).get('start_time', 0)
            ).strftime('%Y-%m-%d %H:%M:%S')],
        ]

        info_table = Table(info_data)
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(info_table)
        story.append(Spacer(1, 20))

        # 性能摘要
        story.append(Paragraph("性能摘要", styles['Heading2']))
        perf_metrics = summary_stats.get('performance_metrics', {})

        perf_data = [
            ['指标', '值'],
            ['总请求数', str(perf_metrics.get('total_requests', 0))],
            ['成功率', f"{perf_metrics.get('success_rate', 0) * 100:.2f}%"],
            ['平均响应时间', f"{perf_metrics.get('avg_response_time', 0):.3f}s"],
            ['总Token数', str(perf_metrics.get('total_tokens', 0))],
            ['超时请求数', str(perf_metrics.get('total_timeouts', 0))]
        ]

        perf_table = Table(perf_data)
        perf_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(perf_table)
        story.append(Spacer(1, 20))

        # 负载测试详细结果
        if load_results:
            story.append(Paragraph("负载测试详细结果", styles['Heading2']))

            load_data = [['并发数', '总请求', '成功率', '平均响应时间', 'RPS']]
            for result in load_results:
                load_data.append([
                    str(result['concurrent_level']),
                    str(result['total_requests']),
                    f"{(1-result['error_rate'])*100:.1f}%",
                    f"{result['avg_response_time']:.2f}s",
                    f"{result['requests_per_second']:.1f}"
                ])

            load_table = Table(load_data)
            load_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            story.append(load_table)

        # 构建PDF
        doc.build(story)
        return str(report_path)

    def open_report(self, report_path: str):
        """在浏览器中打开报告"""
        if report_path.endswith('.html'):
            webbrowser.open(f'file://{Path(report_path).absolute()}')
        else:
            print(f"报告已生成: {report_path}")


class ReportManager:
    """报告管理器"""

    def __init__(self, analyzer: DataAnalyzer, output_dir: str = "reports"):
        self.analyzer = analyzer
        self.generator = ReportGenerator(output_dir)

    def generate_comprehensive_report(
        self,
        session_id: str,
        formats: List[str] = ["html", "excel"]
    ) -> Dict[str, str]:
        """生成综合报告"""

        # 获取测试数据
        summary_stats = self.analyzer.generate_summary_stats(session_id)
        load_results = self.analyzer.database.get_load_test_results(session_id)
        concurrency_analysis = self.analyzer.analyze_concurrency_impact(session_id)

        # 转换为字典格式
        load_results_dict = [result.to_dict() for result in load_results]

        generated_reports = {}

        if "html" in formats:
            html_path = self.generator.generate_html_report(
                session_id=session_id,
                summary_stats=summary_stats,
                load_results=load_results_dict,
                concurrency_analysis=concurrency_analysis
            )
            generated_reports["html"] = html_path

        if "excel" in formats:
            excel_path = self.generator.generate_excel_report(
                session_id=session_id,
                summary_stats=summary_stats,
                load_results=load_results_dict
            )
            generated_reports["excel"] = excel_path

        if "pdf" in formats:
            pdf_path = self.generator.generate_pdf_report(
                session_id=session_id,
                summary_stats=summary_stats,
                load_results=load_results_dict
            )
            generated_reports["pdf"] = pdf_path

        return generated_reports