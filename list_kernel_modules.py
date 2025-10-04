#!/usr/bin/env python3
"""
Kernel Module Lister

This script parses /proc/modules to list all currently loaded kernel modules.
It provides detailed information about each module including name, size, 
reference count, dependencies, and status.
"""

import os
import sys
from typing import List, Dict, Optional


class KernelModule:
    """Represents a loaded kernel module with its properties."""
    
    def __init__(self, name: str, size: int, ref_count: int, 
                 dependencies: List[str], status: str, address: str):
        self.name = name
        self.size = size
        self.ref_count = ref_count
        self.dependencies = dependencies
        self.status = status
        self.address = address
    
    def __str__(self) -> str:
        deps_str = ", ".join(self.dependencies) if self.dependencies else "None"
        return (f"Module: {self.name}\n"
                f"  Size: {self.size} bytes\n"
                f"  Reference Count: {self.ref_count}\n"
                f"  Dependencies: {deps_str}\n"
                f"  Status: {self.status}\n"
                f"  Address: {self.address}\n")


def parse_proc_modules() -> List[KernelModule]:
    """
    Parse /proc/modules file and return a list of KernelModule objects.
    
    Returns:
        List[KernelModule]: List of loaded kernel modules
        
    Raises:
        FileNotFoundError: If /proc/modules doesn't exist
        PermissionError: If unable to read /proc/modules
    """
    modules = []
    
    try:
        with open('/proc/modules', 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                # Parse the line format:
                # module_name size ref_count dependencies status address
                parts = line.split()
                if len(parts) < 6:
                    continue
                
                name = parts[0]
                size = int(parts[1])
                ref_count = int(parts[2])
                
                # Dependencies are comma-separated, empty if none
                deps_str = parts[3]
                if deps_str == '-':
                    dependencies = []
                else:
                    # Split by comma and filter out status markers like [permanent]
                    deps = deps_str.split(',')
                    dependencies = [dep.strip() for dep in deps if dep.strip() and not dep.strip().startswith('[')]
                
                status = parts[4]
                address = parts[5]
                
                module = KernelModule(name, size, ref_count, dependencies, status, address)
                modules.append(module)
                
    except FileNotFoundError:
        print("Error: /proc/modules not found. Are you running on a Linux system?", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print("Error: Permission denied reading /proc/modules", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing /proc/modules: {e}", file=sys.stderr)
        sys.exit(1)
    
    return modules


def format_size(size_bytes: int) -> str:
    """Convert bytes to human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def display_modules(modules: List[KernelModule], show_details: bool = False):
    """
    Display the loaded kernel modules.
    
    Args:
        modules: List of KernelModule objects
        show_details: If True, show detailed information for each module
    """
    print(f"Loaded Kernel Modules ({len(modules)} total)\n")
    print("=" * 60)
    
    if not show_details:
        # Simple table format
        print(f"{'Module Name':<25} {'Size':<10} {'Ref Count':<10} {'Status':<10}")
        print("-" * 60)
        
        for module in sorted(modules, key=lambda x: x.name):
            size_str = format_size(module.size)
            print(f"{module.name:<25} {size_str:<10} {module.ref_count:<10} {module.status:<10}")
    else:
        # Detailed format
        for i, module in enumerate(sorted(modules, key=lambda x: x.name), 1):
            print(f"{i}. {module}")


def main():
    """Main function to run the kernel module lister."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="List all loaded kernel modules by parsing /proc/modules",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 list_kernel_modules.py              # Simple list
  python3 list_kernel_modules.py --detailed  # Detailed information
  python3 list_kernel_modules.py --count     # Show only count
        """
    )
    
    parser.add_argument('--detailed', '-d', action='store_true',
                       help='Show detailed information for each module')
    parser.add_argument('--count', '-c', action='store_true',
                       help='Show only the count of loaded modules')
    
    args = parser.parse_args()
    
    try:
        modules = parse_proc_modules()
        
        if args.count:
            print(f"Total loaded kernel modules: {len(modules)}")
        else:
            display_modules(modules, args.detailed)
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
