"""Test runner for Balena Cloud integration tests."""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import pytest


def run_tests():
    """Run all tests for the Balena Cloud integration."""

    print("🧪 Starting Balena Cloud Integration Test Suite")
    print("=" * 60)

    # Get the test directory
    test_dir = Path(__file__).parent

    # Define test configurations
    test_configs = [
        {
            "name": "Unit Tests",
            "path": test_dir / "test_units.py",
            "description": "Testing individual components and functions",
        },
        {
            "name": "API Integration Tests",
            "path": test_dir / "test_api_integration.py",
            "description": "Testing Balena Cloud API client functionality",
        },
        {
            "name": "Home Assistant Integration Tests",
            "path": test_dir / "test_integration.py",
            "description": "Testing Home Assistant platform integration",
        },
        {
            "name": "Cross-Platform Tests",
            "path": test_dir / "test_cross_platform.py",
            "description": "Testing compatibility across device architectures",
        },
        {
            "name": "End-to-End Tests",
            "path": test_dir / "test_end_to_end.py",
            "description": "Testing complete user workflows",
        },
    ]

    total_start_time = time.time()
    results = {}

    for config in test_configs:
        print(f"\n📋 Running {config['name']}")
        print(f"   {config['description']}")
        print("-" * 60)

        start_time = time.time()

        # Run the specific test file
        exit_code = pytest.main([
            str(config["path"]),
            "-v",
            "--tb=short",
            "--disable-warnings",
            "-q"
        ])

        end_time = time.time()
        duration = end_time - start_time

        results[config["name"]] = {
            "exit_code": exit_code,
            "duration": duration,
            "status": "PASSED" if exit_code == 0 else "FAILED"
        }

        print(f"   ✓ Completed in {duration:.2f}s - {results[config['name']]['status']}")

    # Print summary
    total_duration = time.time() - total_start_time

    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    passed_count = sum(1 for r in results.values() if r["exit_code"] == 0)
    total_count = len(results)

    for name, result in results.items():
        status_icon = "✅" if result["exit_code"] == 0 else "❌"
        print(f"{status_icon} {name}: {result['status']} ({result['duration']:.2f}s)")

    print(f"\nOverall: {passed_count}/{total_count} test suites passed")
    print(f"Total time: {total_duration:.2f}s")

    if passed_count == total_count:
        print("\n🎉 All tests passed! Integration is ready for deployment.")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} test suite(s) failed. Please review the output above.")
        return 1


def run_specific_test_category(category: str):
    """Run a specific category of tests."""

    categories = {
        "unit": "test_units.py",
        "api": "test_api_integration.py",
        "integration": "test_integration.py",
        "cross-platform": "test_cross_platform.py",
        "e2e": "test_end_to_end.py",
        "all": None,  # Run all tests
    }

    if category not in categories:
        print(f"❌ Unknown test category: {category}")
        print(f"Available categories: {', '.join(categories.keys())}")
        return 1

    test_dir = Path(__file__).parent

    if category == "all":
        return run_tests()
    else:
        test_file = test_dir / categories[category]
        print(f"🧪 Running {category} tests from {test_file}")

        exit_code = pytest.main([
            str(test_file),
            "-v",
            "--tb=short",
        ])

        return exit_code


def run_performance_tests():
    """Run performance-specific tests."""

    print("⚡ Running Performance Tests")
    print("=" * 60)

    test_dir = Path(__file__).parent

    # Run with performance-focused options
    exit_code = pytest.main([
        str(test_dir),
        "-v",
        "-k", "performance or large_dataset or concurrent or large_fleet",
        "--tb=short",
        "--disable-warnings",
    ])

    return exit_code


def run_security_tests():
    """Run security-specific tests."""

    print("🔒 Running Security Tests")
    print("=" * 60)

    test_dir = Path(__file__).parent

    # Run with security-focused options
    exit_code = pytest.main([
        str(test_dir),
        "-v",
        "-k", "security or validation or sanitization or token or auth",
        "--tb=short",
        "--disable-warnings",
    ])

    return exit_code


def run_workflow_tests():
    """Run workflow and user scenario tests."""

    print("🔄 Running Workflow Tests")
    print("=" * 60)

    test_dir = Path(__file__).parent

    # Run with workflow-focused options
    exit_code = pytest.main([
        str(test_dir),
        "-v",
        "-k", "workflow or scenario or user or real_world",
        "--tb=short",
        "--disable-warnings",
    ])

    return exit_code


def run_coverage_report():
    """Run tests with coverage reporting."""

    print("📈 Running Tests with Coverage Analysis")
    print("=" * 60)

    test_dir = Path(__file__).parent
    project_dir = test_dir.parent

    # Run with coverage
    exit_code = pytest.main([
        str(test_dir),
        "--cov=custom_components/balena_cloud",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-fail-under=80",  # Require 80% coverage
        "-v",
    ])

    if exit_code == 0:
        print("\n📊 Coverage report generated in htmlcov/index.html")

    return exit_code


def run_compatibility_tests():
    """Run compatibility tests for different device types and architectures."""

    print("🔧 Running Compatibility Tests")
    print("=" * 60)

    test_dir = Path(__file__).parent

    # Run with compatibility-focused options
    exit_code = pytest.main([
        str(test_dir),
        "-v",
        "-k", "compatibility or architecture or device_type or mixed",
        "--tb=short",
        "--disable-warnings",
    ])

    return exit_code


def generate_test_report():
    """Generate a comprehensive test report."""

    print("📝 Generating Comprehensive Test Report")
    print("=" * 60)

    test_dir = Path(__file__).parent

    # Generate HTML report
    exit_code = pytest.main([
        str(test_dir),
        "--html=test_report.html",
        "--self-contained-html",
        "-v",
    ])

    if exit_code == 0:
        print("\n📄 Test report generated: test_report.html")

    return exit_code


def print_help():
    """Print help information."""

    print("🧪 Balena Cloud Integration Test Runner")
    print("=" * 60)
    print("\nAvailable commands:")
    print("  all             - Run all test suites")
    print("  unit            - Run unit tests only")
    print("  api             - Run API integration tests only")
    print("  integration     - Run Home Assistant integration tests only")
    print("  cross-platform  - Run cross-platform tests only")
    print("  e2e             - Run end-to-end tests only")
    print("  performance     - Run performance tests only")
    print("  security        - Run security tests only")
    print("  workflow        - Run workflow and user scenario tests")
    print("  compatibility   - Run compatibility tests")
    print("  coverage        - Run tests with coverage analysis")
    print("  report          - Generate comprehensive HTML test report")
    print("  help            - Show this help message")
    print("\nExamples:")
    print("  python test_runner.py unit")
    print("  python test_runner.py performance")
    print("  python test_runner.py coverage")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command in ["unit", "api", "integration", "cross-platform", "e2e", "all"]:
            sys.exit(run_specific_test_category(command))
        elif command == "performance":
            sys.exit(run_performance_tests())
        elif command == "security":
            sys.exit(run_security_tests())
        elif command == "workflow":
            sys.exit(run_workflow_tests())
        elif command == "compatibility":
            sys.exit(run_compatibility_tests())
        elif command == "coverage":
            sys.exit(run_coverage_report())
        elif command == "report":
            sys.exit(generate_test_report())
        elif command == "help":
            print_help()
            sys.exit(0)
        else:
            print(f"❌ Unknown command: {command}")
            print_help()
            sys.exit(1)
    else:
        sys.exit(run_tests())