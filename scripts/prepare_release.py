#!/usr/bin/env python3
"""Release preparation script for Balena Cloud Home Assistant integration."""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def get_current_version():
    """Get current version from manifest.json."""
    manifest_path = Path("custom_components/balena_cloud/manifest.json")
    if not manifest_path.exists():
        print("❌ manifest.json not found!")
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    return manifest.get("version", "0.0.0")


def update_version(new_version):
    """Update version in manifest.json."""
    manifest_path = Path("custom_components/balena_cloud/manifest.json")

    with open(manifest_path) as f:
        manifest = json.load(f)

    manifest["version"] = new_version

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    print(f"✅ Updated manifest.json version to {new_version}")


def validate_version_format(version):
    """Validate semantic version format."""
    pattern = r"^\d+\.\d+\.\d+$"
    if not re.match(pattern, version):
        print(f"❌ Invalid version format: {version}")
        print("Version should be in format: MAJOR.MINOR.PATCH (e.g., 1.0.0)")
        return False
    return True


def run_tests():
    """Run the test suite."""
    print("🧪 Running test suite...")
    try:
        result = subprocess.run(
            ["python", "tests/test_runner.py"],
            capture_output=True,
            text=True,
            cwd=Path.cwd()
        )

        if result.returncode == 0:
            print("✅ All tests passed!")
            return True
        else:
            print("❌ Tests failed!")
            print(result.stdout)
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False


def generate_changelog(version):
    """Generate changelog entry template."""
    date = datetime.now().strftime("%Y-%m-%d")

    changelog_entry = f"""
## [{version}] - {date}

### ✨ Added
- New feature descriptions here

### 🔧 Changed
- Changed feature descriptions here

### 🐛 Fixed
- Bug fix descriptions here

### 🗑️ Removed
- Removed feature descriptions here

### ⚠️ Security
- Security fix descriptions here
"""

    changelog_path = Path("CHANGELOG.md")
    if changelog_path.exists():
        with open(changelog_path) as f:
            existing_content = f.read()

        # Insert new entry after the header
        lines = existing_content.split('\n')
        header_end = 0
        for i, line in enumerate(lines):
            if line.startswith('## '):
                header_end = i
                break

        lines.insert(header_end, changelog_entry.strip())

        with open(changelog_path, "w") as f:
            f.write('\n'.join(lines))
    else:
        with open(changelog_path, "w") as f:
            f.write(f"# Changelog\n\nAll notable changes to this project will be documented in this file.\n{changelog_entry}")

    print(f"✅ Generated changelog entry for {version}")
    print(f"📝 Please edit CHANGELOG.md to add specific changes")


def create_git_tag(version):
    """Create and push git tag."""
    tag_name = f"v{version}"

    try:
        # Create tag
        subprocess.run(["git", "tag", "-a", tag_name, "-m", f"Release {version}"], check=True)
        print(f"✅ Created git tag: {tag_name}")

        # Ask to push
        response = input(f"Push tag {tag_name} to origin? (y/N): ")
        if response.lower() == 'y':
            subprocess.run(["git", "push", "origin", tag_name], check=True)
            print(f"✅ Pushed tag {tag_name} to origin")

        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error creating/pushing tag: {e}")
        return False


def validate_integration():
    """Run integration validation checks."""
    print("🔍 Validating integration...")

    # Check manifest.json
    manifest_path = Path("custom_components/balena_cloud/manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)

    required_fields = ["domain", "name", "version", "requirements", "dependencies"]
    for field in required_fields:
        if field not in manifest:
            print(f"❌ Missing required field in manifest.json: {field}")
            return False

    # Check HACS config
    hacs_path = Path("hacs.json")
    if hacs_path.exists():
        with open(hacs_path) as f:
            hacs_config = json.load(f)

        if "balena_cloud" not in hacs_config.get("domains", []):
            print("❌ Domain mismatch in hacs.json")
            return False

    print("✅ Integration validation passed")
    return True


def main():
    """Main release preparation function."""
    parser = argparse.ArgumentParser(description="Prepare a new release")
    parser.add_argument("version", help="New version number (e.g., 1.0.0)")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running tests")
    parser.add_argument("--skip-tag", action="store_true", help="Skip creating git tag")

    args = parser.parse_args()

    # Validate version format
    if not validate_version_format(args.version):
        sys.exit(1)

    current_version = get_current_version()
    print(f"📦 Current version: {current_version}")
    print(f"📦 New version: {args.version}")

    # Confirm with user
    response = input(f"Continue with release preparation for v{args.version}? (y/N): ")
    if response.lower() != 'y':
        print("❌ Release preparation cancelled")
        sys.exit(1)

    # Run validation
    if not validate_integration():
        sys.exit(1)

    # Run tests
    if not args.skip_tests:
        if not run_tests():
            response = input("Tests failed. Continue anyway? (y/N): ")
            if response.lower() != 'y':
                sys.exit(1)

    # Update version
    update_version(args.version)

    # Generate changelog
    generate_changelog(args.version)

    # Create git tag
    if not args.skip_tag:
        create_git_tag(args.version)

    print(f"""
🎉 Release preparation complete!

Next steps:
1. Edit CHANGELOG.md to add specific changes
2. Commit the version changes: git add . && git commit -m "Prepare release v{args.version}"
3. Push changes: git push
4. Create a GitHub release at: https://github.com/eseverson/hass-balena/releases/new
5. Select tag v{args.version} and publish the release

The GitHub Actions will automatically:
- Run validation and tests
- Create the release archive
- Update release notes
""")


if __name__ == "__main__":
    main()