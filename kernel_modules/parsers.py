"""
Parsers for kernel module information.

This module contains classes for parsing different sources of kernel module
information including /proc/modules, modules.builtin, and modinfo output.
"""

import os
import sys
import subprocess
import re
from typing import List, Set, Optional
from .models import KernelModule, BuiltinModule


class ModuleParser:
    """Parser for loadable kernel modules from /proc/modules."""
    
    @staticmethod
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
            raise FileNotFoundError("/proc/modules not found. Are you running on a Linux system?")
        except PermissionError:
            raise PermissionError("Permission denied reading /proc/modules")
        except Exception as e:
            raise Exception(f"Error parsing /proc/modules: {e}")
        
        return modules


class BuiltinModuleParser:
    """Parser for builtin kernel modules from various sources."""
    
    @staticmethod
    def get_loadable_module_names() -> Set[str]:
        """
        Get names of currently loaded modules from /proc/modules.
        
        Returns:
            Set[str]: Set of currently loaded module names
        """
        loadable_modules = set()
        
        try:
            with open('/proc/modules', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        module_name = line.split()[0]
                        loadable_modules.add(module_name)
        except Exception:
            pass
        
        return loadable_modules
    
    @staticmethod
    def get_builtin_modules_from_modules_builtin() -> Set[str]:
        """
        Extract builtin module names from /lib/modules/{version}/modules.builtin.
        
        This is the authoritative source for builtin modules as per kernel documentation:
        https://www.kernel.org/doc/html/latest/kbuild/kbuild.html#modules-builtin
        
        Returns:
            Set[str]: Set of builtin module names from modules.builtin file
        """
        builtin_modules = set()
        
        try:
            kernel_version = os.uname().release
            modules_builtin_path = f'/lib/modules/{kernel_version}/modules.builtin'
            
            if os.path.exists(modules_builtin_path):
                with open(modules_builtin_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            # Extract module name from path like "kernel/fs/ext4/ext4.ko"
                            module_name = os.path.basename(line).replace('.ko', '')
                            builtin_modules.add(module_name)
            else:
                print(f"Warning: {modules_builtin_path} not found", file=sys.stderr)
                
        except Exception as e:
            print(f"Warning: Error reading modules.builtin: {e}", file=sys.stderr)
        
        return builtin_modules
    
    @staticmethod
    def get_builtin_modules_from_modinfo() -> List[BuiltinModule]:
        """
        Get builtin module information using modinfo command.
        
        Returns:
            List[BuiltinModule]: List of builtin modules with metadata
        """
        builtin_modules = []
        
        try:
            # Get list of all available modules (including builtin)
            result = subprocess.run(['modinfo', '-a'], capture_output=True, text=True, check=True)
            
            # Parse modinfo output to find builtin modules
            current_module = None
            module_info = {}
            
            for line in result.stdout.split('\n'):
                if line.startswith('filename:'):
                    # Extract module name from filename
                    filename = line.split(':', 1)[1].strip()
                    if filename == '(builtin)':
                        # This is a builtin module
                        if current_module:
                            builtin_modules.append(BuiltinModule(
                                name=current_module,
                                description=module_info.get('description', ''),
                                version=module_info.get('version', ''),
                                author=module_info.get('author', ''),
                                license=module_info.get('license', '')
                            ))
                        current_module = None
                        module_info = {}
                    elif filename.endswith('.ko'):
                        # This is a loadable module, skip
                        current_module = None
                        module_info = {}
                    else:
                        # This might be a builtin module
                        current_module = filename.split('/')[-1] if '/' in filename else filename
                elif current_module and ':' in line:
                    key, value = line.split(':', 1)
                    module_info[key.strip()] = value.strip()
                    
        except subprocess.CalledProcessError:
            # modinfo might not be available or might fail
            pass
        except FileNotFoundError:
            # modinfo command not found
            pass
        except Exception as e:
            print(f"Warning: Error running modinfo: {e}", file=sys.stderr)
        
        return builtin_modules
    
    @staticmethod
    def get_builtin_modules_from_config() -> Set[str]:
        """
        Extract builtin module names from kernel configuration files.
        
        This is a fallback method. The primary method should be modules.builtin.
        
        Returns:
            Set[str]: Set of builtin module names from config
        """
        builtin_modules = set()
        
        # Try different config file locations
        config_paths = [
            '/proc/config.gz',
            f'/boot/config-{os.uname().release}',
            '/boot/config'
        ]
        
        for config_path in config_paths:
            if os.path.exists(config_path):
                try:
                    if config_path.endswith('.gz'):
                        import gzip
                        with gzip.open(config_path, 'rt') as f:
                            content = f.read()
                    else:
                        with open(config_path, 'r') as f:
                            content = f.read()
                    
                    # Look for CONFIG_*_BUILTIN=y patterns
                    for line in content.split('\n'):
                        if '=y' in line and 'CONFIG_' in line and 'BUILTIN' in line:
                            # Extract module name from CONFIG_MODULE_NAME_BUILTIN=y
                            match = re.search(r'CONFIG_([A-Z0-9_]+)_BUILTIN=y', line)
                            if match:
                                module_name = match.group(1).lower().replace('_', '')
                                builtin_modules.add(module_name)
                                
                except Exception as e:
                    print(f"Warning: Error reading {config_path}: {e}", file=sys.stderr)
        
        return builtin_modules
    
    @classmethod
    def get_all_builtin_modules(cls) -> List[BuiltinModule]:
        """
        Get all builtin modules using the authoritative kernel files.
        
        Uses /lib/modules/{version}/modules.builtin as the primary source,
        as specified in the kernel documentation:
        https://www.kernel.org/doc/html/latest/kbuild/kbuild.html#modules-builtin
        
        Returns:
            List[BuiltinModule]: List of all detected builtin modules
        """
        builtin_modules = []
        module_names = set()
        
        # Get currently loaded modules to exclude them from builtin detection
        loadable_modules = cls.get_loadable_module_names()
        
        # Primary method: Use modules.builtin file (authoritative source)
        modules_builtin = cls.get_builtin_modules_from_modules_builtin()
        module_names.update(modules_builtin)
        
        # Fallback methods (only if modules.builtin is not available)
        if not module_names:
            print("Warning: modules.builtin not found, using fallback methods", file=sys.stderr)
            config_modules = cls.get_builtin_modules_from_config()
            modinfo_modules = cls.get_builtin_modules_from_modinfo()
            
            # Combine fallback module names
            module_names.update(config_modules)
            module_names.update(module.name for module in modinfo_modules)
            
            # Remove loadable modules from builtin detection to avoid false positives
            module_names = module_names - loadable_modules
        
        # Get detailed module info from modinfo for builtin modules
        modinfo_modules = cls.get_builtin_modules_from_modinfo()
        modinfo_names = {module.name for module in modinfo_modules}
        
        # Create BuiltinModule objects
        for name in module_names:
            # Check if we have detailed info from modinfo
            existing_module = next((m for m in modinfo_modules if m.name == name), None)
            if existing_module:
                builtin_modules.append(existing_module)
            else:
                builtin_modules.append(BuiltinModule(name=name))
        
        return builtin_modules
