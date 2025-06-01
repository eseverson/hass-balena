#!/usr/bin/env python3
"""Script to help set up GitHub repository for HACS validation."""

import json
import subprocess
import sys
from pathlib import Path


def get_repository_info():
    """Get repository information from git remote."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True
        )
        remote_url = result.stdout.strip()

        # Extract owner/repo from URL
        if "github.com" in remote_url:
            if remote_url.endswith(".git"):
                remote_url = remote_url[:-4]

            if remote_url.startswith("https://github.com/"):
                repo_path = remote_url.replace("https://github.com/", "")
            elif remote_url.startswith("git@github.com:"):
                repo_path = remote_url.replace("git@github.com:", "")
            else:
                print("❌ Unable to parse GitHub URL")
                return None, None

            owner, repo = repo_path.split("/")
            return owner, repo
        else:
            print("❌ Not a GitHub repository")
            return None, None

    except subprocess.CalledProcessError:
        print("❌ Unable to get git remote URL")
        return None, None


def get_integration_info():
    """Get integration information from manifest.json."""
    manifest_path = Path("custom_components/balena_cloud/manifest.json")
    if not manifest_path.exists():
        print("❌ manifest.json not found!")
        return None

    with open(manifest_path) as f:
        manifest = json.load(f)

    return {
        "name": manifest.get("name", ""),
        "domain": manifest.get("domain", ""),
        "version": manifest.get("version", ""),
        "description": f"Home Assistant integration for {manifest.get('name', '')} - Monitor and control your Balena Cloud devices"
    }


def generate_topics():
    """Generate appropriate topics for the repository."""
    return [
        "home-assistant",
        "hacs",
        "custom-component",
        "balena-cloud",
        "balena",
        "iot",
        "device-management",
        "home-automation",
        "integration",
        "raspberry-pi"
    ]


def main():
    """Main function."""
    print("🔧 GitHub Repository Setup for HACS Validation")
    print("=" * 50)

    # Get repository info
    owner, repo = get_repository_info()
    if not owner or not repo:
        sys.exit(1)

    print(f"📁 Repository: {owner}/{repo}")

    # Get integration info
    integration_info = get_integration_info()
    if not integration_info:
        sys.exit(1)

    print(f"🏠 Integration: {integration_info['name']} v{integration_info['version']}")

    # Generate setup instructions
    topics = generate_topics()
    description = integration_info["description"]

    print("\n📋 Required GitHub Repository Setup:")
    print("-" * 40)

    print("\n1. 📝 **Add Repository Description**")
    print(f"   Go to: https://github.com/{owner}/{repo}/settings")
    print(f"   Set description to:")
    print(f"   📄 {description}")

    print("\n2. 🏷️  **Add Repository Topics**")
    print(f"   In the same settings page, add these topics:")
    for topic in topics:
        print(f"   🏷️  {topic}")

    print("\n3. 📖 **Using GitHub CLI (gh)**")
    print("   If you have GitHub CLI installed, you can run:")
    print(f"   gh repo edit {owner}/{repo} --description \"{description}\"")

    topics_str = ",".join(topics)
    print(f"   gh repo edit {owner}/{repo} --add-topic \"{topics_str}\"")

    print("\n4. ✅ **Verify Setup**")
    print(f"   Check your repository: https://github.com/{owner}/{repo}")
    print("   - Description should be visible")
    print("   - Topics should appear as tags below the description")

    print("\n5. 🔄 **Re-run HACS Validation**")
    print("   After making these changes, re-run the GitHub Actions workflow")
    print("   The HACS validation should now pass")

    print("\n📚 **HACS Documentation**")
    print("   - HACS Requirements: https://hacs.xyz/docs/publish/include")
    print("   - Repository Setup: https://hacs.xyz/docs/publish/include#check-repository")

    print("\n⚠️  **Note about Brands Repository**")
    print("   The 'brands' validation failure is normal for new integrations.")
    print("   This will be resolved when the integration is accepted into HACS.")

    print(f"\n🎉 Setup complete! Your integration is ready for HACS submission.")


if __name__ == "__main__":
    main()