#!/usr/bin/env python3
"""Simple local validation script for Balena Cloud integration (no Docker required)."""

import json
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and report the result."""
    print(f"🔍 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            return True
        else:
            print(f"❌ {description} - FAILED")
            if result.stdout:
                print("STDOUT:", result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            return False
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False


def validate_manifest():
    """Validate manifest.json."""
    print("🔍 Validating manifest.json...")

    manifest_path = Path("custom_components/balena_cloud/manifest.json")
    if not manifest_path.exists():
        print("❌ manifest.json not found!")
        return False

    try:
        with open(manifest_path) as f:
            manifest = json.load(f)

        # Check for invalid fields that HACS doesn't allow
        invalid_fields = []
        hacs_allowed_fields = {
            "domain", "name", "codeowners", "config_flow", "dependencies",
            "documentation", "integration_type", "iot_class", "issue_tracker",
            "loggers", "requirements", "version"
        }

        for field in manifest.keys():
            if field not in hacs_allowed_fields:
                invalid_fields.append(field)

        if invalid_fields:
            print(f"❌ Invalid manifest fields: {invalid_fields}")
            print("These fields are not allowed in Home Assistant manifests:")
            for field in invalid_fields:
                print(f"  - {field}: {manifest[field]}")
            return False

        # Check required fields
        required_fields = ["domain", "name", "version", "requirements"]
        missing_fields = []
        for field in required_fields:
            if field not in manifest:
                missing_fields.append(field)

        if missing_fields:
            print(f"❌ Missing required fields: {missing_fields}")
            return False

        print("✅ manifest.json validation - PASSED")
        return True

    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in manifest.json: {e}")
        return False
    except Exception as e:
        print(f"❌ Error validating manifest.json: {e}")
        return False


def validate_hacs_json():
    """Validate hacs.json."""
    print("🔍 Validating hacs.json...")

    hacs_path = Path("hacs.json")
    if not hacs_path.exists():
        print("❌ hacs.json not found!")
        return False

    try:
        with open(hacs_path) as f:
            hacs_config = json.load(f)

        # Check required fields
        required_fields = ["name", "homeassistant"]
        missing_fields = []
        for field in required_fields:
            if field not in hacs_config:
                missing_fields.append(field)

        if missing_fields:
            print(f"❌ Missing required HACS fields: {missing_fields}")
            return False

        print("✅ hacs.json validation - PASSED")
        return True

    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in hacs.json: {e}")
        return False
    except Exception as e:
        print(f"❌ Error validating hacs.json: {e}")
        return False


def validate_services():
    """Check if services.yaml is needed."""
    print("🔍 Checking services configuration...")

    # Check if services.py registers any services
    services_path = Path("custom_components/balena_cloud/services.py")
    if services_path.exists():
        with open(services_path) as f:
            content = f.read()
            if "async_register" in content:
                # Services are registered in code, check if services.yaml exists
                services_yaml = Path("custom_components/balena_cloud/services.yaml")
                if not services_yaml.exists():
                    print("❌ Integration registers services but services.yaml is missing!")
                    return False
                else:
                    print("✅ Services validation - PASSED")
                    return True

    print("✅ No services registered - PASSED")
    return True


def validate_python_imports():
    """Check if Python files can be imported."""
    print("🔍 Checking Python import syntax...")

    py_files = list(Path("custom_components/balena_cloud").glob("*.py"))
    failed_files = []

    for py_file in py_files:
        if py_file.name.startswith("_"):
            continue

        try:
            # Check syntax by compiling
            with open(py_file) as f:
                content = f.read()
            compile(content, py_file.name, 'exec')
        except SyntaxError as e:
            failed_files.append(f"{py_file.name}: {e}")
        except Exception as e:
            failed_files.append(f"{py_file.name}: {e}")

    if failed_files:
        print("❌ Python syntax errors found:")
        for error in failed_files:
            print(f"   - {error}")
        return False

    print("✅ Python import syntax - PASSED")
    return True


def main():
    """Main validation function."""
    print("🚀 Running Simple Local Validation for Balena Cloud Integration")
    print("   (No Docker required - basic checks only)")
    print("=" * 70)

    os.chdir(Path(__file__).parent.parent)

    validation_results = []

    # 1. Validate manifest
    validation_results.append(validate_manifest())

    # 2. Validate HACS configuration
    validation_results.append(validate_hacs_json())

    # 3. Validate services
    validation_results.append(validate_services())

    # 4. Check Python syntax
    validation_results.append(validate_python_imports())

    # 5. Code formatting with Black
    validation_results.append(run_command(
        "black --check --diff custom_components/",
        "Black code formatting"
    ))

    # 6. Import sorting with isort
    validation_results.append(run_command(
        "isort --check-only --diff custom_components/",
        "isort import sorting"
    ))

    # 7. Linting with flake8
    validation_results.append(run_command(
        "flake8 custom_components/ --max-line-length=100 --ignore=E203,W503",
        "flake8 linting"
    ))

    # 8. Security scan with Bandit
    validation_results.append(run_command(
        "bandit -r custom_components/ -f json -o bandit-report.json",
        "Bandit security scan"
    ))

    print("\n" + "=" * 70)
    print("📊 VALIDATION SUMMARY")
    print("=" * 70)

    passed = sum(validation_results)
    total = len(validation_results)

    if passed == total:
        print(f"🎉 ALL BASIC VALIDATIONS PASSED ({passed}/{total})")
        print("✅ Integration is ready for push!")
        print("\n💡 For full validation including HACS/Hassfest:")
        print("   - Push to GitHub (GitHub Actions will run full validation)")
        print("   - Or run: python scripts/validate_local.py (requires Docker)")
        return 0
    else:
        failed = total - passed
        print(f"❌ VALIDATIONS FAILED ({failed}/{total} failed)")
        print("⚠️  Please fix the issues above before pushing.")
        return 1


if __name__ == "__main__":
    sys.exit(main())