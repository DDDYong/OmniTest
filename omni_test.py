"""
-------------------------------------------------
File:           omni_test.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:
OmniTest自动化测试框架的API接口模块,提供简洁的编程API接口来运行各类测试
-------------------------------------------------
"""

import os
import sys
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from run import ExecutionRequest, TestRunner, execute_request
from utils.logger import logger
from utils.path import path_util


@dataclass(frozen = True)
class ExecutionResult:
    exit_code: int | None = None
    error: Exception | None = None
    test_kind: str = ""
    target: Mapping[str, Any] = field(default_factory = lambda: MappingProxyType({}))
    report_requested: bool = False
    report_generated: bool = False
    report_skipped_reason: str | None = None
    report_info: Mapping[str, Any] = field(default_factory = lambda: MappingProxyType({}))


class OmniTest:
    """
    OmniTest框架的主要API类
    提供简洁的编程接口来运行各类测试
    """

    __test__ = False

    def __init__(self) -> None:
        """初始化OmniTest实例"""
        self.runner = TestRunner()
        self.last_exit_code = None
        self.last_error = None
        self.last_result = ExecutionResult()

    @staticmethod
    def _freeze_mapping(data: dict[str, Any]) -> Mapping[str, Any]:
        return MappingProxyType(dict(data))

    def _build_report_info(self, *, generated: bool, skipped_reason: str | None) -> Mapping[str, Any]:
        report_info = path_util.get_current_run_context(create_dirs = generated)
        report_info.update({
            'report_generated': generated,
            'report_skipped_reason': skipped_reason,
        })
        return self._freeze_mapping(report_info)

    def _build_execution_request(
            self,
            *,
            command: str,
            test_dir: str | None = None,
            test_file: str | None = None,
            markers: str | None = None,
            num_workers: int = 2,
            html_report: bool = False,
            users: int = 100,
            spawn_rate: int = 10,
            run_time: str = '5m',
            auto_clean: bool = True,
            auto_report: bool = True,
    ) -> ExecutionRequest:
        return ExecutionRequest(
            command = command,
            test_dir = test_dir,
            test_file = test_file,
            markers = markers,
            num_workers = num_workers,
            html_report = html_report,
            users = users,
            spawn_rate = spawn_rate,
            run_time = run_time,
            auto_clean = auto_clean,
            auto_report = auto_report,
        )

    def _fail_execution(
            self,
            *,
            error: Exception,
            test_kind: str,
            target: dict[str, Any],
            auto_report: bool,
            skipped_reason: str,
    ) -> "OmniTest":
        self.last_exit_code = None
        self.last_error = error
        self.last_result = ExecutionResult(
            exit_code = None,
            error = error,
            test_kind = test_kind,
            target = self._freeze_mapping(target),
            report_requested = auto_report,
            report_generated = False,
            report_skipped_reason = skipped_reason,
            report_info = self._build_report_info(generated = False, skipped_reason = skipped_reason),
        )
        return self

    def _execute_test_flow(
            self,
            *,
            test_kind: str,
            title: str,
            target: dict[str, Any],
            request: ExecutionRequest,
            auto_clean: bool,
            auto_report: bool,
            skip_invalid_target_report: bool,
    ) -> "OmniTest":
        logger.info("=" * 60)
        logger.info(f"开始执行{title}")
        for key, value in target.items():
            logger.info(f"{key}: {value}")
        logger.info(f"自动清理: {auto_clean}")
        logger.info(f"自动报告: {auto_report}")
        logger.info("=" * 60)

        if auto_clean:
            logger.info("执行自动清理报告操作")
            clean_result = self.clean()
            if clean_result.last_error is not None:
                logger.error(f"{title}执行失败: 清理阶段异常: {str(clean_result.last_error)}", exc_info = True)
                logger.info("=" * 60)
                return self._fail_execution(
                    error = clean_result.last_error,
                    test_kind = test_kind,
                    target = target,
                    auto_report = auto_report,
                    skipped_reason = "cleanup_failed",
                )
        else:
            logger.info("跳过自动清理报告")

        logger.info(f"正在运行{title} - 开始执行测试用例")
        report_generated = False
        report_skipped_reason = None
        report_error = None
        try:
            exit_code = execute_request(request, self.runner, include_side_effects = False)
            self.last_exit_code = exit_code
            self.last_error = None
            logger.info(f"{title}执行完成")
        except Exception as e:
            logger.error(f"{title}执行失败: {str(e)}", exc_info = True)
            logger.info("=" * 60)
            return self._fail_execution(
                error = e,
                test_kind = test_kind,
                target = target,
                auto_report = auto_report,
                skipped_reason = "runner_exception",
            )

        invalid_code = getattr(TestRunner, "INVALID_TEST_TARGET_EXIT_CODE", 4)
        if exit_code != 0:
            logger.warning(f"{title}退出码: {exit_code}")

        should_generate_report = auto_report
        if skip_invalid_target_report and exit_code == invalid_code:
            should_generate_report = False
            report_skipped_reason = "invalid_test_target"

        if should_generate_report:
            logger.info("准备自动生成测试报告")
            try:
                report_generated = self.runner.generate_allure_report(serve = False, wait_for_enter = False)
                self.runner.generate_report_index()
            except Exception as e:
                report_error = e
                report_skipped_reason = "report_generation_failed"
                self.last_error = e
                logger.error(f"{title}报告生成失败: {str(e)}", exc_info = True)
        elif auto_report and report_skipped_reason == "invalid_test_target":
            logger.warning(f"{title}目标无效,退出码: {exit_code},跳过报告生成")
        else:
            logger.info("跳过自动生成报告")

        self.last_result = ExecutionResult(
            exit_code = exit_code,
            error = report_error,
            test_kind = test_kind,
            target = self._freeze_mapping(target),
            report_requested = auto_report,
            report_generated = report_generated,
            report_skipped_reason = report_skipped_reason,
            report_info = self._build_report_info(generated = report_generated, skipped_reason = report_skipped_reason),
        )

        logger.info("=" * 60)
        return self

    def clean(self) -> "OmniTest":
        """清理测试报告目录"""

        self.last_exit_code = 0
        self.last_error = None
        logger.info("=" * 60)
        logger.info("开始清理测试报告和截图")
        try:
            self.runner.clean_reports()
            self.last_result = ExecutionResult(
                exit_code = 0,
                error = None,
                test_kind = 'clean',
                target = self._freeze_mapping({}),
                report_requested = False,
                report_generated = False,
                report_skipped_reason = None,
                report_info = self._build_report_info(generated = False, skipped_reason = None),
            )
            logger.info("测试报告和截图清理完成")
        except Exception as e:
            self.last_exit_code = None
            self.last_error = e
            self.last_result = ExecutionResult(
                exit_code = None,
                error = e,
                test_kind = 'clean',
                target = self._freeze_mapping({}),
                report_requested = False,
                report_generated = False,
                report_skipped_reason = 'cleanup_failed',
                report_info = self._build_report_info(generated = False, skipped_reason = 'cleanup_failed'),
            )
            logger.error(f"清理测试报告失败: {str(e)}", exc_info = True)
        logger.info("=" * 60)
        return self

    def api(self, test_dir = None, test_file = None, markers = None, auto_clean = True, auto_report = True) -> "OmniTest":
        """
        运行API测试

        Args:
            test_dir: 测试目录
            test_file: 测试文件
            markers: 测试标记
            auto_clean: 是否自动清理报告
            auto_report: 是否自动生成报告

        Returns:
            OmniTest: 返回实例本身以支持链式调用
        """
        return self._execute_test_flow(
            test_kind = "api",
            title = "API测试",
            target = {"测试目录": test_dir, "测试文件": test_file, "测试标记": markers},
            request = self._build_execution_request(
                command = 'api', test_dir = test_dir, test_file = test_file, markers = markers,
                auto_clean = auto_clean, auto_report = auto_report,
            ),
            auto_clean = auto_clean,
            auto_report = auto_report,
            skip_invalid_target_report = True,
        )

    def web(self, test_dir = None, test_file = None, markers = None, auto_clean = True, auto_report = True) -> "OmniTest":
        """
        运行Web测试

        Args:
            test_dir: 测试目录
            test_file: 测试文件
            markers: 测试标记
            auto_clean: 是否自动清理报告
            auto_report: 是否自动生成报告

        Returns:
            OmniTest: 返回实例本身以支持链式调用
        """
        return self._execute_test_flow(
            test_kind = "web",
            title = "Web测试",
            target = {"测试目录": test_dir, "测试文件": test_file, "测试标记": markers},
            request = self._build_execution_request(
                command = 'web', test_dir = test_dir, test_file = test_file, markers = markers,
                auto_clean = auto_clean, auto_report = auto_report,
            ),
            auto_clean = auto_clean,
            auto_report = auto_report,
            skip_invalid_target_report = True,
        )

    def app(self, test_dir = None, test_file = None, markers = None, auto_clean = True, auto_report = True) -> "OmniTest":
        """
        运行App测试

        Args:
            test_dir: 测试目录
            test_file: 测试文件
            markers: 测试标记
            auto_clean: 是否自动清理报告
            auto_report: 是否自动生成报告

        Returns:
            OmniTest: 返回实例本身以支持链式调用
        """
        return self._execute_test_flow(
            test_kind = "app",
            title = "App测试",
            target = {"测试目录": test_dir, "测试文件": test_file, "测试标记": markers},
            request = self._build_execution_request(
                command = 'app', test_dir = test_dir, test_file = test_file, markers = markers,
                auto_clean = auto_clean, auto_report = auto_report,
            ),
            auto_clean = auto_clean,
            auto_report = auto_report,
            skip_invalid_target_report = True,
        )

    def parallel(
        self,
        test_dir = None,
        test_file = None,
        markers = "parallel",
        num_workers = 2,
        html_report = False,
        workers = None,
        html = None,
        auto_clean = True,
        auto_report = True,
    ) -> "OmniTest":
        if workers is not None:
            num_workers = workers
        if html is not None:
            html_report = html

        return self._execute_test_flow(
            test_kind = "parallel",
            title = "并行测试",
            target = {
                "测试目录": test_dir,
                "测试文件": test_file,
                "测试标记": markers,
                "worker数量": num_workers,
                "HTML报告": html_report,
            },
            request = self._build_execution_request(
                command = 'parallel', test_dir = test_dir, test_file = test_file, markers = markers,
                num_workers = num_workers, html_report = html_report,
                auto_clean = auto_clean, auto_report = auto_report,
            ),
            auto_clean = auto_clean,
            auto_report = auto_report,
            skip_invalid_target_report = True,
        )

    def performance(self, test_file, users = 100, spawn_rate = 10, run_time = '5m') -> "OmniTest":
        """
        运行性能测试
        
        Args:
            test_file: 测试文件
            users: 用户数量
            spawn_rate: 每秒生成的用户数
            run_time: 运行时间
            
        Returns:
            OmniTest: 返回实例本身以支持链式调用
        """
        logger.info("=" * 60)
        logger.info("开始执行性能测试")
        logger.info(f"测试文件: {test_file}")
        logger.info(f"用户数量: {users}")
        logger.info(f"每秒生成用户数: {spawn_rate}")
        logger.info(f"运行时间: {run_time}")
        logger.info("=" * 60)

        try:
            logger.info("正在启动性能测试")
            request = self._build_execution_request(
                command = 'performance', test_file = test_file, users = users,
                spawn_rate = spawn_rate, run_time = run_time, auto_clean = False, auto_report = False,
            )
            exit_code = execute_request(request, self.runner, include_side_effects = False)
            self.last_exit_code = exit_code
            self.last_error = None
            self.last_result = ExecutionResult(
                exit_code = exit_code,
                error = None,
                test_kind = 'performance',
                target = self._freeze_mapping({
                    '测试文件': test_file,
                    '用户数量': users,
                    '每秒生成用户数': spawn_rate,
                    '运行时间': run_time,
                }),
                report_requested = False,
                report_generated = False,
                report_skipped_reason = None,
                report_info = self._build_report_info(generated = False, skipped_reason = None),
            )
            logger.info("性能测试执行完成")
        except Exception as e:
            self.last_exit_code = None
            self.last_error = e
            self.last_result = ExecutionResult(
                exit_code = None,
                error = e,
                test_kind = 'performance',
                target = self._freeze_mapping({
                    '测试文件': test_file,
                    '用户数量': users,
                    '每秒生成用户数': spawn_rate,
                    '运行时间': run_time,
                }),
                report_requested = False,
                report_generated = False,
                report_skipped_reason = 'runner_exception',
                report_info = self._build_report_info(generated = False, skipped_reason = 'runner_exception'),
            )
            logger.error(f"性能测试执行失败: {str(e)}", exc_info = True)

        logger.info("=" * 60)
        return self

    def all(self, auto_clean: bool = True, auto_report: bool = True) -> "OmniTest":
        """
        运行所有测试

        Args:
            auto_clean: 是否自动清理报告
            auto_report: 是否自动生成报告

        Returns:
            OmniTest: 返回实例本身以支持链式调用
        """
        return self._execute_test_flow(
            test_kind = "all",
            title = "所有测试",
            target = {},
            request = self._build_execution_request(command = 'all', auto_clean = auto_clean, auto_report = auto_report),
            auto_clean = auto_clean,
            auto_report = auto_report,
            skip_invalid_target_report = False,
        )

    def report(self, generate: bool = True, open: bool = True) -> "OmniTest":
        """
        生成和/或打开Allure报告

        Args:
            generate: 是否生成报告
            open: 是否打开报告

        Returns:
            OmniTest: 返回实例本身以支持链式调用
        """

        self.last_exit_code = 0
        self.last_error = None
        logger.info("=" * 60)
        logger.info("测试报告操作")
        logger.info(f"生成报告: {generate}")
        logger.info(f"打开报告: {open}")
        logger.info("=" * 60)

        try:
            if generate:
                logger.info("开始生成Allure报告")
                self.runner.generate_allure_report(serve = False, wait_for_enter = False)
                self.runner.generate_report_index()
                logger.info("Allure报告生成完成")

            if open:
                logger.info("开始打开Allure报告")
                self.runner.open_allure_report()
                logger.info("Allure报告已打开")

            self.last_result = ExecutionResult(
                exit_code = 0,
                error = None,
                test_kind = 'report',
                target = self._freeze_mapping({'generate': generate, 'open': open}),
                report_requested = generate,
                report_generated = generate,
                report_skipped_reason = None,
                report_info = self._build_report_info(generated = generate, skipped_reason = None),
            )
            logger.info("测试报告操作完成")
        except Exception as e:
            self.last_exit_code = None
            self.last_error = e
            self.last_result = ExecutionResult(
                exit_code = None,
                error = e,
                test_kind = 'report',
                target = self._freeze_mapping({'generate': generate, 'open': open}),
                report_requested = generate,
                report_generated = False,
                report_skipped_reason = 'report_operation_failed',
                report_info = self._build_report_info(generated = False, skipped_reason = 'report_operation_failed'),
            )
            logger.error(f"生成/打开测试报告失败: {str(e)}", exc_info = True)

        logger.info("=" * 60)
        return self


# 创建全局实例以便直接导入使用
ot = OmniTest()
