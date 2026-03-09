#!/usr/bin/env python3
"""
Script to update imports after restructuring to production-ready module organization.
"""

import os
import re
from pathlib import Path

# Import mapping: old_import -> new_import
IMPORT_MAPPINGS = {
    # Events
    'from src.events import': 'from src.core.events import',
    
    # Models
    'from src.buffers import': 'from src.core.models import',
    'from src.session import Session': 'from src.core.models import Session',
    'from src.session import SessionManager': 'from src.session.manager import SessionManager',
    
    # Services
    'from src.asr_service import': 'from src.services.asr import',
    'from src.reasoning_service import': 'from src.services.llm import',
    'from src.tts_service import': 'from src.services.tts import',
    
    # Infrastructure
    'from src.config import': 'from src.infrastructure.config import',
    'from src.logger import': 'from src.utils.logger import',
    'from src.resilience import': 'from src.infrastructure.resilience import',
    
    # Observability
    'from src.health import SystemHealth': 'from src.observability.health import SystemHealth',
    'from src.health import HealthCheckServer': 'from src.api.health_server import HealthCheckServer',
    'from src.latency import': 'from src.observability.latency import',
    'from src.metrics_dashboard import': 'from src.observability.metrics import',
    
    # Session
    'from src.session_recorder import': 'from src.session.recorder import',
    'from src.replay_system import': 'from src.session.replay import',
    
    # API
    'from src.websocket_server import': 'from src.api.websocket import',
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
    """Update all Python files in src/ and tests/ directories."""
    root_dir = Path(__file__).parent
    
    # Directories to process
    directories = [
        root_dir / 'src',
        root_dir / 'tests',
    ]
    
    updated_files = []
    
    for directory in directories:
        if not directory.exists():
            continue
            
        # Find all Python files
        for filepath in directory.rglob('*.py'):
            if update_file_imports(filepath):
                updated_files.append(filepath)
                print(f"✓ Updated: {filepath.relative_to(root_dir)}")
    
    print(f"\n{'='*60}")
    print(f"Updated {len(updated_files)} files")
    print(f"{'='*60}")
    
    if updated_files:
        print("\nUpdated files:")
        for filepath in updated_files:
            print(f"  - {filepath.relative_to(root_dir)}")


if __name__ == '__main__':
    main()
