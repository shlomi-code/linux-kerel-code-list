"""
Filtering and sorting functionality for kernel modules.

This module contains classes for filtering and sorting kernel module
collections based on various criteria.
"""

import fnmatch
from typing import List, Optional, Union
from .models import KernelModule, BuiltinModule


class ModuleFilter:
    """Filter modules based on various criteria."""
    
    @staticmethod
    def filter_modules(modules: List[Union[KernelModule, BuiltinModule]], 
                      name_pattern: Optional[str] = None,
                      min_size: Optional[int] = None,
                      max_size: Optional[int] = None,
                      min_refs: Optional[int] = None,
                      status: Optional[str] = None) -> List[Union[KernelModule, BuiltinModule]]:
        """
        Filter modules based on various criteria.
        
        Args:
            modules: List of modules to filter
            name_pattern: Wildcard pattern for module names
            min_size: Minimum size in bytes
            max_size: Maximum size in bytes
            min_refs: Minimum reference count
            status: Module status to filter by
            
        Returns:
            List of filtered modules
        """
        filtered = []
        
        for module in modules:
            # Name pattern filtering
            if name_pattern and not fnmatch.fnmatch(module.name, name_pattern):
                continue
                
            # Size filtering (only for KernelModule)
            if isinstance(module, KernelModule):
                if min_size is not None and module.size < min_size:
                    continue
                if max_size is not None and module.size > max_size:
                    continue
                    
                # Reference count filtering
                if min_refs is not None and module.ref_count < min_refs:
                    continue
                    
                # Status filtering
                if status and module.status != status:
                    continue
            
            filtered.append(module)
        
        return filtered


class ModuleSorter:
    """Sort modules by specified field."""
    
    @staticmethod
    def sort_modules(modules: List[Union[KernelModule, BuiltinModule]], 
                    sort_by: str = 'name', reverse: bool = False) -> List[Union[KernelModule, BuiltinModule]]:
        """
        Sort modules by specified field.
        
        Args:
            modules: List of modules to sort
            sort_by: Field to sort by ('name', 'size', 'refs', 'status')
            reverse: Reverse sort order
            
        Returns:
            Sorted list of modules
        """
        def sort_key(module):
            if sort_by == 'name':
                return module.name.lower()
            elif sort_by == 'size' and isinstance(module, KernelModule):
                return module.size
            elif sort_by == 'refs' and isinstance(module, KernelModule):
                return module.ref_count
            elif sort_by == 'status' and isinstance(module, KernelModule):
                return module.status
            else:
                return module.name.lower()
        
        return sorted(modules, key=sort_key, reverse=reverse)


class ModuleDisplay:
    """Display modules in various formats."""
    
    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Convert bytes to human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    @staticmethod
    def display_modules(modules: List[KernelModule], builtin_modules: List[BuiltinModule] = None, 
                       show_details: bool = False, show_builtin: bool = False, quiet: bool = False):
        """
        Display the loaded kernel modules and optionally builtin modules.
        
        Args:
            modules: List of KernelModule objects (loadable modules)
            builtin_modules: List of BuiltinModule objects (builtin modules)
            show_details: If True, show detailed information for each module
            show_builtin: If True, include builtin modules in the output
            quiet: If True, suppress headers and only show module data
        """
        total_modules = len(modules)
        if show_builtin and builtin_modules:
            total_modules += len(builtin_modules)
        
        if not quiet:
            print(f"Kernel Modules ({total_modules} total)\n")
            print("=" * 60)
        
        if not show_details:
            # Simple table format
            if not quiet:
                print(f"| {'Module Name':<25} | {'Type':<10} | {'Size':<10} | {'Ref Count':<10} | {'Status':<10} | {'Description':<50} |")
                print("|" + "-" * 28 + "|" + "-" * 12 + "|" + "-" * 12 + "|" + "-" * 12 + "|" + "-" * 12 + "|" + "-" * 52 + "|")
            
            # Display loadable modules
            for module in modules:
                size_str = ModuleDisplay.format_size(module.size)
                description = module.description or 'N/A'
                print(f"| {module.name:<25} | {'Loadable':<10} | {size_str:<10} | {module.ref_count:<10} | {module.status:<10} | {description:<50} |")
            
            # Display builtin modules if requested
            if show_builtin and builtin_modules:
                for module in builtin_modules:
                    print(f"| {module.name:<25} | {'Builtin':<10} | {'N/A':<10} | {'N/A':<10} | {'Always':<10} | {module.description or 'N/A':<50} |")
        else:
            # Detailed format
            if not quiet:
                print("Loadable Kernel Modules:")
                print("-" * 30)
            for i, module in enumerate(modules, 1):
                print(f"{i}. {module}")
            
            if show_builtin and builtin_modules:
                if not quiet:
                    print(f"\nBuiltin Kernel Modules ({len(builtin_modules)} total):")
                    print("-" * 30)
                for i, module in enumerate(builtin_modules, 1):
                    print(f"{i}. {module}")
