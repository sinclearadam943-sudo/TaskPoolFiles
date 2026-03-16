#!/usr/bin/env python3
"""
通用自动化测试框架核心实现
"""

import sys
import os
import json
import time
import traceback
import importlib
import inspect
from dataclasses import dataclass, field
from enum import Enum
from multiprocessing import Pool
from typing import List, Callable, Dict, Optional, Any

class TestStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"

@dataclass
class TestCase:
    name: str
    func: Callable
    fixture_deps: List[str] = field(default_factory=list)
    status: TestStatus = TestStatus.PENDING
    duration: float = 0.0
    error: Optional[str] = None

@dataclass
class TestResult:
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    test_cases: List[TestCase] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time
    
    @property
    def success_rate(self) -> float:
        return self.passed / self.total if self.total > 0 else 0.0

@dataclass
class Fixture:
    name: str
    func: Callable
    scope: str = "function"  # function/class/module/session
    cached_value: Any = None

class TestFramework:
    def __init__(self):
        self.fixtures: Dict[str, Fixture] = {}
        self.test_cases: List[TestCase] = []
        self.result = TestResult()
    
    def fixture(self, name: str = None, scope: str = "function"):
        """Fixture装饰器"""
        def decorator(func):
            fixture_name = name or func.__name__
            self.fixtures[fixture_name] = Fixture(fixture_name, func, scope)
            return func
        return decorator
    
    def test(self, name: str = None):
        """测试用例装饰器"""
        def decorator(func):
            test_name = name or func.__name__
            # 分析参数，找到fixture依赖
            sig = inspect.signature(func)
            deps = list(sig.parameters.keys())
            self.test_cases.append(TestCase(test_name, func, deps))
            return func
        return decorator
    
    def resolve_fixture(self, fixture_name: str) -> Any:
        """解析fixture"""
        fixture = self.fixtures.get(fixture_name)
        if not fixture:
            raise ValueError(f"Fixture {fixture_name} not found")
        
        if fixture.scope in ("module", "session") and fixture.cached_value is not None:
            return fixture.cached_value
        
        # 执行fixture，处理yield
        gen = fixture.func()
        value = next(gen)
        fixture.cached_value = value
        # 保存cleanup供后面使用
        self._cleanups.append((gen, fixture))
        return value
    
    def resolve_test_dependencies(self, test: TestCase) -> Dict[str, Any]:
        """解析测试的所有依赖fixture"""
        kwargs = {}
        for dep in test.fixture_deps:
            kwargs[dep] = self.resolve_fixture(dep)
        return kwargs
    
    def run_single_test(self, test: TestCase) -> TestCase:
        """运行单个测试"""
        start = time.time()
        self._cleanups = []
        
        try:
            kwargs = self.resolve_test_dependencies(test)
            test.func(**kwargs)
            test.status = TestStatus.PASSED
        except Exception as e:
            test.status = TestStatus.FAILED
            test.error = "".join(traceback.format_exception(*sys.exc_info()))
        finally:
            # 执行cleanup
            for gen, fixture in reversed(self._cleanups):
                try:
                    next(gen)
                except StopIteration:
                    pass
                if fixture.scope not in ("module", "session"):
                    fixture.cached_value = None
        
        test.duration = time.time() - start
        return test
    
    def discover_tests(self, directory: str = ".") -> List[TestCase]:
        """发现目录下所有测试用例"""
        tests = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.startswith("test_") and file.endswith(".py"):
                    path = os.path.join(root, file)
                    module_name = path.replace("/", ".").rsplit(".", 1)[0]
                    module = importlib.import_module(module_name)
                    # 收集模块中被@Test装饰的测试
                    for name, obj in inspect.getmembers(module):
                        if hasattr(obj, "_is_test"):
                            tests.append(TestCase(name, obj))
        return tests
    
    def run_tests_parallel(self, tests: List[TestCase], nprocs: int = None) -> TestResult:
        """并行运行测试"""
        if nprocs is None:
            nprocs = os.cpu_count() or 4
        
        with Pool(nprocs) as pool:
            results = pool.map(self.run_single_test, tests)
        
        return self._collect_results(results)
    
    def run_tests_sequential(self, tests: List[TestCase]) -> TestResult:
        """顺序运行测试"""
        results = [self.run_single_test(test) for test in tests]
        return self._collect_results(results)
    
    def _collect_results(self, tests: List[TestCase]) -> TestResult:
        """收集测试结果"""
        result = TestResult(
            total=len(tests),
            start_time=self.result.start_time,
            end_time=time.time()
        )
        
        for test in tests:
            result.test_cases.append(test)
            if test.status == TestStatus.PASSED:
                result.passed += 1
            elif test.status == TestStatus.FAILED:
                result.failed += 1
            elif test.status == TestStatus.SKIPPED:
                result.skipped += 1
        
        return result
    
    def generate_html_report(self, result: TestResult, output_path: str = "report.html"):
        """生成HTML测试报告"""
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .summary { background: #f5f5f5; padding: 15px; border-radius: 5px; }
        .passed { color: green; }
        .failed { color: red; }
        .test-case { border-bottom: 1px solid #eee; padding: 10px 0; }
    </style>
</head>
<body>
<h1>Test Report</h1>
<div class="summary">
    <h2>Summary</h2>
    <p>Total: {total} | Passed: <span class="passed">{passed}</span> | Failed: <span class="failed">{failed}</span> | Skipped: {skipped}</p>
    <p>Duration: {duration:.2f}s | Success rate: {success_rate:.1%}</p>
</div>
<h2>Failed Tests</h2>
{failed_tests}
</body>
</html>
        """.format(
            total=result.total,
            passed=result.passed,
            failed=result.failed,
            skipped=result.skipped,
            duration=result.duration,
            success_rate=result.success_rate,
            failed_tasks="\n".join([
                f"<div class='test-case'><h3>{t.name}</h3><pre>{t.error}</pre></div>"
                for t in result.test_cases if t.status == TestStatus.FAILED
            ])
        )
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_template)
        
        print(f"Report generated: {output_path}")

if __name__ == "__main__":
    # 使用示例
    framework = TestFramework()
    
    # 示例fixture
    @framework.fixture(scope="session")
    def database():
        print("Setup database")
        conn = "fake_connection"
        yield conn
        print("Teardown database")
    
    # 示例测试
    @framework.test()
    def test_addition(database):
        assert 1 + 1 == 2
    
    @framework.test()
    def test_subtraction(database):
        assert 3 - 1 == 1
    
    # 运行
    result = framework.run_tests_sequential(framework.test_cases)
    
    print(f"\nResult: {result.passed}/{result.total} passed")
    framework.generate_html_report(result)
    
    sys.exit(0 if result.failed == 0 else 1)
