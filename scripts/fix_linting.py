#!/usr/bin/env python3
"""Script to fix flake8 linting issues."""

import re
from pathlib import Path


def remove_unused_imports(content):
    """Remove unused imports from content."""
    # Remove unused imports
    lines = content.split('\n')
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('from ') and 'import' in line:
            # Check if this import is used in the file
            import_name = line.split('import')[-1].strip()
            if import_name not in content[i+1:]:
                # Skip this line as it's unused
                i += 1
                continue
        elif line.startswith('import ') and ' as ' not in line:
            # Check if this import is used in the file
            import_name = line.split('import')[-1].strip()
            if import_name not in content[i+1:]:
                # Skip this line as it's unused
                i += 1
                continue
        new_lines.append(line)
        i += 1
    return '\n'.join(new_lines)


def remove_unused_variables(content):
    """Remove unused variables from content."""
    # Remove unused variables
    lines = content.split('\n')
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if '=' in line and not line.strip().startswith('#'):
            # Check if this variable is used in the file
            var_name = line.split('=')[0].strip()
            if var_name not in content[i+1:]:
                # Skip this line as it's unused
                i += 1
                continue
        new_lines.append(line)
        i += 1
    return '\n'.join(new_lines)


def fix_file(file_path):
    """Fix linting issues in a file."""
    with open(file_path) as f:
        content = f.read()

    # Fix imports
    content = remove_unused_imports(content)

    # Fix variables
    content = remove_unused_variables(content)

    # Write back to file
    with open(file_path, 'w') as f:
        f.write(content)


def main():
    """Main function."""
    # Get all Python files in custom_components
    python_files = Path('custom_components').rglob('*.py')
    for file_path in python_files:
        print(f"Fixing {file_path}...")
        fix_file(file_path)


if __name__ == '__main__':
    main()