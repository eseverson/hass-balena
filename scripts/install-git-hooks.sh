#!/bin/bash

# Install git hooks for the Balena Cloud Home Assistant integration
# This script sets up pre-commit hooks to maintain code quality

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🔧 Installing git hooks for Balena Cloud integration..."

# Check if we're in a git repository
if [ ! -d "$PROJECT_ROOT/.git" ]; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

# Create hooks directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/.git/hooks"

# Install pre-commit hook
cat > "$PROJECT_ROOT/.git/hooks/pre-commit" << 'EOF'
#!/bin/bash

# Pre-commit hook to run tests before allowing commit
# This ensures that no broken code gets committed to the repository

set -e

echo "🔍 Running pre-commit checks..."

# Check if we're in the right directory
if [ ! -f "pytest.ini" ]; then
    echo "❌ Error: Not in project root directory (pytest.ini not found)"
    exit 1
fi

# Check if pytest is available
if ! command -v python &> /dev/null; then
    echo "❌ Error: Python not found in PATH"
    exit 1
fi

# Check if pytest module is available
if ! python -c "import pytest" &> /dev/null; then
    echo "❌ Error: pytest module not installed"
    echo "💡 Install with: pip install pytest"
    exit 1
fi

echo "🧪 Running test suite..."

# Run the tests with minimal output unless there are failures
if python -m pytest tests/ --tb=short -q; then
    echo "✅ All tests passed! Proceeding with commit..."
    exit 0
else
    echo ""
    echo "❌ Tests failed! Commit aborted."
    echo ""
    echo "💡 Fix the failing tests before committing:"
    echo "   python -m pytest tests/ -v"
    echo ""
    echo "🚫 Commit blocked to maintain code quality."
    exit 1
fi
EOF

# Make the hook executable
chmod +x "$PROJECT_ROOT/.git/hooks/pre-commit"

echo "✅ Pre-commit hook installed successfully!"
echo ""
echo "📋 What this does:"
echo "   • Runs all tests before every commit"
echo "   • Blocks commits if any tests fail"
echo "   • Maintains 100% test success rate"
echo ""
echo "🎯 Benefits:"
echo "   • Prevents broken code from being committed"
echo "   • Maintains code quality automatically"
echo "   • Catches regressions early"
echo ""
echo "💡 To bypass the hook in emergencies (not recommended):"
echo "   git commit --no-verify -m \"emergency commit\""
echo ""
echo "🚀 Happy coding! Your commits are now protected by tests."