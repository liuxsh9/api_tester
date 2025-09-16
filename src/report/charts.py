import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import seaborn as sns
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from pathlib import Path
import base64
from io import BytesIO

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 设置seaborn样式
sns.set_style("whitegrid")
sns.set_palette("husl")


class ChartGenerator:
    """图表生成器"""

    def __init__(self, output_dir: str = "reports/charts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_response_time_chart(
        self,
        load_results: List[Dict[str, Any]],
        chart_type: str = "line"
    ) -> str:
        """创建响应时间图表"""

        df = pd.DataFrame(load_results)

        if chart_type == "plotly":
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=df['concurrent_level'],
                y=df['avg_response_time'],
                mode='lines+markers',
                name='平均响应时间',
                line=dict(color='blue', width=3),
                marker=dict(size=8)
            ))

            fig.add_trace(go.Scatter(
                x=df['concurrent_level'],
                y=df['p95_response_time'],
                mode='lines+markers',
                name='95%响应时间',
                line=dict(color='red', width=2),
                marker=dict(size=6)
            ))

            fig.add_trace(go.Scatter(
                x=df['concurrent_level'],
                y=df['p99_response_time'],
                mode='lines+markers',
                name='99%响应时间',
                line=dict(color='orange', width=2),
                marker=dict(size=6)
            ))

            fig.update_layout(
                title='响应时间 vs 并发数',
                xaxis_title='并发数',
                yaxis_title='响应时间 (秒)',
                hovermode='x',
                template='plotly_white'
            )

            return fig.to_html(include_plotlyjs='cdn')

        else:  # matplotlib
            fig, ax = plt.subplots(figsize=(12, 8))

            ax.plot(df['concurrent_level'], df['avg_response_time'],
                   marker='o', linewidth=3, label='平均响应时间')
            ax.plot(df['concurrent_level'], df['p95_response_time'],
                   marker='s', linewidth=2, label='95%响应时间')
            ax.plot(df['concurrent_level'], df['p99_response_time'],
                   marker='^', linewidth=2, label='99%响应时间')

            ax.set_xlabel('并发数')
            ax.set_ylabel('响应时间 (秒)')
            ax.set_title('响应时间 vs 并发数')
            ax.legend()
            ax.grid(True, alpha=0.3)

            chart_path = self.output_dir / "response_time_chart.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()

            return str(chart_path)

    def create_throughput_chart(
        self,
        load_results: List[Dict[str, Any]],
        chart_type: str = "line"
    ) -> str:
        """创建吞吐量图表"""

        df = pd.DataFrame(load_results)

        if chart_type == "plotly":
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('请求吞吐量', 'Token吞吐量'),
                shared_xaxes=True
            )

            # 请求吞吐量
            fig.add_trace(
                go.Scatter(
                    x=df['concurrent_level'],
                    y=df['requests_per_second'],
                    mode='lines+markers',
                    name='RPS',
                    line=dict(color='green', width=3)
                ),
                row=1, col=1
            )

            # Token吞吐量
            fig.add_trace(
                go.Scatter(
                    x=df['concurrent_level'],
                    y=df['tokens_per_second'],
                    mode='lines+markers',
                    name='TPS',
                    line=dict(color='purple', width=3)
                ),
                row=2, col=1
            )

            fig.update_layout(
                title='吞吐量 vs 并发数',
                template='plotly_white',
                height=600
            )

            fig.update_xaxes(title_text="并发数", row=2, col=1)
            fig.update_yaxes(title_text="请求/秒", row=1, col=1)
            fig.update_yaxes(title_text="Token/秒", row=2, col=1)

            return fig.to_html(include_plotlyjs='cdn')

        else:  # matplotlib
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

            # 请求吞吐量
            ax1.plot(df['concurrent_level'], df['requests_per_second'],
                    marker='o', linewidth=3, color='green', label='请求/秒')
            ax1.set_ylabel('请求/秒')
            ax1.set_title('请求吞吐量 vs 并发数')
            ax1.grid(True, alpha=0.3)
            ax1.legend()

            # Token吞吐量
            ax2.plot(df['concurrent_level'], df['tokens_per_second'],
                    marker='s', linewidth=3, color='purple', label='Token/秒')
            ax2.set_xlabel('并发数')
            ax2.set_ylabel('Token/秒')
            ax2.set_title('Token吞吐量 vs 并发数')
            ax2.grid(True, alpha=0.3)
            ax2.legend()

            plt.tight_layout()

            chart_path = self.output_dir / "throughput_chart.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()

            return str(chart_path)

    def create_error_rate_chart(
        self,
        load_results: List[Dict[str, Any]],
        chart_type: str = "bar"
    ) -> str:
        """创建错误率图表"""

        df = pd.DataFrame(load_results)
        df['error_rate_percent'] = df['error_rate'] * 100

        if chart_type == "plotly":
            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=df['concurrent_level'],
                y=df['error_rate_percent'],
                name='错误率',
                marker_color='red',
                opacity=0.7
            ))

            fig.update_layout(
                title='错误率 vs 并发数',
                xaxis_title='并发数',
                yaxis_title='错误率 (%)',
                template='plotly_white'
            )

            return fig.to_html(include_plotlyjs='cdn')

        else:  # matplotlib
            fig, ax = plt.subplots(figsize=(12, 6))

            bars = ax.bar(df['concurrent_level'], df['error_rate_percent'],
                         color='red', alpha=0.7)

            ax.set_xlabel('并发数')
            ax.set_ylabel('错误率 (%)')
            ax.set_title('错误率 vs 并发数')
            ax.grid(True, alpha=0.3)

            # 添加数值标签
            for bar, error_rate in zip(bars, df['error_rate_percent']):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{error_rate:.1f}%',
                       ha='center', va='bottom')

            chart_path = self.output_dir / "error_rate_chart.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()

            return str(chart_path)

    def create_response_time_distribution(
        self,
        request_results: List[Dict[str, Any]],
        chart_type: str = "histogram"
    ) -> str:
        """创建响应时间分布图"""

        df = pd.DataFrame(request_results)
        successful_requests = df[df['success'] == True]

        if successful_requests.empty:
            return ""

        if chart_type == "plotly":
            fig = go.Figure()

            fig.add_trace(go.Histogram(
                x=successful_requests['response_time'],
                nbinsx=50,
                name='响应时间分布',
                marker_color='skyblue',
                opacity=0.7
            ))

            fig.update_layout(
                title='响应时间分布',
                xaxis_title='响应时间 (秒)',
                yaxis_title='频次',
                template='plotly_white'
            )

            return fig.to_html(include_plotlyjs='cdn')

        else:  # matplotlib
            fig, ax = plt.subplots(figsize=(12, 6))

            ax.hist(successful_requests['response_time'], bins=50,
                   color='skyblue', alpha=0.7, edgecolor='black')

            ax.set_xlabel('响应时间 (秒)')
            ax.set_ylabel('频次')
            ax.set_title('响应时间分布')
            ax.grid(True, alpha=0.3)

            # 添加统计线
            mean_time = successful_requests['response_time'].mean()
            median_time = successful_requests['response_time'].median()

            ax.axvline(mean_time, color='red', linestyle='--', label=f'平均值: {mean_time:.2f}s')
            ax.axvline(median_time, color='green', linestyle='--', label=f'中位数: {median_time:.2f}s')
            ax.legend()

            chart_path = self.output_dir / "response_time_distribution.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()

            return str(chart_path)

    def create_heatmap(
        self,
        data: pd.DataFrame,
        x_col: str,
        y_col: str,
        value_col: str,
        title: str
    ) -> str:
        """创建热力图"""

        pivot_data = data.pivot(index=y_col, columns=x_col, values=value_col)

        fig, ax = plt.subplots(figsize=(12, 8))

        sns.heatmap(pivot_data, annot=True, fmt='.2f', cmap='YlOrRd',
                   ax=ax, cbar_kws={'label': value_col})

        ax.set_title(title)
        plt.tight_layout()

        chart_path = self.output_dir / "heatmap.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()

        return str(chart_path)

    def create_network_stats_chart(
        self,
        network_stats: Dict[str, Dict[str, Any]],
        chart_type: str = "bar"
    ) -> str:
        """创建网络统计图表"""

        if not network_stats:
            return ""

        hosts = list(network_stats.keys())
        success_rates = [stats['success_rate'] * 100 for stats in network_stats.values()]
        avg_times = [stats['avg_response_time'] for stats in network_stats.values()]

        if chart_type == "plotly":
            fig = make_subplots(
                rows=1, cols=2,
                subplot_titles=('网络成功率', '平均延时'),
                specs=[[{"secondary_y": False}, {"secondary_y": False}]]
            )

            fig.add_trace(
                go.Bar(x=hosts, y=success_rates, name='成功率 (%)', marker_color='green'),
                row=1, col=1
            )

            fig.add_trace(
                go.Bar(x=hosts, y=avg_times, name='延时 (ms)', marker_color='blue'),
                row=1, col=2
            )

            fig.update_layout(
                title='网络质量统计',
                template='plotly_white'
            )

            return fig.to_html(include_plotlyjs='cdn')

        else:  # matplotlib
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

            # 成功率
            bars1 = ax1.bar(hosts, success_rates, color='green', alpha=0.7)
            ax1.set_ylabel('成功率 (%)')
            ax1.set_title('网络成功率')
            ax1.set_ylim(0, 100)

            for bar, rate in zip(bars1, success_rates):
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height,
                        f'{rate:.1f}%', ha='center', va='bottom')

            # 平均延时
            bars2 = ax2.bar(hosts, avg_times, color='blue', alpha=0.7)
            ax2.set_ylabel('延时 (ms)')
            ax2.set_title('平均网络延时')

            for bar, time_val in zip(bars2, avg_times):
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height,
                        f'{time_val:.1f}ms', ha='center', va='bottom')

            plt.tight_layout()

            chart_path = self.output_dir / "network_stats_chart.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()

            return str(chart_path)

    def image_to_base64(self, image_path: str) -> str:
        """将图片转换为base64编码"""
        with open(image_path, 'rb') as img_file:
            img_data = img_file.read()
            return base64.b64encode(img_data).decode('utf-8')