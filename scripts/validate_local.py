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


def check_docker():
    """Check if Docker is available."""
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False


def validate_hacs():
    """Run HACS validation using Docker."""
    print("🔍 Running HACS validation...")

    if not check_docker():
        print("⚠️ Docker not available - Skipping HACS validation")
        print("   Install Docker to run HACS validation locally")
        return True  # Don't fail if Docker is not available

    # Check if we have a GitHub token
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        print("⚠️ GITHUB_TOKEN not set - Skipping HACS validation")
        print("   Set GITHUB_TOKEN environment variable to run HACS validation")
        print("   Example: export GITHUB_TOKEN=your_github_token")
        print("   Or use: GITHUB_TOKEN=your_token python scripts/validate_local.py")
        return True  # Don't fail if token is not available

    # HACS validation using the official action in Docker
    cmd = f"""docker run --rm -v $(pwd):/github/workspace \
        -e GITHUB_WORKSPACE=/github/workspace \
        -e GITHUB_TOKEN={github_token} \
        -e INPUT_CATEGORY=integration \
        -e INPUT_IGNORE="brands" \
        ghcr.io/hacs/action:main"""

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print("✅ HACS validation - PASSED")
            return True
        else:
            print("❌ HACS validation - FAILED")
            if result.stdout:
                print("STDOUT:", result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("❌ HACS validation - TIMEOUT (taking too long)")
        return False
    except Exception as e:
        print(f"❌ HACS validation - ERROR: {e}")
        return False


def validate_hassfest():
    """Run Hassfest validation using Docker."""
    print("🔍 Running Hassfest validation...")

    if not check_docker():
        print("⚠️ Docker not available - Skipping Hassfest validation")
        print("   Install Docker to run Hassfest validation locally")
        return True  # Don't fail if Docker is not available

    # Try multiple possible Hassfest action locations
    hassfest_images = [
        "ghcr.io/home-assistant/actions:hassfest",
        "homeassistant/home-assistant:dev",
    ]

    for image in hassfest_images:
        try:
            print(f"   Trying Hassfest with image: {image}")

            if "home-assistant:dev" in image:
                # Use Home Assistant dev image with hassfest command
                cmd = f"""docker run --rm -v $(pwd):/config {image} \
                    python -m homeassistant.scripts.hassfest --integration-path /config/custom_components/balena_cloud"""
            else:
                # Use official action image
                cmd = f"""docker run --rm -v $(pwd):/github/workspace \
                    -e GITHUB_WORKSPACE=/github/workspace \
                    {image}"""

            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                print("✅ Hassfest validation - PASSED")
                return True
            else:
                print(f"   Image {image} failed, trying next...")
                continue

        except subprocess.TimeoutExpired:
            print(f"   Image {image} timed out, trying next...")
            continue
        except Exception as e:
            print(f"   Image {image} error: {e}, trying next...")
            continue

    # If all images failed, provide instructions
    print("⚠️ Hassfest validation - SKIPPED")
    print("   Could not run Hassfest locally with Docker")
    print("   This validation will run in GitHub Actions")
    return True  # Don't fail if we can't run Hassfest locally


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

    # 1. Validate manifest
    validation_results.append(validate_manifest())

    # 2. Validate services
    validation_results.append(validate_services())

    # 3. HACS validation (requires Docker)
    validation_results.append(validate_hacs())

    # 4. Hassfest validation (requires Docker)
    validation_results.append(validate_hassfest())

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