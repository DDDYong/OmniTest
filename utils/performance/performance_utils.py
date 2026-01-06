"""
-------------------------------------------------
File:           performance_utils.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:
性能测试工具类,提供性能测试数据处理、报告生成、结果分析等辅助功能
-------------------------------------------------
"""
import json
import os
import random
import statistics
import time
from typing import Optional, Dict, List, Any

from utils.common_util import CommonUtils
from utils.file_util import DataHandler
# 暂时注释掉数据分析相关的导入,避免缺少依赖
# import pandas as pd
# import matplotlib.pyplot as plt
# import seaborn as sns
# import numpy as np
from utils.logger_util import logger


class PerformanceUtils:
    """
    性能测试工具类
    提供性能测试数据处理、报告生成、结果分析等功能
    """

    def __init__(self):
        """
        初始化性能测试工具
        """
        self.utils = CommonUtils()
        self.data_handler = DataHandler()
        self._setup_plots()

    def _setup_plots(self):
        """
        设置图表样式
        """
        # 暂时注释掉matplotlib相关代码,避免缺少依赖
        # 设置matplotlib中文字体
        # plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
        # plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

        # # 设置seaborn样式
        # sns.set(style="whitegrid")
        sns.set_palette("husl")

    def generate_test_data(self, data_type: str = "json", count: int = 100,
                           output_file: Optional[str] = None, **kwargs) -> str:
        """
        生成性能测试数据
        
        Args:
        data_type: 数据类型, 支持 "json", "yaml", "csv"
        count: 数据记录数量
        output_file: 输出文件路径, 如不指定则自动生成
        **kwargs: 其他参数, 如数据模板
            
        Returns:
        str: 生成的数据文件路径
        """
        logger.info(f"开始生成性能测试数据,类型: {data_type},记录数: {count}")

        # 生成数据记录
        data_records = []

        # 根据数据模板生成记录
        template = kwargs.get("template", {})

        for i in range(count):
            # 生成单条记录
            record = self._generate_record(template, i)
            data_records.append(record)

        # 确定输出文件路径
        if not output_file:
            timestamp = self.utils.get_timestamp()
            # 延迟导入获取配置值
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
            try:
                from config.config_manager import config
                data_dir = config.DATA_DIR
            except ImportError:
                logger.warning("无法导入config模块，使用默认数据目录")
            output_file = os.path.join(
                data_dir,
                f"performance_test_data_{timestamp}.{data_type}"
            )

        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file), exist_ok = True)

        # 保存数据
        if data_type == "json":
            with open(output_file, "w", encoding = "utf-8") as f:
                json.dump(data_records, f, ensure_ascii = False, indent = 2)
        elif data_type in ["yaml", "yml"]:
            self.data_handler.save_data(output_file, data_records)
        elif data_type == "csv":
            # 延迟导入pandas
            try:
                import pandas as pd
                df = pd.DataFrame(data_records)
                df.to_csv(output_file, index = False, encoding = "utf-8")
            except ImportError:
                logger.error("缺少pandas库，无法生成CSV文件")
                raise ImportError("缺少pandas库，请安装后重试")
        else:
            raise ValueError(f"不支持的数据类型: {data_type}")

        logger.info(f"性能测试数据生成完成,保存到: {output_file}")
        return output_file

    def _generate_record(self, template: Dict[str, Any], index: int) -> Dict[str, Any]:
        """
        生成单条测试记录
        
        Args:
        template: 数据模板
        index: 记录索引
            
        Returns:
        Dict[str, Any]: 生成的记录
        """
        record = {}

        for key, value in template.items():
            # 根据值的类型生成相应的数据
            if isinstance(value, str):
                # 处理特殊标记
                if value == "{{random_string}}":
                    record[key] = self.utils.generate_random_string()
                elif value == "{{timestamp}}":
                    record[key] = self.utils.get_timestamp()
                elif value == "{{uuid}}":
                    record[key] = self.utils.generate_uuid()
                elif value == "{{index}}":
                    record[key] = index
                elif value == "{{random_int}}":
                    record[key] = random.randint(1, 1000)
                else:
                    record[key] = value
            elif isinstance(value, int):
                record[key] = value + index  # 递增数字
            elif isinstance(value, float):
                record[key] = round(value + random.random() * 10, 2)
            elif isinstance(value, bool):
                record[key] = random.choice([True, False])
            elif isinstance(value, list):
                if value:
                    record[key] = random.choice(value)
                else:
                    record[key] = []
            elif isinstance(value, dict):
                # 递归处理嵌套字典
                record[key] = self._generate_record(value, index)
            else:
                record[key] = value

        return record

    def parse_locust_results(self, results_dir: str,
                             file_pattern: str = "*.csv") -> list:
        """
        解析Locust测试结果
        
        Args:
        results_dir: 结果文件目录
        file_pattern: 文件匹配模式
            
        Returns:
        list: 解析后的结果数据列表
        """
        # 延迟导入pandas
        try:
            import pandas as pd
        except ImportError:
            logger.error("缺少pandas库，无法解析Locust测试结果")
            raise ImportError("缺少pandas库，请安装后重试")
        import glob

        logger.info(f"开始解析Locust测试结果,目录: {results_dir}")

        # 查找结果文件
        result_files = glob.glob(os.path.join(results_dir, file_pattern))

        if not result_files:
            logger.warning(f"在目录 {results_dir} 中未找到匹配的结果文件: {file_pattern}")
            return []

        # 解析每个文件
        all_data = []

        for file_path in result_files:
            try:
                # 解析CSV文件
                df = pd.read_csv(file_path)

                # 将DataFrame转换为列表字典格式
                file_data = df.to_dict('records')
                all_data.extend(file_data)
            except Exception as e:
                logger.error(f"解析文件 {file_path} 时出错: {str(e)}")
                continue

        logger.info(f"Locust测试结果解析完成,共 {len(all_data)} 条记录")
        return all_data

    def analyze_performance_results(self, results_file: str,
                                    output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        分析性能测试结果
        
        Args:
        results_file: 结果文件路径 (JSON格式)
        output_dir: 输出分析结果的目录, 如不指定则使用默认报告目录
            
        Returns:
        Dict[str, Any]: 分析结果
        """
        logger.info(f"开始分析性能测试结果: {results_file}")

        # 读取结果文件
        try:
            with open(results_file, "r", encoding = "utf-8") as f:
                results = json.load(f)
        except Exception as e:
            logger.error(f"读取结果文件失败: {str(e)}")
            raise

        # 确定输出目录
        if not output_dir:
            output_dir = os.path.join(config.REPORT_DIR, "performance_analysis")
        os.makedirs(output_dir, exist_ok = True)

        # 分析结果
        analysis = {
            "summary": self._calculate_summary_stats(results),
            "request_details": self._analyze_request_details(results),
            "response_time_distribution": self._analyze_response_time_distribution(results),
            "error_analysis": self._analyze_errors(results)
        }

        # 生成可视化图表
        self._generate_charts(results, output_dir)

        # 保存分析报告
        report_file = os.path.join(output_dir, f"analysis_report_{self.utils.get_timestamp()}.json")
        with open(report_file, "w", encoding = "utf-8") as f:
            json.dump(analysis, f, ensure_ascii = False, indent = 2)

        logger.info(f"性能测试结果分析完成,报告保存到: {report_file}")
        return analysis

    def _calculate_summary_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算汇总统计信息
        
        Args:
        results: 测试结果列表
            
        Returns:
        Dict[str, Any]: 汇总统计信息
        """
        if not results:
            return {}

        # 提取响应时间
        response_times = [r.get("response_time", 0) for r in results if r.get("success")]

        # 计算成功和失败的请求数
        successful = sum(1 for r in results if r.get("success"))
        failed = len(results) - successful

        summary = {
            "total_requests": len(results),
            "successful_requests": successful,
            "failed_requests": failed,
            "success_rate": round(successful / len(results) * 100, 2) if results else 0
        }

        # 计算响应时间统计
        if response_times:
            summary["avg_response_time"] = round(statistics.mean(response_times), 2)
            summary["median_response_time"] = round(statistics.median(response_times), 2)
            summary["min_response_time"] = min(response_times)
            summary["max_response_time"] = max(response_times)

            if len(response_times) > 1:
                summary["std_response_time"] = round(statistics.stdev(response_times), 2)

            # 计算百分位数
            percentiles = [50, 90, 95, 99]
            for p in percentiles:
                summary[f"p{p}_response_time"] = round(np.percentile(response_times, p), 2)

        return summary

    def _analyze_request_details(self, results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        分析请求详情
        
        Args:
        results: 测试结果列表
            
        Returns:
        Dict[str, List[Dict[str, Any]]]: 请求详情分析
        """
        # 按请求名称分组
        request_groups = {}

        for result in results:
            name = result.get("name", "unknown")

            if name not in request_groups:
                request_groups[name] = []

            request_groups[name].append(result)

        # 分析每个请求组
        details = {}

        for name, group_results in request_groups.items():
            # 提取响应时间
            response_times = [r.get("response_time", 0) for r in group_results if r.get("success")]

            # 计算成功和失败的请求数
            successful = sum(1 for r in group_results if r.get("success"))
            failed = len(group_results) - successful

            group_analysis = {
                "total_requests": len(group_results),
                "successful_requests": successful,
                "failed_requests": failed,
                "success_rate": round(successful / len(group_results) * 100, 2) if group_results else 0
            }

            # 计算响应时间统计
            if response_times:
                group_analysis["avg_response_time"] = round(statistics.mean(response_times), 2)
                group_analysis["median_response_time"] = round(statistics.median(response_times), 2)
                group_analysis["min_response_time"] = min(response_times)
                group_analysis["max_response_time"] = max(response_times)

                if len(response_times) > 1:
                    group_analysis["std_response_time"] = round(statistics.stdev(response_times), 2)

            details[name] = group_analysis

        return details

    def _analyze_response_time_distribution(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        分析响应时间分布
        
        Args:
        results: 测试结果列表
            
        Returns:
        List[Dict[str, Any]]: 响应时间分布
        """
        # 提取成功请求的响应时间
        response_times = [r.get("response_time", 0) for r in results if r.get("success")]

        if not response_times:
            return []

        # 定义响应时间区间（毫秒）
        bins = [0, 50, 100, 200, 500, 1000, 2000, 5000, float("inf")]
        labels = ["<50ms", "50-100ms", "100-200ms", "200-500ms", "500ms-1s", "1-2s", "2-5s", ">5s"]

        # 统计每个区间的请求数
        distribution = []
        total = len(response_times)

        for i in range(len(bins) - 1):
            count = sum(1 for rt in response_times if bins[i] <= rt < bins[i + 1])

            if i == len(bins) - 2:  # 最后一个区间
                count = sum(1 for rt in response_times if rt >= bins[i])

            distribution.append({
                "range": labels[i],
                "count": count,
                "percentage": round(count / total * 100, 2) if total else 0
            })

        return distribution

    def _analyze_errors(self, results: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        分析错误类型
        
        Args:
        results: 测试结果列表
            
        Returns:
        Dict[str, int]: 错误类型统计
        """
        error_counts = {}

        for result in results:
            if not result.get("success") and "error" in result:
                error = result["error"]
                error_counts[error] = error_counts.get(error, 0) + 1

        return error_counts

    def _generate_charts(self, results: List[Dict[str, Any]], output_dir: str):
        """
        生成可视化图表
        
        Args:
        results: 测试结果列表
        output_dir: 输出目录
        """
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok = True)

        # 提取成功请求的响应时间
        response_times = [r.get("response_time", 0) for r in results if r.get("success")]

        if not response_times:
            logger.warning("没有成功的请求数据,无法生成图表")
            return

        # 1. 响应时间分布图
        plt.figure(figsize = (10, 6))
        sns.histplot(response_times, bins = 30, kde = True)
        plt.title("响应时间分布图")
        plt.xlabel("响应时间 (ms)")
        plt.ylabel("请求数")
        plt.savefig(os.path.join(output_dir, "response_time_distribution.png"), dpi = 300)
        plt.close()

        # 2. 响应时间箱线图
        plt.figure(figsize = (10, 6))
        sns.boxplot(y = response_times)
        plt.title("响应时间箱线图")
        plt.ylabel("响应时间 (ms)")
        plt.savefig(os.path.join(output_dir, "response_time_boxplot.png"), dpi = 300)
        plt.close()

        # 3. 按请求名称分组的平均响应时间
        # 按请求名称分组
        request_groups = {}

        for result in results:
            if result.get("success"):
                name = result.get("name", "unknown")

                if name not in request_groups:
                    request_groups[name] = []

                request_groups[name].append(result.get("response_time", 0))

        if request_groups:
            # 计算每组的平均响应时间
            avg_response_times = []
            request_names = []

            for name, times in request_groups.items():
                request_names.append(name)
                avg_response_times.append(statistics.mean(times))

            # 绘制条形图
            plt.figure(figsize = (12, 6))
            bars = plt.bar(range(len(avg_response_times)), avg_response_times)

            # 设置颜色（根据响应时间）
            max_time = max(avg_response_times)
            for i, bar in enumerate(bars):
                color_intensity = min(avg_response_times[i] / max_time * 0.8 + 0.2, 1.0)
                bar.set_color((color_intensity, 0.4, 0.2))

            plt.title("各请求平均响应时间")
            plt.xlabel("请求名称")
            plt.ylabel("平均响应时间 (ms)")
            plt.xticks(range(len(request_names)), request_names, rotation = 45, ha = "right")
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, "avg_response_time_by_request.png"), dpi = 300)
            plt.close()

        logger.info(f"性能测试图表生成完成,保存到: {output_dir}")

    def generate_performance_report(self, analysis_results: Dict[str, Any],
                                    output_file: Optional[str] = None,
                                    template: Optional[str] = None) -> str:
        """
        生成性能测试报告
        
        Args:
        analysis_results: 分析结果
        output_file: 输出文件路径, 如不指定则自动生成
        template: 报告模板路径
            
        Returns:
        str: 生成的报告文件路径
        """
        logger.info("开始生成性能测试报告")

        # 确保输出目录存在
        if not output_file:
            timestamp = self.utils.get_timestamp()
            output_file = os.path.join(
                config.REPORT_DIR,
                f"performance_report_{timestamp}.html"
            )

        os.makedirs(os.path.dirname(output_file), exist_ok = True)

        # 生成HTML报告
        html_content = self._generate_html_report(analysis_results)

        # 保存报告
        with open(output_file, "w", encoding = "utf-8") as f:
            f.write(html_content)

        logger.info(f"性能测试报告生成完成,保存到: {output_file}")
        return output_file

    def _generate_html_report(self, analysis_results: Dict[str, Any]) -> str:
        """
        生成HTML报告内容
        
        Args:
        analysis_results: 分析结果
            
        Returns:
        str: HTML报告内容
        """
        # 生成报告头部
        html_header = """
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>性能测试报告</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
        body {
        font-family: 'Helvetica Neue', Arial, sans-serif;
        line-height: 1.6;
        color: #333;
        background-color: #f5f5f5;
        }
        .container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
        }
        .header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 30px;
        border-radius: 10px;
        margin-bottom: 30px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .card {
        background-color: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        padding: 20px;
        margin-bottom: 20px;
        }
        .card h2 {
        color: #444;
        margin-bottom: 20px;
        font-size: 1.5rem;
        border-bottom: 2px solid #eee;
        padding-bottom: 10px;
        }
        .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 20px;
        margin-bottom: 20px;
        }
        .stat-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 20px;
        border-radius: 8px;
        text-align: center;
        }
        .stat-value {
        font-size: 2rem;
        font-weight: bold;
        color: #444;
        }
        .stat-label {
        font-size: 0.9rem;
        color: #666;
        margin-top: 5px;
        }
        .success-rate {
        font-size: 1.5rem;
        font-weight: bold;
        }
        .success-rate.good {
        color: #28a745;
        }
        .success-rate.warning {
        color: #ffc107;
        }
        .success-rate.danger {
        color: #dc3545;
        }
        .table {
        width: 100%;
        border-collapse: collapse;
        }
        .table th, .table td {
        padding: 12px;
        text-align: left;
        border-bottom: 1px solid #ddd;
        }
        .table th {
        background-color: #f8f9fa;
        font-weight: 600;
        color: #444;
        }
        .chart-container {
        position: relative;
        height: 400px;
        margin-bottom: 30px;
        }
        .footer {
        text-align: center;
        margin-top: 40px;
        padding: 20px;
        color: #666;
        font-size: 0.9rem;
        }
        </style>
        </head>
        <body>
        <div class="container">
        <div class="header">
        <h1>性能测试报告</h1>
        <p>生成时间: {timestamp}</p>
        </div>
        """
        # 生成时间戳
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        html_header = html_header.format(timestamp = timestamp)

        # 生成汇总统计
        summary = analysis_results.get("summary", {})

        html_summary = """
        <div class="card">
        <h2>测试汇总</h2>
        <div class="stats-grid">
        """
        # 添加统计卡片
        stats = [
            ("总请求数", summary.get("total_requests", 0), "total"),
            ("成功请求数", summary.get("successful_requests", 0), "success"),
            ("失败请求数", summary.get("failed_requests", 0), "failed"),
            ("平均响应时间", f"{summary.get('avg_response_time', 0)}ms", "avg"),
            ("90% 响应时间", f"{summary.get('p90_response_time', 0)}ms", "p90"),
            ("99% 响应时间", f"{summary.get('p99_response_time', 0)}ms", "p99")
        ]

        for label, value, stat_type in stats:
            html_summary += f"""
            <div class="stat-card">
            <div class="stat-value">{value}</div>
            <div class="stat-label">{label}</div>
            </div>
              """
            html_summary += """
            </div>
            <div class="text-center">
            <span class="success-rate {success_rate_class}">
            成功率: {success_rate}%
            </span>
            </div>
            </div>
            """
        # 根据成功率设置颜色类
        success_rate = summary.get("success_rate", 0)
        if success_rate >= 95:
            success_rate_class = "good"
        elif success_rate >= 90:
            success_rate_class = "warning"
        else:
            success_rate_class = "danger"

        html_summary = html_summary.format(
            success_rate_class = success_rate_class,
            success_rate = success_rate
        )

        # 生成响应时间分布
        distribution = analysis_results.get("response_time_distribution", [])

        html_distribution = """
        <div class="card">
        <h2>响应时间分布</h2>
        <div class="chart-container">
        <canvas id="distributionChart"></canvas>
        </div>
        <table class="table">
        <thead>
        <tr>
        <th>响应时间区间</th>
        <th>请求数</th>
        <th>百分比</th>
        </tr>
        </thead>
        <tbody>
        """
        for item in distribution:
            html_distribution += f"""
            <tr>
            <td>{item['range']}</td>
            <td>{item['count']}</td>
            <td>{item['percentage']}%</td>
            </tr>
            """
        html_distribution += """
        </tbody>
        </table>
        </div>
        """
        # 生成请求详情
        request_details = analysis_results.get("request_details", {})

        html_details = """
        <div class="card">
        <h2>请求详情</h2>
        <table class="table">
        <thead>
        <tr>
        <th>请求名称</th>
        <th>总请求数</th>
        <th>成功数</th>
        <th>失败数</th>
        <th>成功率</th>
        <th>平均响应时间</th>
        </tr>
        </thead>
        <tbody>
        """
        for name, details in request_details.items():
            html_details += f"""
            <tr>
            <td>{name}</td>
            <td>{details.get('total_requests', 0)}</td>
            <td>{details.get('successful_requests', 0)}</td>
            <td>{details.get('failed_requests', 0)}</td>
            <td>{details.get('success_rate', 0)}%</td>
            <td>{details.get('avg_response_time', 0)}ms</td>
            </tr>
            """
        html_details += """
        </tbody>
        </table>
        </div>
        """
        # 生成错误分析
        errors = analysis_results.get("error_analysis", {})

        html_errors = """
        <div class="card">
        <h2>错误分析</h2>
        <div class="chart-container">
        <canvas id="errorChart"></canvas>
        </div>
        <table class="table">
        <thead>
        <tr>
        <th>错误类型</th>
        <th>出现次数</th>
        </tr>
        </thead>
        <tbody>
        """
        for error, count in errors.items():
            # 限制错误描述长度
            display_error = error[:100] + "..." if len(error) > 100 else error
            html_errors += f"""
            <tr>
            <td title="{error}">{display_error}</td>
            <td>{count}</td>
            </tr>
            """
        html_errors += """
        </tbody>
        </table>
        </div>
        """
        # 生成JavaScript代码
        html_js = """
        <script>
        // 响应时间分布图表
        const distributionCtx = document.getElementById('distributionChart').getContext('2d');
        const distributionData = {
        labels: [%s],
        datasets: [{
        label: '请求数',
        data: [%s],
        backgroundColor: [
        'rgba(255, 99, 132, 0.6)',
        'rgba(54, 162, 235, 0.6)',
        'rgba(255, 206, 86, 0.6)',
        'rgba(75, 192, 192, 0.6)',
        'rgba(153, 102, 255, 0.6)',
        'rgba(255, 159, 64, 0.6)',
        'rgba(199, 199, 199, 0.6)',
        'rgba(83, 102, 255, 0.6)'
        ],
        borderColor: [
        'rgba(255, 99, 132, 1)',
        'rgba(54, 162, 235, 1)',
        'rgba(255, 206, 86, 1)',
        'rgba(75, 192, 192, 1)',
        'rgba(153, 102, 255, 1)',
        'rgba(255, 159, 64, 1)',
        'rgba(199, 199, 199, 1)',
        'rgba(83, 102, 255, 1)'
        ],
        borderWidth: 1
        }]
        };
        
        new Chart(distributionCtx, {
        type: 'bar',
        data: distributionData,
        options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
        y: {
        beginAtZero: true,
        title: {
        display: true,
        text: '请求数'
        }
        }},
        x: {
        title: {
        display: true,
        text: '响应时间区间'
        }
        }
        }
        }
        });
        
        // 错误统计图表
        const errorCtx = document.getElementById('errorChart').getContext('2d');
        const errorData = {
        labels: [%s],
        datasets: [{
        data: [%s],
        backgroundColor: [
        'rgba(255, 99, 132, 0.6)',
        'rgba(54, 162, 235, 0.6)',
        'rgba(255, 206, 86, 0.6)',
        'rgba(75, 192, 192, 0.6)',
        'rgba(153, 102, 255, 0.6)',
        'rgba(255, 159, 64, 0.6)',
        'rgba(199, 199, 199, 0.6)'
        ],
        borderColor: [
        'rgba(255, 99, 132, 1)',
        'rgba(54, 162, 235, 1)',
        'rgba(255, 206, 86, 1)',
        'rgba(75, 192, 192, 1)',
        'rgba(153, 102, 255, 1)',
        'rgba(255, 159, 64, 1)',
        'rgba(199, 199, 199, 1)'
        ],
        borderWidth: 1
        }]
        };
        
        new Chart(errorCtx, {
        type: 'pie',
        data: errorData,
        options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
        legend: {
        position: 'right'
        }
        }
        }
        });
        </script>
        """
        # 准备图表数据
        distribution_labels = ', '.join([f'"{item["range"]}"' for item in distribution])
        distribution_counts = ', '.join([str(item["count"]) for item in distribution])

        error_labels = []
        error_counts = []

        # 只取前7个错误类型（图表颜色有限）
        error_items = list(errors.items())[:7]

        for error, count in error_items:
            # 限制错误描述长度
            display_error = error[:20] + "..." if len(error) > 20 else error
            error_labels.append(f'"{display_error}"')
            error_counts.append(str(count))

        error_labels_str = ', '.join(error_labels)
        error_counts_str = ', '.join(error_counts)

        # 替换占位符
        html_js = html_js % (distribution_labels, distribution_counts,
                             error_labels_str, error_counts_str)

        # 生成页脚
        html_footer = """
        <div class="footer">
        <p>性能测试报告由 OmniTest 自动化测试框架生成</p>
        </div>
        </div>
        </body>
        </html>
        """
        # 组合所有部分
        html_content = html_header + html_summary + html_distribution + \
                       html_details + html_errors + html_js + html_footer

        return html_content

    def compare_performance_results(self, results_files: List[str],
                                    output_file: Optional[str] = None) -> str:
        """
        比较多个性能测试结果
        
        Args:
            results_files: 结果文件路径列表
            output_file: 输出比较报告路径, 如不指定则自动生成
            
        Returns:
            str: 生成的比较报告文件路径
        """
        logger.info(f"开始比较性能测试结果,文件数: {len(results_files)}")

        # 分析每个文件
        all_analysis = []

        for file_path in results_files:
            try:
                # 读取结果文件
                with open(file_path, "r", encoding = "utf-8") as f:
                    results = json.load(f)

                # 分析结果
                analysis = self._calculate_summary_stats(results)

                # 添加文件标识
                file_name = os.path.basename(file_path)
                analysis["file_name"] = file_name
                analysis["file_path"] = file_path

                all_analysis.append(analysis)
                logger.info(f"已分析结果文件: {file_name}")
            except Exception as e:
                logger.error(f"分析结果文件 {file_path} 失败: {str(e)}")

        if not all_analysis:
            logger.warning("没有成功分析的结果文件")
        raise ValueError("没有成功分析的结果文件")

        # 生成比较报告
        if not output_file:
            # 自动生成文件名
            timestamp = self.utils.get_timestamp()
            output_file = os.path.join(
                config.REPORT_DIR,
                f"performance_comparison_{timestamp}.html"
            )

        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file), exist_ok = True)

        # 生成HTML比较报告
        html_content = self._generate_comparison_report(all_analysis)

        # 保存报告
        with open(output_file, "w", encoding = "utf-8") as f:
            f.write(html_content)

        logger.info(f"性能测试结果比较报告生成完成,保存到: {output_file}")
        return output_file

    def _generate_comparison_report(self, analysis_list: List[Dict[str, Any]]) -> str:
        """
        生成比较报告HTML内容
        
        Args:
            analysis_list: 分析结果列表
            
        Returns:
            str: HTML报告内容
        """
        # 生成报告头部
        html_header = """
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>性能测试结果比较报告</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css">
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {
                    font-family: 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    background-color: #f5f5f5;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }
                .header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 10px;
                    margin-bottom: 30px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }
                .card {
                    background-color: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
                    padding: 20px;
                    margin-bottom: 20px;
                }
                .card h2 {
                    color: #444;
                    margin-bottom: 20px;
                    font-size: 1.5rem;
                    border-bottom: 2px solid #eee;
                    padding-bottom: 10px;
                }
                .table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 20px;
                }
                .table th, .table td {
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }
                .table th {
                    background-color: #f8f9fa;
                    font-weight: 600;
                    color: #444;
                }
                .table tr:hover {
                    background-color: #f5f5f5;
                }
                .chart-container {
                    position: relative;
                    height: 400px;
                    margin-bottom: 30px;
                }
                .improvement {
                    color: #28a745;
                    font-weight: bold;
                }
                .regression {
                    color: #dc3545;
                    font-weight: bold;
                }
                .no-change {
                    color: #6c757d;
                }
                .footer {
                    text-align: center;
                    margin-top: 40px;
                    padding: 20px;
                    color: #666;
                    font-size: 0.9rem;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>性能测试结果比较报告</h1>
                    <p>生成时间: {timestamp}</p>
                </div>
        """
        # 生成时间戳
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        html_header = html_header.format(timestamp = timestamp)

        # 生成比较表格
        html_table = """
        <div class="card">
        <h2>测试结果比较</h2>
        <table class="table">
        <thead>
        <tr>
        <th>测试文件</th>
        <th>总请求数</th>
        <th>成功率</th>
        <th>平均响应时间</th>
        <th>90% 响应时间</th>
        <th>99% 响应时间</th>
        </tr>
        </thead>
        <tbody>
        """
        # 提取数据用于图表
        labels = []
        avg_response_times = []
        success_rates = []

        for analysis in analysis_list:
            file_name = analysis.get("file_name", "unknown")

            # 添加到图表数据
            labels.append(file_name)
            avg_response_times.append(analysis.get("avg_response_time", 0))
            success_rates.append(analysis.get("success_rate", 0))

        html_table += f"""
                            <tr>
                                <td>{file_name}</td>
                                <td>{analysis.get('total_requests', 0)}</td>
                                <td>{analysis.get('success_rate', 0)}%</td>
                                <td>{analysis.get('avg_response_time', 0)}ms</td>
                                <td>{analysis.get('p90_response_time', 0)}ms</td>
                                <td>{analysis.get('p99_response_time', 0)}ms</td>
                            </tr>
            """
        html_table += """
                        </tbody>
                    </table>
                </div>
        """
        # 生成图表
        html_charts = """
        <div class="card">
        <h2>性能对比图表</h2>
        <div class="chart-container">
        <canvas id="comparisonChart"></canvas>
        </div>
        </div>
        """
        # 生成JavaScript代码 - 避免嵌套过深的f-string表达式
        # 先将数据转换为JSON字符串
        labels_json = json.dumps(labels)
        avg_response_times_json = json.dumps(avg_response_times)
        success_rates_json = json.dumps(success_rates)

        html_js = """
        <script>
        // 性能比较图表
        const ctx = document.getElementById('comparisonChart').getContext('2d');
        
        // 准备数据
        const labels = {0};
        const avgResponseTimes = {1};
        const successRates = {2};
        
        // 创建图表
        new Chart(ctx, {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: [
                    {{
                        label: '平均响应时间 (ms)',
                        data: avgResponseTimes,
                        backgroundColor: 'rgba(255, 99, 132, 0.6)',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 1,
                        yAxisID: 'y'
                    }},
                    {{
                        label: '成功率 (%)',
                        data: successRates,
                        backgroundColor: 'rgba(54, 162, 235, 0.6)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1,
                        type: 'line',
                        yAxisID: 'y1'
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        position: 'left',
                        title: {{
                            display: true,
                            text: '平均响应时间 (ms)'
                        }}
                    }},
                    y1: {{
                        beginAtZero: true,
                        position: 'right',
                        title: {{
                            display: true,
                            text: '成功率 (%)'
                        }},
                        max: 100,
                        grid: {{
                            drawOnChartArea: false
                        }}
                    }}
                }}
            }}
        }});
        </script>
        """.format(labels_json, avg_response_times_json, success_rates_json)
        # 生成页脚
        html_footer = """
        <div class="footer">
        <p>性能测试结果比较报告由 OmniTest 自动化测试框架生成</p>
        </div>
        </div>
        </body>
        </html>
        """
        # 组合所有部分
        html_content = html_header + html_table + html_charts + html_js + html_footer

        return html_content

        # 创建性能测试工具实例
        performance_utils = PerformanceUtils()
