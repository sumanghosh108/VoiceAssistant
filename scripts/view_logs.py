"""
Simple log viewer utility.

This script helps you view and filter the JSON logs in a readable format.
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def view_logs(log_file: str, filter_level: str = None, filter_session: str = None, 
              filter_component: str = None, limit: int = None):
    """
    View logs with optional filtering.
    
    Args:
        log_file: Path to log file
        filter_level: Filter by log level (info, warning, error)
        filter_session: Filter by session_id
        filter_component: Filter by component
        limit: Limit number of entries to show
    """
    log_path = Path(log_file)
    
    if not log_path.exists():
        print(f"❌ Log file not found: {log_file}")
        return
    
    print(f"\n📁 Reading log file: {log_file}")
    print("=" * 80)
    
    with open(log_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    count = 0
    displayed = 0
    
    for line in lines:
        if not line.strip():
            continue
            
        try:
            log_entry = json.loads(line.strip())
            count += 1
            
            # Apply filters
            if filter_level and log_entry.get('level') != filter_level:
                continue
            
            if filter_session and log_entry.get('session_id') != filter_session:
                continue
            
            if filter_component and log_entry.get('component') != filter_component:
                continue
            
            # Display log entry
            timestamp = log_entry.get('timestamp', 'N/A')
            level = log_entry.get('level', 'N/A').upper()
            event = log_entry.get('event', 'N/A')
            
            # Color code by level
            level_colors = {
                'INFO': '\033[92m',      # Green
                'WARNING': '\033[93m',   # Yellow
                'ERROR': '\033[91m',     # Red
                'DEBUG': '\033[94m'      # Blue
            }
            color = level_colors.get(level, '\033[0m')
            reset = '\033[0m'
            
            print(f"\n{color}[{level}]{reset} {timestamp}")
            print(f"  📝 {event}")
            
            # Show additional fields
            exclude_keys = {'timestamp', 'level', 'event', 'log_file', 'log_level'}
            extra_fields = {k: v for k, v in log_entry.items() if k not in exclude_keys}
            
            if extra_fields:
                for key, value in extra_fields.items():
                    if key == 'exception':
                        print(f"  ⚠️  {key}: [See full traceback below]")
                    else:
                        print(f"  • {key}: {value}")
            
            # Show exception if present
            if 'exception' in log_entry:
                print(f"\n  {color}Exception Traceback:{reset}")
                for line in log_entry['exception'].split('\n'):
                    print(f"    {line}")
            
            displayed += 1
            
            # Check limit
            if limit and displayed >= limit:
                break
                
        except json.JSONDecodeError as e:
            print(f"⚠️  Failed to parse line: {e}")
    
    print("\n" + "=" * 80)
    print(f"📊 Total entries: {count} | Displayed: {displayed}")
    
    if filter_level or filter_session or filter_component:
        print(f"🔍 Filters applied:")
        if filter_level:
            print(f"   - Level: {filter_level}")
        if filter_session:
            print(f"   - Session: {filter_session}")
        if filter_component:
            print(f"   - Component: {filter_component}")
    
    print()


def list_log_files():
    """List all available log files."""
    logs_dir = Path("logs")
    
    if not logs_dir.exists():
        print("❌ No logs directory found")
        return
    
    log_files = sorted(logs_dir.glob("voice_assistant_*.log"), reverse=True)
    
    if not log_files:
        print("❌ No log files found")
        return
    
    print("\n📁 Available log files:")
    print("=" * 80)
    
    for i, log_file in enumerate(log_files, 1):
        size = log_file.stat().st_size
        modified = datetime.fromtimestamp(log_file.stat().st_mtime)
        print(f"{i}. {log_file.name}")
        print(f"   Size: {size:,} bytes | Modified: {modified.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print()


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("\n📖 Log Viewer Usage:")
        print("=" * 80)
        print("\nList all log files:")
        print("  python view_logs.py list")
        print("\nView latest log:")
        print("  python view_logs.py latest")
        print("\nView specific log file:")
        print("  python view_logs.py <log_file>")
        print("\nView with filters:")
        print("  python view_logs.py <log_file> --level error")
        print("  python view_logs.py <log_file> --session session-123")
        print("  python view_logs.py <log_file> --component asr")
        print("  python view_logs.py <log_file> --limit 10")
        print("\nCombine filters:")
        print("  python view_logs.py latest --level error --limit 5")
        print()
        return
    
    command = sys.argv[1]
    
    if command == "list":
        list_log_files()
        return
    
    # Get log file
    if command == "latest":
        logs_dir = Path("logs")
        log_files = sorted(logs_dir.glob("voice_assistant_*.log"), reverse=True)
        if not log_files:
            print("❌ No log files found")
            return
        log_file = str(log_files[0])
    else:
        log_file = command
    
    # Parse filters
    filter_level = None
    filter_session = None
    filter_component = None
    limit = None
    
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--level" and i + 1 < len(sys.argv):
            filter_level = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--session" and i + 1 < len(sys.argv):
            filter_session = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--component" and i + 1 < len(sys.argv):
            filter_component = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--limit" and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])
            i += 2
        else:
            i += 1
    
    view_logs(log_file, filter_level, filter_session, filter_component, limit)


if __name__ == "__main__":
    main()
