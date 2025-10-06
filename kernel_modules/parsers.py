"""
Parsers for kernel module information.

This module contains classes for parsing different sources of kernel module
information including /proc/modules, modules.builtin, and modinfo output.
"""

import os
import sys
import subprocess
import re
import zstandard as zstd
import tempfile
from typing import List, Set, Optional
from .models import KernelModule, BuiltinModule

try:
    from elftools.elf.elffile import ELFFile
    ELF_TOOLS_AVAILABLE = True
except ImportError:
    ELF_TOOLS_AVAILABLE = False


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
                    
                    # Get file path and description using modinfo
                    file_path = ModuleParser._get_module_file_path(name)
                    description = ModuleParser._get_module_description(name)
                    module = KernelModule(name, size, ref_count, dependencies, status, address, "loadable", file_path, description)
                    modules.append(module)
                    
        except FileNotFoundError:
            raise FileNotFoundError("/proc/modules not found. Are you running on a Linux system?")
        except PermissionError:
            raise PermissionError("Permission denied reading /proc/modules")
        except Exception as e:
            raise Exception(f"Error parsing /proc/modules: {e}")
        
        return modules
    
    @staticmethod
    def _get_module_file_path(module_name: str) -> str:
        """
        Get the full file path of a kernel module using modinfo.
        
        Args:
            module_name: Name of the module
            
        Returns:
            str: Full path to the module file, or empty string if not found
        """
        try:
            result = subprocess.run(['modinfo', '-n', module_name], 
                                  capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            # modinfo might not be available or module might not have a file
            return ""
    
    @staticmethod
    def _get_module_description(module_name: str) -> str:
        """
        Get the description of a kernel module by parsing the ELF file.
        
        Args:
            module_name: Name of the module
            
        Returns:
            str: Module description, or empty string if not found
        """
        # First try to get the file path
        file_path = ModuleParser._get_module_file_path(module_name)
        if not file_path:
            return ""
        
        # Try ELF parsing first if available
        if ELF_TOOLS_AVAILABLE:
            description = ModuleParser._extract_description_from_elf(file_path)
            if description:
                return description
        
        # Fallback to modinfo if ELF parsing fails or is not available
        try:
            result = subprocess.run(['modinfo', '-F', 'description', module_name], 
                                  capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ""
    
    @staticmethod
    def _extract_description_from_elf(file_path: str) -> str:
        """
        Extract module description from ELF file by parsing the .modinfo section.
        
        Args:
            file_path: Path to the kernel module file
            
        Returns:
            str: Module description, or empty string if not found
        """
        try:
            # Handle compressed modules
            if file_path.endswith('.ko.zst'):
                return ModuleParser._extract_from_compressed_elf(file_path)
            else:
                return ModuleParser._extract_from_elf_file(file_path)
        except Exception as e:
            print(f"Warning: Error parsing ELF file {file_path}: {e}", file=sys.stderr)
            return ""
    
    @staticmethod
    def _extract_from_elf_file(file_path: str) -> str:
        """
        Extract description from uncompressed ELF file.
        
        Args:
            file_path: Path to the .ko file
            
        Returns:
            str: Module description, or empty string if not found
        """
        try:
            with open(file_path, 'rb') as f:
                elf = ELFFile(f)
                modinfo_section = elf.get_section_by_name('.modinfo')
                if not modinfo_section:
                    return ""
                
                modinfo_data = modinfo_section.data()
                modinfo_strings = modinfo_data.split(b'\x00')
                
                for entry in modinfo_strings:
                    if entry.startswith(b'description='):
                        return entry.split(b'=', 1)[1].decode('utf-8', errors='ignore')
                
                return ""
        except Exception as e:
            print(f"Warning: Error reading ELF file {file_path}: {e}", file=sys.stderr)
            return ""
    
    @staticmethod
    def _extract_from_compressed_elf(file_path: str) -> str:
        """
        Extract description from compressed .ko.zst file.
        
        Args:
            file_path: Path to the .ko.zst file
            
        Returns:
            str: Module description, or empty string if not found
        """
        try:
            # Decompress the file to a temporary location
            with tempfile.NamedTemporaryFile(suffix='.ko', delete=False) as temp_file:
                temp_path = temp_file.name
                
                # Decompress using zstandard
                with open(file_path, 'rb') as compressed_file:
                    dctx = zstd.ZstdDecompressor()
                    with dctx.stream_reader(compressed_file) as reader:
                        temp_file.write(reader.read())
                
                # Extract description from decompressed file
                description = ModuleParser._extract_from_elf_file(temp_path)
                
                # Clean up temporary file
                os.unlink(temp_path)
                
                return description
        except Exception as e:
            print(f"Warning: Error decompressing {file_path}: {e}", file=sys.stderr)
            return ""


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
