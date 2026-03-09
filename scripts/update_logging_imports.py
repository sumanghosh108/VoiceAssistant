"""
Script to update logging imports from infrastructure to utils.logger.

This script updates all imports from:
  from src.utils.logger import ...
to:
  from src.utils.logger import ...
"""

import re
from pathlib import Path


def update_file(file_path: Path) -> bool:
    """
    Update imports in a single file.
    
    Args:
        file_path: Path to the file to update
        
    Returns:
        True if file was modified, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace the import statement
        content = re.sub(
            r'from src\.infrastructure\.logging import',
            'from src.utils.logger import',
            content
        )
        
        # Check if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Update all Python files with logging imports."""
    project_root = Path(__file__).parent
    
    # Find all Python files
    python_files = list(project_root.rglob("*.py"))
    
    # Exclude virtual environment and cache directories
    python_files = [
        f for f in python_files
        if not any(part.startswith('.') or part == '__pycache__' or part == '.venv'
                   for part in f.parts)
    ]
    
    print(f"Found {len(python_files)} Python files to check")
    print("=" * 60)
    
    updated_files = []
    
    for file_path in python_files:
        if update_file(file_path):
            updated_files.append(file_path)
            print(f"✅ Updated: {file_path.relative_to(project_root)}")
    
    print("=" * 60)
    print(f"\nSummary:")
    print(f"  Total files checked: {len(python_files)}")
    print(f"  Files updated: {len(updated_files)}")
    print(f"  Files unchanged: {len(python_files) - len(updated_files)}")
    
    if updated_files:
        print(f"\n✅ Successfully updated {len(updated_files)} files!")
    else:
        print(f"\n✅ No files needed updating!")


if __name__ == "__main__":
    main()
