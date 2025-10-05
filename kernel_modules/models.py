"""
Data models for kernel modules.

This module contains the core data structures used to represent
kernel modules and their properties.
"""

from typing import List


class KernelModule:
    """Represents a loaded kernel module with its properties."""
    
    def __init__(self, name: str, size: int, ref_count: int, 
                 dependencies: List[str], status: str, address: str, 
                 module_type: str = "loadable", file_path: str = ""):
        """
        Initialize a KernelModule instance.
        
        Args:
            name: Module name
            size: Module size in bytes
            ref_count: Reference count
            dependencies: List of module dependencies
            status: Module status (Live, Dead, Unloading)
            address: Memory address
            module_type: Type of module (loadable or builtin)
            file_path: Full path to the module file (.ko file)
        """
        self.name = name
        self.size = size
        self.ref_count = ref_count
        self.dependencies = dependencies
        self.status = status
        self.address = address
        self.module_type = module_type
        self.file_path = file_path
    
    def __str__(self) -> str:
        """Return string representation of the module."""
        deps_str = ", ".join(self.dependencies) if self.dependencies else "None"
        file_path_str = self.file_path if self.file_path else "N/A"
        return (f"Module: {self.name} ({self.module_type})\n"
                f"  Size: {self.size} bytes\n"
                f"  Reference Count: {self.ref_count}\n"
                f"  Dependencies: {deps_str}\n"
                f"  Status: {self.status}\n"
                f"  Address: {self.address}\n"
                f"  File Path: {file_path_str}\n")
    
    def __repr__(self) -> str:
        """Return detailed string representation."""
        return (f"KernelModule(name='{self.name}', size={self.size}, "
                f"ref_count={self.ref_count}, status='{self.status}')")
    
    def to_dict(self) -> dict:
        """Convert module to dictionary representation."""
        return {
            'name': self.name,
            'size': self.size,
            'ref_count': self.ref_count,
            'dependencies': self.dependencies,
            'status': self.status,
            'address': self.address,
            'type': self.module_type,
            'file_path': self.file_path
        }


class BuiltinModule:
    """Represents a builtin kernel module."""
    
    def __init__(self, name: str, description: str = "", version: str = "", 
                 author: str = "", license: str = ""):
        """
        Initialize a BuiltinModule instance.
        
        Args:
            name: Module name
            description: Module description
            version: Module version
            author: Module author
            license: Module license
        """
        self.name = name
        self.description = description
        self.version = version
        self.author = author
        self.license = license
        self.module_type = "builtin"
    
    def __str__(self) -> str:
        """Return string representation of the module."""
        return (f"Module: {self.name} (builtin)\n"
                f"  Description: {self.description}\n"
                f"  Version: {self.version}\n"
                f"  Author: {self.author}\n"
                f"  License: {self.license}\n")
    
    def __repr__(self) -> str:
        """Return detailed string representation."""
        return f"BuiltinModule(name='{self.name}')"
    
    def to_dict(self) -> dict:
        """Convert module to dictionary representation."""
        return {
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'author': self.author,
            'license': self.license,
            'type': self.module_type
        }
