#!/usr/bin/env python3
"""
Kernel Module Lister

This script parses /proc/modules to list all currently loaded kernel modules.
It provides detailed information about each module including name, size, 
reference count, dependencies, and status.
"""

import os
import sys
import subprocess
import re
import json
import csv
import fnmatch
import tempfile
import glob
from typing import List, Dict, Optional, Set, Union

try:
    from elftools.elf.elffile import ELFFile
    ELF_TOOLS_AVAILABLE = True
except ImportError:
    ELF_TOOLS_AVAILABLE = False

try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False


class KernelModule:
    """Represents a loaded kernel module with its properties."""
    
    def __init__(self, name: str, size: int, ref_count: int, 
                 dependencies: List[str], status: str, address: str, 
                 module_type: str = "loadable", file_path: str = "", description: str = "",
                 signed: str = ""):
        self.name = name
        self.size = size
        self.ref_count = ref_count
        self.dependencies = dependencies
        self.status = status
        self.address = address
        self.module_type = module_type
        self.file_path = file_path
        self.description = description
        self.signed = signed
    
    def __str__(self) -> str:
        deps_str = ", ".join(self.dependencies) if self.dependencies else "None"
        file_path_str = self.file_path if self.file_path else "N/A"
        description_str = self.description if self.description else "N/A"
        return (f"Module: {self.name} ({self.module_type})\n"
                f"  Size: {self.size} bytes\n"
                f"  Reference Count: {self.ref_count}\n"
                f"  Dependencies: {deps_str}\n"
                f"  Status: {self.status}\n"
                f"  Address: {self.address}\n"
                f"  File Path: {file_path_str}\n"
                f"  Description: {description_str}\n")


class BuiltinModule:
    """Represents a builtin kernel module."""
    
    def __init__(self, name: str, description: str = "", version: str = "", 
                 author: str = "", license: str = ""):
        self.name = name
        self.description = description
        self.version = version
        self.author = author
        self.license = license
        self.module_type = "builtin"
    
    def __str__(self) -> str:
        return (f"Module: {self.name} (builtin)\n"
                f"  Description: {self.description}\n"
                f"  Version: {self.version}\n"
                f"  Author: {self.author}\n"
                f"  License: {self.license}\n")


def get_builtin_modules_from_kallsyms() -> Set[str]:
    """
    Extract builtin module names from /proc/kallsyms.
    
    This method is not reliable for detecting builtin modules as loadable modules
    also appear in kallsyms. This function is kept for completeness but should
    not be used as the primary detection method.
    
    Returns:
        Set[str]: Set of builtin module names found in kallsyms
        
    Raises:
        FileNotFoundError: If /proc/kallsyms doesn't exist
        PermissionError: If unable to read /proc/kallsyms
    """
    # This method is unreliable - loadable modules also appear in kallsyms
    # We'll return an empty set to avoid false positives
    return set()


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


def get_all_builtin_modules() -> List[BuiltinModule]:
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
    loadable_modules = get_loadable_module_names()
    
    # Primary method: Use modules.builtin file (authoritative source)
    modules_builtin = get_builtin_modules_from_modules_builtin()
    module_names.update(modules_builtin)
    
    # Fallback methods (only if modules.builtin is not available)
    if not module_names:
        print("Warning: modules.builtin not found, using fallback methods", file=sys.stderr)
        kallsyms_modules = get_builtin_modules_from_kallsyms()
        config_modules = get_builtin_modules_from_config()
        modinfo_modules = get_builtin_modules_from_modinfo()
        
        # Combine fallback module names
        module_names.update(kallsyms_modules)
        module_names.update(config_modules)
        module_names.update(module.name for module in modinfo_modules)
        
        # Remove loadable modules from builtin detection to avoid false positives
        module_names = module_names - loadable_modules
    
    # Get detailed module info from modinfo for builtin modules
    modinfo_modules = get_builtin_modules_from_modinfo()
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


def get_module_file_path(module_name: str) -> str:
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


def get_module_description(module_name: str) -> str:
    """
    Get the description of a kernel module by parsing the ELF file.
    
    Args:
        module_name: Name of the module
        
    Returns:
        str: Module description, or empty string if not found
    """
    # First try to get the file path
    file_path = get_module_file_path(module_name)
    if not file_path:
        return ""
    
    # Try ELF parsing first if available
    if ELF_TOOLS_AVAILABLE:
        description = extract_description_from_elf(file_path)
        if description:
            return description
    
    # Fallback to modinfo if ELF parsing fails or is not available
    try:
        result = subprocess.run(['modinfo', '-F', 'description', module_name], 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def extract_description_from_elf(file_path: str) -> str:
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
            return extract_from_compressed_elf(file_path)
        else:
            return extract_from_elf_file(file_path)
    except Exception as e:
        print(f"Warning: Error parsing ELF file {file_path}: {e}", file=sys.stderr)
        return ""


def extract_from_elf_file(file_path: str) -> str:
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


def _elf_has_signature_info(file_path: str) -> bool:
    """
    Check for signature-related keys in the ELF .modinfo section.
    Returns True if keys like sig_id/signature/signer are present.
    """
    try:
        with open(file_path, 'rb') as f:
            elf = ELFFile(f)
            modinfo_section = elf.get_section_by_name('.modinfo')
            if not modinfo_section:
                return False
            modinfo_data = modinfo_section.data()
            modinfo_strings = modinfo_data.split(b'\x00')
            for entry in modinfo_strings:
                # Common keys present for signed modules
                if (entry.startswith(b'sig_id=') or
                    entry.startswith(b'signer=') or
                    entry.startswith(b'signature=') or
                    entry.startswith(b'sig_key=') or
                    entry.startswith(b'sig_hashalgo=')):
                    return True
    except Exception:
        return False
    return False


def _file_has_appended_signature_marker(file_path: str) -> bool:
    """
    Check for the textual marker that appears in signed modules:
    "~Module signature appended~" near the end of the file.
    """
    try:
        with open(file_path, 'rb') as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            read_size = min(8192, size)
            f.seek(size - read_size)
            tail = f.read(read_size)
            return b'Module signature appended' in tail
    except Exception:
        return False


def is_module_signed_from_file(file_path: str) -> Optional[bool]:
    """
    Determine whether the module file is signed.
    Tries ELF .modinfo keys and appended signature marker.
    Returns True/False, or None if undetermined.
    """
    if not file_path:
        return None
    try:
        # If compressed, decompress to temp first
        if file_path.endswith('.ko.zst'):
            if not ZSTD_AVAILABLE:
                return None
            with tempfile.NamedTemporaryFile(suffix='.ko', delete=False) as temp_file:
                temp_path = temp_file.name
                try:
                    with open(file_path, 'rb') as compressed_file:
                        dctx = zstd.ZstdDecompressor()
                        with dctx.stream_reader(compressed_file) as reader:
                            temp_file.write(reader.read())
                finally:
                    temp_file.flush()
            try:
                # Check both ELF modinfo and appended marker
                if ELF_TOOLS_AVAILABLE and _elf_has_signature_info(temp_path):
                    return True
                if _file_has_appended_signature_marker(temp_path):
                    return True
                return False
            finally:
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
        else:
            if ELF_TOOLS_AVAILABLE and _elf_has_signature_info(file_path):
                return True
            if _file_has_appended_signature_marker(file_path):
                return True
            return False
    except Exception:
        return None


def extract_from_compressed_elf(file_path: str) -> str:
    """
    Extract description from compressed .ko.zst file.
    
    Args:
        file_path: Path to the .ko.zst file
        
    Returns:
        str: Module description, or empty string if not found
    """
    if not ZSTD_AVAILABLE:
        print("Warning: zstandard library not available for decompressing .ko.zst files", file=sys.stderr)
        return ""
    
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
            description = extract_from_elf_file(temp_path)
            
            # Clean up temporary file
            os.unlink(temp_path)
            
            return description
    except Exception as e:
        print(f"Warning: Error decompressing {file_path}: {e}", file=sys.stderr)
        return ""


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
                
                # Get file path and description using modinfo/ELF
                file_path = get_module_file_path(name)
                description = get_module_description(name)
                signed_flag = is_module_signed_from_file(file_path)
                signed_str = 'Yes' if signed_flag else ('No' if signed_flag is False else 'Unknown')
                module = KernelModule(name, size, ref_count, dependencies, status, address, "loadable", file_path, description, signed_str)
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


def modules_to_json(modules: List[Union[KernelModule, BuiltinModule]], 
                   builtin_modules: List[BuiltinModule] = None) -> str:
    """Convert modules to JSON format."""
    data = {
        'loadable_modules': [],
        'builtin_modules': []
    }
    
    for module in modules:
        if isinstance(module, KernelModule):
            data['loadable_modules'].append({
                'name': module.name,
                'size': module.size,
                'ref_count': module.ref_count,
                'dependencies': module.dependencies,
                'status': module.status,
                'address': module.address,
                'type': module.module_type,
                'file_path': module.file_path,
                'description': module.description
            })
        else:
            data['builtin_modules'].append({
                'name': module.name,
                'description': module.description,
                'version': module.version,
                'author': module.author,
                'license': module.license,
                'type': module.module_type
            })
    
    if builtin_modules:
        for module in builtin_modules:
            data['builtin_modules'].append({
                'name': module.name,
                'description': module.description,
                'version': module.version,
                'author': module.author,
                'license': module.license,
                'type': module.module_type
            })
    
    return json.dumps(data, indent=2)


def modules_to_csv(modules: List[Union[KernelModule, BuiltinModule]], 
                  builtin_modules: List[BuiltinModule] = None) -> str:
    """Convert modules to CSV format."""
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Name', 'Type', 'Size', 'Ref Count', 'Status', 'Dependencies', 'File Path', 'Description'])
    
    # Write loadable modules
    for module in modules:
        if isinstance(module, KernelModule):
            writer.writerow([
                module.name,
                'Loadable',
                module.size,
                module.ref_count,
                module.status,
                ','.join(module.dependencies) if module.dependencies else '',
                module.file_path or 'N/A',
                module.description or 'N/A'
            ])
    
    # Write builtin modules
    if builtin_modules:
        for module in builtin_modules:
            writer.writerow([
                module.name,
                'Builtin',
                '',
                '',
                'Always',
                '',
                'N/A',  # Builtin modules don't have file paths
                module.description
            ])
    
    return output.getvalue()


def get_unloaded_modules(loaded_modules: List[KernelModule]) -> List[Dict]:
    """
    Get list of unloaded kernel modules from the current kernel version.
    
    Args:
        loaded_modules: List of currently loaded modules
        
    Returns:
        List of dictionaries containing unloaded module information
    """
    unloaded_modules = []
    
    try:
        # Get current kernel version
        kernel_version = os.uname().release
        modules_dir = f'/lib/modules/{kernel_version}'
        
        if not os.path.exists(modules_dir):
            return unloaded_modules
        
        # Get list of loaded module names
        loaded_names = {module.name for module in loaded_modules}
        
        # Find all .ko and .ko.zst files
        ko_patterns = [
            f'{modules_dir}/**/*.ko',
            f'{modules_dir}/**/*.ko.zst'
        ]
        
        for pattern in ko_patterns:
            for file_path in glob.glob(pattern, recursive=True):
                # Extract module name from file path
                module_name = os.path.basename(file_path)
                if module_name.endswith('.ko.zst'):
                    module_name = module_name[:-7]  # Remove .ko.zst
                elif module_name.endswith('.ko'):
                    module_name = module_name[:-3]  # Remove .ko
                
                # Skip if module is already loaded
                if module_name in loaded_names:
                    continue
                
                # Get file size
                try:
                    file_size = os.path.getsize(file_path)
                except OSError:
                    file_size = 0
                
                # Get description using ELF parsing
                description = get_module_description_from_file(file_path)
                
                unloaded_modules.append({
                    'name': module_name,
                    'file_path': file_path,
                    'size': file_size,
                    'description': description
                })
        
        # Sort by module name
        unloaded_modules.sort(key=lambda x: x['name'])
        
    except Exception as e:
        print(f"Warning: Error getting unloaded modules: {e}", file=sys.stderr)
    
    return unloaded_modules


def get_module_description_from_file(file_path: str) -> str:
    """
    Get module description from ELF file.
    
    Args:
        file_path: Path to the module file
        
    Returns:
        str: Module description, or empty string if not found
    """
    try:
        # Handle compressed modules
        if file_path.endswith('.ko.zst'):
            with tempfile.NamedTemporaryFile(suffix='.ko', delete=False) as temp_file:
                temp_path = temp_file.name
                
                with open(file_path, 'rb') as compressed_file:
                    dctx = zstd.ZstdDecompressor()
                    with dctx.stream_reader(compressed_file) as reader:
                        temp_file.write(reader.read())
                
                # Extract description from decompressed file
                description = extract_description_from_elf_file(temp_path)
                
                # Clean up temporary file
                os.unlink(temp_path)
                
                return description
        else:
            return extract_description_from_elf_file(file_path)
            
    except Exception:
        return ""


def modules_to_html(modules: List[Union[KernelModule, BuiltinModule]], 
                   builtin_modules: List[BuiltinModule] = None,
                   system_info: Dict = None) -> str:
    """Convert modules to HTML format with styled report."""
    import datetime
    import platform
    
    # Get system information
    if system_info is None:
        system_info = {
            'hostname': platform.node(),
            'system': platform.system(),
            'release': platform.release(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    # Calculate statistics
    loadable_count = len(modules)
    builtin_count = len(builtin_modules) if builtin_modules else 0
    
    # Get unloaded modules
    unloaded_modules = get_unloaded_modules([m for m in modules if isinstance(m, KernelModule)])
    unloaded_count = len(unloaded_modules)
    
    total_count = loadable_count + builtin_count
    
    # Calculate total size
    total_size = sum(module.size for module in modules if isinstance(module, KernelModule))
    
    # Group modules by status
    status_groups = {}
    for module in modules:
        if isinstance(module, KernelModule):
            status = module.status
            if status not in status_groups:
                status_groups[status] = 0
            status_groups[status] += 1
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kernel Modules Report - {system_info['hostname']}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f8fafc;
            color: #1e293b;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #1e40af 0%, #3730a3 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 1.1em;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f1f5f9;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #1e40af;
            margin-bottom: 5px;
        }}
        .stat-label {{
            color: #64748b;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .content {{
            padding: 30px;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section h2 {{
            color: #1e293b;
            border-bottom: 2px solid #1e40af;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .module-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            border: 1px solid #cbd5e1;
        }}
        .module-table th {{
            background: #1e40af;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 500;
            border-right: 1px solid #3b82f6;
        }}
        .module-table th:last-child {{
            border-right: none;
        }}
        .module-table th.sortable {{
            cursor: pointer;
            user-select: none;
            position: relative;
        }}
        .module-table th.sortable:hover {{
            background: #3b82f6;
        }}
        .module-table th.sortable::after {{
            content: ' ↕';
            opacity: 0.5;
            font-size: 0.8em;
        }}
        .module-table th.sortable.asc::after {{
            content: ' ↑';
            opacity: 1;
        }}
        .module-table th.sortable.desc::after {{
            content: ' ↓';
            opacity: 1;
        }}
        .collapsible-header {{
            cursor: pointer;
            user-select: none;
            position: relative;
        }}
        .collapsible-header::after {{
            content: ' ▼';
            position: absolute;
            right: 15px;
            top: 50%;
            transform: translateY(-50%);
            transition: transform 0.3s ease;
        }}
        .collapsible-header.collapsed::after {{
            transform: translateY(-50%) rotate(-90deg);
        }}
        .collapsible-content {{
            transition: opacity 0.3s ease;
        }}
        .collapsible-content.collapsed {{
            display: none;
        }}
        .collapsible-content.expanded {{
            display: block;
        }}
        .module-table td {{
            padding: 12px;
            border-bottom: 1px solid #e2e8f0;
            border-right: 1px solid #e2e8f0;
        }}
        .module-table td:last-child {{
            border-right: none;
        }}
        .module-table tr:nth-child(even) {{
            background: #f8fafc;
        }}
        .module-table tr:hover {{
            background: #e0f2fe;
        }}
        .module-type {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
        }}
        .type-loadable {{
            background: #dcfce7;
            color: #166534;
        }}
        .type-builtin {{
            background: #fef3c7;
            color: #92400e;
        }}
        .status-live {{
            color: #059669;
            font-weight: bold;
        }}
        .status-dead {{
            color: #dc2626;
            font-weight: bold;
        }}
        .status-unloading {{
            color: #d97706;
            font-weight: bold;
        }}
        .dependencies {{
            max-width: 200px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .footer {{
            background: #1e293b;
            color: white;
            padding: 20px;
            text-align: center;
            font-size: 0.9em;
        }}
        .search-box {{
            margin-bottom: 20px;
        }}
        .search-box input {{
            width: 100%;
            padding: 10px;
            border: 1px solid #cbd5e1;
            border-radius: 4px;
            font-size: 16px;
            background: white;
        }}
        .summary {{
            background: #e0f2fe;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .summary h3 {{
            margin-top: 0;
            color: #0c4a6e;
        }}
        .summary ul {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        .summary li {{
            margin: 5px 0;
        }}
    </style>
    <script>
        function searchModules() {{
            const input = document.getElementById('searchInput');
            const filter = input.value.toLowerCase();
            const tables = document.querySelectorAll('.module-table');
            
            tables.forEach(table => {{
                const rows = table.getElementsByTagName('tr');
                for (let i = 1; i < rows.length; i++) {{
                    const name = rows[i].getElementsByTagName('td')[0];
                    if (name) {{
                        const txtValue = name.textContent || name.innerText;
                        if (txtValue.toLowerCase().indexOf(filter) > -1) {{
                            rows[i].style.display = '';
                        }} else {{
                            rows[i].style.display = 'none';
                        }}
                    }}
                }}
            }});
        }}
        
        function sortTable(table, column, isNumeric = false) {{
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const header = table.querySelectorAll('th')[column];
            
            // Remove existing sort classes
            table.querySelectorAll('th').forEach(th => {{
                th.classList.remove('asc', 'desc');
            }});
            
            // Determine sort direction
            const isAsc = !header.classList.contains('asc');
            header.classList.add(isAsc ? 'asc' : 'desc');
            
            // Sort rows
            rows.sort((a, b) => {{
                const aVal = a.cells[column].textContent.trim();
                const bVal = b.cells[column].textContent.trim();
                
                let comparison = 0;
                if (isNumeric) {{
                    const aNum = parseFloat(aVal.replace(/[^0-9.-]/g, '')) || 0;
                    const bNum = parseFloat(bVal.replace(/[^0-9.-]/g, '')) || 0;
                    comparison = aNum - bNum;
                }} else {{
                    comparison = aVal.localeCompare(bVal);
                }}
                
                return isAsc ? comparison : -comparison;
            }});
            
            // Re-append sorted rows
            rows.forEach(row => tbody.appendChild(row));
        }}
        
        function makeSortable() {{
            const tables = document.querySelectorAll('.module-table');
            tables.forEach(table => {{
                const headers = table.querySelectorAll('th');
                headers.forEach((header, index) => {{
                    if (header.textContent.trim() !== '') {{
                        header.classList.add('sortable');
                        header.addEventListener('click', () => {{
                            // Determine if column is numeric based on header text
                            const numericColumns = ['Size', 'Ref Count', 'Count', 'Percentage'];
                            const isNumeric = numericColumns.includes(header.textContent.trim());
                            sortTable(table, index, isNumeric);
                        }});
                    }}
                }});
            }});
        }}
        
        function makeCollapsible() {{
            const sections = document.querySelectorAll('.section');
            sections.forEach((section, index) => {{
                const header = section.querySelector('h2');
                const table = section.querySelector('.module-table');
                
                if (header && table) {{
                    // First table (Loadable Modules) is expanded by default
                    if (index === 0) {{
                        header.classList.add('collapsible-header', 'expanded');
                        table.classList.add('collapsible-content', 'expanded');
                    }} else {{
                        header.classList.add('collapsible-header', 'collapsed');
                        table.classList.add('collapsible-content', 'collapsed');
                    }}
                    
                    header.addEventListener('click', () => {{
                        const isCollapsed = header.classList.contains('collapsed');
                        if (isCollapsed) {{
                            header.classList.remove('collapsed');
                            header.classList.add('expanded');
                            table.classList.remove('collapsed');
                            table.classList.add('expanded');
                        }} else {{
                            header.classList.add('collapsed');
                            header.classList.remove('expanded');
                            table.classList.remove('expanded');
                            table.classList.add('collapsed');
                        }}
                    }});
                }}
            }});
        }}
        
        // Initialize sorting and collapsible when page loads
        document.addEventListener('DOMContentLoaded', () => {{
            makeSortable();
            makeCollapsible();
        }});
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Kernel Modules Report</h1>
            <p>{system_info['hostname']} - {system_info['timestamp']}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{total_count}</div>
                <div class="stat-label">Loaded Modules</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{loadable_count}</div>
                <div class="stat-label">Loadable</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{builtin_count}</div>
                <div class="stat-label">Builtin</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{unloaded_count}</div>
                <div class="stat-label">Unloaded</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{format_size(total_size)}</div>
                <div class="stat-label">Total Size</div>
            </div>
        </div>
        
        <div class="content">
            <div class="summary">
                <h3>System Information</h3>
                <ul>
                    <li><strong>Hostname:</strong> {system_info['hostname']}</li>
                    <li><strong>System:</strong> {system_info['system']} {system_info['release']}</li>
                    <li><strong>Architecture:</strong> {system_info['machine']}</li>
                    <li><strong>Processor:</strong> {system_info['processor']}</li>
                    <li><strong>Report Generated:</strong> {system_info['timestamp']}</li>
                </ul>
            </div>
            
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="Search modules..." onkeyup="searchModules()">
            </div>
            
            <div class="section">
                <h2>Loadable Kernel Modules ({loadable_count})</h2>
                <table class="module-table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Size</th>
                            <th>Ref Count</th>
                            <th>Dependencies</th>
                            <th>File Path</th>
                            <th>Description</th>
                            <th>Signed</th>
                            <th>Address</th>
                        </tr>
                    </thead>
                    <tbody>"""
    
    # Add loadable modules
    for module in modules:
        if isinstance(module, KernelModule):
            deps_str = ', '.join(module.dependencies) if module.dependencies else 'None'
            file_path = module.file_path or 'N/A'
            description = module.description or 'N/A'
            html += f"""
                        <tr>
                            <td><strong>{module.name}</strong></td>
                            <td>{format_size(module.size)}</td>
                            <td>{module.ref_count}</td>
                            <td class="dependencies" title="{deps_str}">{deps_str}</td>
                            <td><code>{file_path}</code></td>
                            <td>{description}</td>
                            <td>{module.signed}</td>
                            <td><code>{module.address}</code></td>
                        </tr>"""
    
    html += """
                    </tbody>
                </table>
            </div>"""
    
    # Add builtin modules if present
    if builtin_modules:
        html += f"""
            <div class="section">
                <h2>Builtin Kernel Modules ({builtin_count})</h2>
                <table class="module-table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Description</th>
                            <th>Version</th>
                            <th>Author</th>
                            <th>License</th>
                        </tr>
                    </thead>
                    <tbody>"""
        
        for module in builtin_modules:
            html += f"""
                            <tr>
                                <td><strong>{module.name}</strong></td>
                                <td>{module.description or 'N/A'}</td>
                                <td>{module.version or 'N/A'}</td>
                                <td>{module.author or 'N/A'}</td>
                                <td>{module.license or 'N/A'}</td>
                            </tr>"""
        
        html += """
                    </tbody>
                </table>
            </div>"""
    
    # Add unloaded modules table
    if unloaded_modules:
        html += f"""
            <div class="section">
                <h2>Unloaded Kernel Modules ({unloaded_count})</h2>
                <table class="module-table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Size</th>
                            <th>File Path</th>
                            <th>Description</th>
                        </tr>
                    </thead>
                    <tbody>"""
        
        for module in unloaded_modules:
            file_path = module['file_path']
            description = module['description'] or 'N/A'
            html += f"""
                        <tr>
                            <td><strong>{module['name']}</strong></td>
                            <td>{format_size(module['size'])}</td>
                            <td><code>{file_path}</code></td>
                            <td>{description}</td>
                        </tr>"""
        
        html += """
                    </tbody>
                </table>
            </div>"""
    
    # Add status summary
    if status_groups:
        html += """
            <div class="section">
                <h2>Module Status Summary</h2>
                <table class="module-table">
                    <thead>
                        <tr>
                            <th>Status</th>
                            <th>Count</th>
                            <th>Percentage</th>
                        </tr>
                    </thead>
                    <tbody>"""
        
        for status, count in status_groups.items():
            percentage = (count / loadable_count) * 100 if loadable_count > 0 else 0
            status_class = f"status-{status.lower()}"
            html += f"""
                        <tr>
                            <td><span class="{status_class}">{status}</span></td>
                            <td>{count}</td>
                            <td>{percentage:.1f}%</td>
                        </tr>"""
        
        html += """
                    </tbody>
                </table>
            </div>"""
    
    html += f"""
        </div>
        
        <div class="footer">
            <p>Generated by Kernel Module Lister v2.0.0 on {system_info['timestamp']}</p>
            <p>System: {system_info['system']} {system_info['release']} ({system_info['machine']})</p>
        </div>
    </div>
</body>
</html>"""
    
    return html


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
            size_str = format_size(module.size)
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


def main():
    """Main function to run the kernel module lister."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="List all kernel modules (loadable and builtin) by parsing /proc/modules and other sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 list_kernel_modules.py                    # Simple list of loadable modules
  python3 list_kernel_modules.py --detailed         # Detailed information
  python3 list_kernel_modules.py --builtin          # Include builtin modules
  python3 list_kernel_modules.py --builtin-only     # Show only builtin modules
  python3 list_kernel_modules.py --count            # Show only count
  
  # Filtering examples
  python3 list_kernel_modules.py --filter "snd*"    # Show only modules starting with 'snd'
  python3 list_kernel_modules.py --min-size 50000   # Show modules >= 50KB
  python3 list_kernel_modules.py --min-refs 2       # Show modules with >= 2 references
  
  # Sorting examples
  python3 list_kernel_modules.py --sort size         # Sort by size
  python3 list_kernel_modules.py --sort refs --reverse  # Sort by refs, largest first
  
  # Output format examples
  python3 list_kernel_modules.py --json             # JSON output
  python3 list_kernel_modules.py --csv              # CSV output
  python3 list_kernel_modules.py --html             # HTML report
  python3 list_kernel_modules.py --html -o report.html  # Save HTML to file
  python3 list_kernel_modules.py --quiet            # Suppress headers
        """
    )
    
    parser.add_argument('--detailed', '-d', action='store_true',
                       help='Show detailed information for each module')
    parser.add_argument('--count', '-c', action='store_true',
                       help='Show only the count of modules')
    parser.add_argument('--builtin', '-b', action='store_true',
                       help='Include builtin modules in the output')
    parser.add_argument('--builtin-only', action='store_true',
                       help='Show only builtin modules (exclude loadable modules)')
    
    # Filtering options
    parser.add_argument('--filter', '-f', type=str, metavar='PATTERN',
                       help='Filter modules by name pattern (supports wildcards)')
    parser.add_argument('--min-size', type=int, metavar='BYTES',
                       help='Show only modules with size >= specified bytes')
    parser.add_argument('--max-size', type=int, metavar='BYTES',
                       help='Show only modules with size <= specified bytes')
    parser.add_argument('--min-refs', type=int, metavar='COUNT',
                       help='Show only modules with reference count >= specified count')
    parser.add_argument('--status', choices=['Live', 'Dead', 'Unloading'],
                       help='Filter by module status')
    
    # Sorting options
    parser.add_argument('--sort', choices=['name', 'size', 'refs', 'status'],
                       default='name', help='Sort modules by specified field (default: name)')
    parser.add_argument('--reverse', '-r', action='store_true',
                       help='Reverse sort order')
    
    # Output format options
    parser.add_argument('--json', action='store_true',
                       help='Output in JSON format')
    parser.add_argument('--csv', action='store_true',
                       help='Output in CSV format')
    parser.add_argument('--html', action='store_true',
                       help='Output in HTML format with styled report')
    parser.add_argument('--output', '-o', type=str, metavar='FILE',
                       help='Write output to specified file instead of stdout')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Suppress headers and only show module data')
    parser.add_argument('--no-color', action='store_true',
                       help='Disable colored output')
    
    # Information options
    parser.add_argument('--version', action='version', version='%(prog)s 2.0.0',
                       help='Show version information')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output with additional debugging information')
    
    args = parser.parse_args()
    
    try:
        # Verbose output
        if args.verbose:
            print("Verbose mode enabled", file=sys.stderr)
            print(f"Arguments: {args}", file=sys.stderr)
        
        # Get loadable modules
        loadable_modules = parse_proc_modules()
        
        # Get builtin modules if requested
        builtin_modules = None
        if args.builtin or args.builtin_only or args.html:
            builtin_modules = get_all_builtin_modules()
        
        # Combine modules for processing
        all_modules = []
        if not args.builtin_only:
            all_modules.extend(loadable_modules)
        if args.builtin or args.builtin_only or args.html:
            if builtin_modules:
                all_modules.extend(builtin_modules)
        
        # Apply filtering
        if any([args.filter, args.min_size, args.max_size, args.min_refs, args.status]):
            all_modules = filter_modules(
                all_modules,
                name_pattern=args.filter,
                min_size=args.min_size,
                max_size=args.max_size,
                min_refs=args.min_refs,
                status=args.status
            )
        
        # Apply sorting
        all_modules = sort_modules(all_modules, args.sort, args.reverse)
        
        # Separate loadable and builtin modules for display
        filtered_loadable = [m for m in all_modules if isinstance(m, KernelModule)]
        filtered_builtin = [m for m in all_modules if isinstance(m, BuiltinModule)]
        
        if args.count:
            total_count = len(all_modules)
            loadable_count = len(filtered_loadable)
            builtin_count = len(filtered_builtin)
            
            if args.builtin_only:
                print(f"Total builtin kernel modules: {builtin_count}")
            elif args.builtin:
                print(f"Total kernel modules: {total_count} ({loadable_count} loadable, {builtin_count} builtin)")
            else:
                print(f"Total loaded kernel modules: {loadable_count}")
        else:
            # Handle different output formats
            output_content = ""
            if args.json:
                output_content = modules_to_json(filtered_loadable, filtered_builtin)
            elif args.csv:
                output_content = modules_to_csv(filtered_loadable, filtered_builtin)
            elif args.html:
                output_content = modules_to_html(filtered_loadable, filtered_builtin)
            else:
                # Standard display - capture output
                import io
                from contextlib import redirect_stdout
                f = io.StringIO()
                with redirect_stdout(f):
                    if args.builtin_only:
                        if filtered_builtin:
                            display_modules([], filtered_builtin, args.detailed, True, args.quiet)
                        else:
                            print("No builtin modules found.")
                    else:
                        display_modules(filtered_loadable, filtered_builtin, args.detailed, args.builtin, args.quiet)
                output_content = f.getvalue()
            
            # Write output to file or stdout
            if args.output:
                try:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        f.write(output_content)
                    if args.verbose:
                        print(f"Output written to {args.output}", file=sys.stderr)
                except Exception as e:
                    print(f"Error writing to file {args.output}: {e}", file=sys.stderr)
                    sys.exit(1)
            else:
                print(output_content)
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
