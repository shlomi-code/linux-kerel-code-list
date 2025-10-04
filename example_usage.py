#!/usr/bin/env python3
"""
Example usage of the kernel_modules package.

This script demonstrates how to use the modular kernel_modules package
to parse, filter, and format kernel module information.
"""

from kernel_modules import (
    ModuleParser, BuiltinModuleParser,
    JSONFormatter, CSVFormatter, HTMLFormatter,
    ModuleFilter, ModuleSorter, ModuleDisplay
)


def main():
    """Demonstrate the kernel_modules package functionality."""
    
    print("=== Kernel Modules Package Example ===\n")
    
    # 1. Parse loadable modules
    print("1. Parsing loadable modules from /proc/modules...")
    loadable_modules = ModuleParser.parse_proc_modules()
    print(f"   Found {len(loadable_modules)} loadable modules")
    
    # 2. Parse builtin modules
    print("\n2. Parsing builtin modules...")
    builtin_modules = BuiltinModuleParser.get_all_builtin_modules()
    print(f"   Found {len(builtin_modules)} builtin modules")
    
    # 3. Filter modules
    print("\n3. Filtering modules (size >= 50KB)...")
    large_modules = ModuleFilter.filter_modules(
        loadable_modules, 
        min_size=50000
    )
    print(f"   Found {len(large_modules)} modules >= 50KB")
    
    # 4. Sort modules
    print("\n4. Sorting modules by size (largest first)...")
    sorted_modules = ModuleSorter.sort_modules(
        large_modules, 
        sort_by='size', 
        reverse=True
    )
    print("   Top 5 largest modules:")
    for i, module in enumerate(sorted_modules[:5], 1):
        size_str = ModuleDisplay.format_size(module.size)
        print(f"   {i}. {module.name}: {size_str}")
    
    # 5. Filter by name pattern
    print("\n5. Filtering modules by name pattern (snd*)...")
    sound_modules = ModuleFilter.filter_modules(
        loadable_modules,
        name_pattern="snd*"
    )
    print(f"   Found {len(sound_modules)} sound modules")
    
    # 6. Generate different output formats
    print("\n6. Generating output formats...")
    
    # JSON output
    json_formatter = JSONFormatter()
    json_output = json_formatter.format(sound_modules)
    print(f"   JSON output: {len(json_output)} characters")
    
    # CSV output
    csv_formatter = CSVFormatter()
    csv_output = csv_formatter.format(sound_modules)
    print(f"   CSV output: {len(csv_output)} characters")
    
    # HTML output
    html_formatter = HTMLFormatter()
    html_output = html_formatter.format(sound_modules)
    print(f"   HTML output: {len(html_output)} characters")
    
    # Save HTML report
    with open('example_report.html', 'w') as f:
        f.write(html_output)
    print("   Saved example_report.html")
    
    print("\n=== Example completed successfully! ===")


if __name__ == "__main__":
    main()
