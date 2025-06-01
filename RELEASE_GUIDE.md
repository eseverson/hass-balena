# Release Guide

This guide explains how to prepare and publish releases for the Balena Cloud Home Assistant integration.

## Prerequisites

- Python 3.11+
- Git configured with appropriate permissions
- Access to the GitHub repository
- All tests passing locally

## Release Process

### 1. Prepare the Release

Use the automated release preparation script:

```bash
python scripts/prepare_release.py 1.0.0
```

This script will:
- ✅ Validate the version format
- ✅ Run the complete test suite
- ✅ Update the version in `manifest.json`
- ✅ Generate a changelog entry template
- ✅ Create and optionally push a git tag

### 2. Manual Steps

After running the script:

1. **Edit the Changelog**
   ```bash
   # Edit CHANGELOG.md to add specific changes for this release
   nano CHANGELOG.md
   ```

2. **Commit Changes**
   ```bash
   git add .
   git commit -m "Prepare release v1.0.0"
   git push
   ```

3. **Create GitHub Release**
   - Go to https://github.com/eseverson/hass-balena/releases/new
   - Select the tag `v1.0.0`
   - Use the changelog content for release notes
   - Publish the release

### 3. Automated Actions

When you publish the GitHub release, the following happens automatically:

1. **Release Workflow Triggers**
   - Validates the integration
   - Creates `balena_cloud.zip` archive
   - Uploads the archive as a release asset
   - Updates release notes with installation instructions

2. **HACS Integration**
   - HACS detects the new release automatically
   - Users can update via HACS interface

## Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.x.x): Breaking changes
- **MINOR** (x.1.x): New features, backward compatible
- **PATCH** (x.x.1): Bug fixes, backward compatible

### Examples

- `1.0.0` - Initial release
- `1.1.0` - Added new device monitoring features
- `1.1.1` - Fixed authentication bug
- `2.0.0` - Breaking change: Removed deprecated API methods

## Release Checklist

### Pre-Release
- [ ] All tests pass locally
- [ ] Code reviewed and approved
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version incremented appropriately
- [ ] No breaking changes without major version bump

### Release
- [ ] Git tag created and pushed
- [ ] GitHub release published
- [ ] Release notes are clear and helpful
- [ ] Installation instructions are correct

### Post-Release
- [ ] HACS integration confirmed working
- [ ] Monitor for issues in first 24 hours
- [ ] Respond to user feedback
- [ ] Update project boards/milestones

## Testing Releases

### Local Testing
```bash
# Run all tests
cd tests
python test_runner.py

# Test specific integration loading
python -c "
import sys
sys.path.insert(0, 'custom_components')
from balena_cloud import async_setup_entry
print('✅ Integration loads successfully')
"
```

### HACS Testing
1. Install via HACS in a test Home Assistant instance
2. Verify all entities are created correctly
3. Test device control functions
4. Check logs for errors

### GitHub Actions Testing
All releases are automatically validated by:
- HACS validation
- Home Assistant Hassfest validation
- Code quality checks (Black, isort, flake8)
- Security scanning
- Integration tests

## Release Schedule

- **Major releases**: Quarterly (Q1, Q2, Q3, Q4)
- **Minor releases**: Monthly or as needed for new features
- **Patch releases**: As needed for bug fixes
- **Security releases**: Immediately when required

## Hotfix Process

For critical bugs requiring immediate release:

1. Create hotfix branch from main
2. Make minimal fix
3. Fast-track testing
4. Release with patch version bump
5. Merge back to develop branch

```bash
git checkout main
git checkout -b hotfix/1.0.1
# Make fixes
python scripts/prepare_release.py 1.0.1 --skip-tests
git push origin hotfix/1.0.1
# Create pull request and release
```

## Communication

### Release Announcements
- GitHub release notes (automatic)
- Home Assistant Community forum post
- Discord community notification
- Update project documentation

### Issue Response
- Monitor GitHub issues for 48 hours post-release
- Respond to HACS-related issues quickly
- Provide workarounds for known issues
- Plan patches for critical issues

## Rollback Procedure

If a release causes critical issues:

1. **Immediate**: Update release notes with warnings
2. **Short-term**: Prepare hotfix release
3. **Long-term**: Post-mortem and process improvements

```bash
# Emergency: Hide problematic release
gh release edit v1.0.0 --draft
# Fix issues and re-release
```

## Troubleshooting

### Common Issues

**Version conflicts in manifest.json**
```bash
# Check current version
python -c "
import json
with open('custom_components/balena_cloud/manifest.json') as f:
    print(json.load(f)['version'])
"
```

**Git tag issues**
```bash
# List tags
git tag -l

# Delete local tag
git tag -d v1.0.0

# Delete remote tag
git push origin :refs/tags/v1.0.0
```

**HACS validation failures**
```bash
# Test HACS validation locally
docker run --rm -v $(pwd):/github/workspace ghcr.io/hacs/action:main
```

For more help, see:
- [Home Assistant Integration Development](https://developers.home-assistant.io/)
- [HACS Documentation](https://hacs.xyz/)
- [Semantic Versioning Guide](https://semver.org/)