#!/usr/bin/env python3
"""
Setup verification script for Real-Time Voice Assistant.

This script checks if your environment is properly configured and ready to run.
"""

import sys
import os
from pathlib import Path


def check_python_version():
    """Check if Python version is 3.11 or higher."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print(f"✓ Python version: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"✗ Python version: {version.major}.{version.minor}.{version.micro}")
        print(f"  Required: Python 3.11 or higher")
        return False


def check_virtual_env():
    """Check if running in a virtual environment."""
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    if in_venv:
        print(f"✓ Virtual environment: Active")
        print(f"  Location: {sys.prefix}")
        return True
    else:
        print(f"✗ Virtual environment: Not active")
        print(f"  Run: .venv\\Scripts\\activate (Windows) or source .venv/bin/activate (Linux/Mac)")
        return False


def check_dependencies():
    """Check if required packages are installed."""
    required_packages = [
        'aiohttp',
        'websockets',
        'structlog',
        'pydantic',
        'pydantic-settings',
        'python-dotenv',
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✓ Package installed: {package}")
        except ImportError:
            print(f"✗ Package missing: {package}")
            missing.append(package)
    
    if missing:
        print(f"\n  Install missing packages: pip install -r requirements.txt")
        return False
    return True


def check_env_file():
    """Check if .env file exists."""
    env_file = Path('.env')
    if env_file.exists():
        print(f"✓ .env file: Found")
        return True
    else:
        print(f"✗ .env file: Not found")
        print(f"  Create it: cp .env.example .env (Linux/Mac) or copy .env.example .env (Windows)")
        return False


def check_api_keys():
    """Check if API keys are configured."""
    from dotenv import load_dotenv
    load_dotenv()
    
    required_keys = [
        'GEMINI_API_KEY',
        'ELEVENLABS_API_KEY',
        'ELEVENLABS_VOICE_ID',
    ]
    
    optional_keys = [
        'WHISPER_API_KEY',  # Now optional - used for Wav2Vec2 model name
    ]
    
    missing = []
    for key in required_keys:
        value = os.getenv(key)
        if value and value != f'your_{key.lower()}_here':
            print(f"✓ API key configured: {key}")
        else:
            print(f"✗ API key missing: {key}")
            missing.append(key)
    
    # Check optional keys
    for key in optional_keys:
        value = os.getenv(key)
        if value and value != f'your_{key.lower()}_here':
            print(f"✓ Optional config: {key} = {value}")
        else:
            print(f"ℹ Optional config: {key} (using default: facebook/wav2vec2-base-960h)")
    
    if missing:
        print(f"\n  Edit .env file and add your API keys")
        return False
    return True


def check_directories():
    """Check if required directories exist."""
    required_dirs = ['logs', 'recordings', 'config', 'src']
    
    all_exist = True
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"✓ Directory exists: {dir_name}/")
        else:
            print(f"✗ Directory missing: {dir_name}/")
            all_exist = False
    
    return all_exist


def check_imports():
    """Check if main application modules can be imported."""
    try:
        from src.infrastructure.config import ConfigLoader
        print(f"✓ Can import: src.infrastructure.config")
    except ImportError as e:
        print(f"✗ Cannot import: src.infrastructure.config")
        print(f"  Error: {e}")
        return False
    
    try:
        from src.utils.logger import logger
        print(f"✓ Can import: src.utils.logger")
    except ImportError as e:
        print(f"✗ Cannot import: src.utils.logger")
        print(f"  Error: {e}")
        return False
    
    try:
        from src.session.manager import SessionManager
        print(f"✓ Can import: src.session.manager")
    except ImportError as e:
        print(f"✗ Cannot import: src.session.manager")
        print(f"  Error: {e}")
        return False
    
    return True


def main():
    """Run all checks."""
    print("=" * 60)
    print("Real-Time Voice Assistant - Setup Verification")
    print("=" * 60)
    print()
    
    checks = [
        ("Python Version", check_python_version),
        ("Virtual Environment", check_virtual_env),
        ("Dependencies", check_dependencies),
        ("Environment File", check_env_file),
        ("API Keys", check_api_keys),
        ("Directories", check_directories),
        ("Module Imports", check_imports),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n{name}:")
        print("-" * 60)
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ Error during check: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 All checks passed! You're ready to run the application.")
        print("\nRun: python -m src.main")
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        print("\nFor help, see:")
        print("  - RUN_INSTRUCTIONS.md (step-by-step guide)")
        print("  - MANUAL_SETUP_GUIDE.md (complete manual)")
        print("  - QUICK_START_MANUAL.md (5-minute setup)")
    
    print()
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
