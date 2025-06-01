#!/usr/bin/env python3
"""Local validation script for Balena Cloud integration."""

import json
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and report the result."""
    print(f"🔍 {description}...")
    try:
        # Set DISPLAY to empty to run headless
        env = os.environ.copy()
        env['DISPLAY'] = ''
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)
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

        print("✅ manifest.json validation - PASSED")
        return True

    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in manifest.json: {e}")
        return False
    except Exception as e:
        print(f"❌ Error validating manifest.json: {e}")
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
                    print("Creating services.yaml file...")
                    return False
                else:
                    print("✅ Services validation - PASSED")
                    return True

    print("✅ No services registered - PASSED")
    return True


def main():
    """Main validation function."""
    print("🚀 Running Local Validation for Balena Cloud Integration")
    print("=" * 60)

    os.chdir(Path(__file__).parent.parent)

    validation_results = []

    # Install test dependencies first (like GitHub Actions)
    print("📦 Installing test dependencies...")
    install_result = run_command(
        "pip install -r tests/requirements.txt",
        "Install test dependencies"
    )
    validation_results.append(install_result)

    # 1. Validate manifest
    validation_results.append(validate_manifest())

    # 2. Validate services
    validation_results.append(validate_services())

    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)

    passed = sum(validation_results)
    total = len(validation_results)

    if passed == total:
        print(f"🎉 ALL VALIDATIONS PASSED ({passed}/{total})")
        print("✅ Integration is ready for push!")
        return 0
    else:
        failed = total - passed
        print(f"❌ VALIDATIONS FAILED ({failed}/{total} failed)")
        print("⚠️  Please fix the issues above before pushing.")
        return 1


if __name__ == "__main__":
    sys.exit(main())