#!/usr/bin/env python3
"""
Script to update test imports after restructuring test directory.
"""

import os
import re
from pathlib import Path

# Import mapping for test fixtures
IMPORT_MAPPINGS = {
    'from tests.fixtures import': 'from tests.fixtures.mocks import',
    'import tests.fixtures': 'import tests.fixtures.mocks',
}


def update_file_imports(filepath: Path) -> bool:
    """Update imports in a single file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply each mapping
        for old_import, new_import in IMPORT_MAPPINGS.items():
            content = content.replace(old_import, new_import)
        
        # If content changed, write it back
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False


def main():
    """Update all Python test files."""
    root_dir = Path(__file__).parent
    test_dir = root_dir / 'tests'
    
    if not test_dir.exists():
        print(f"Test directory not found: {test_dir}")
        return
    
    updated_files = []
    
    # Find all Python test files
    for filepath in test_dir.rglob('*.py'):
        if filepath.name.startswith('test_') or filepath.name == 'conftest.py':
            if update_file_imports(filepath):
                updated_files.append(filepath)
                print(f"✓ Updated: {filepath.relative_to(root_dir)}")
    
    print(f"\n{'='*60}")
    print(f"Updated {len(updated_files)} test files")
    print(f"{'='*60}")
    
    if updated_files:
        print("\nUpdated files:")
        for filepath in updated_files:
            print(f"  - {filepath.relative_to(root_dir)}")


if __name__ == '__main__':
    main()
