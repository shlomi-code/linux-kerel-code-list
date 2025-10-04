# Linux Kernel Module Lister

A Python script that parses `/proc/modules` to list all currently loaded kernel modules (LKMs - Loadable Kernel Modules) on a Linux system.

## Overview

This script provides a comprehensive way to view all loaded kernel modules, including their size, reference count, dependencies, and status. It's an alternative to using the `lsmod` command-line utility, but with more detailed output and formatting options.

## Features

- **Simple List View**: Clean table format showing module name, size, reference count, and status
- **Detailed View**: Comprehensive information including dependencies and memory addresses
- **Human-readable Sizes**: Converts byte sizes to KB, MB, GB format
- **Sorted Output**: Modules are alphabetically sorted for easy reading
- **Error Handling**: Graceful handling of permission errors and missing files
- **Command-line Options**: Flexible output formatting

## Usage

### Basic Usage
```bash
python3 list_kernel_modules.py
```

### Detailed Information
```bash
python3 list_kernel_modules.py --detailed
```

### Show Only Count
```bash
python3 list_kernel_modules.py --count
```

### Help
```bash
python3 list_kernel_modules.py --help
```

## Example Output

### Simple List
```
Loaded Kernel Modules (45 total)
============================================================
Module Name               Size       Ref Count  Status    
------------------------------------------------------------
acpi_cpufreq             20480      0          Live      
ahci                     45056      2          Live      
ata_generic              16384      0          Live      
...
```

### Detailed View
```
Loaded Kernel Modules (45 total)
============================================================
1. Module: acpi_cpufreq
  Size: 20480 bytes
  Reference Count: 0
  Dependencies: None
  Status: Live
  Address: 0xffffffffc1234000

2. Module: ahci
  Size: 45056 bytes
  Reference Count: 2
  Dependencies: libahci
  Status: Live
  Address: 0xffffffffc1245000
...
```

## How It Works

The script reads from `/proc/modules`, which is a virtual file that contains information about all currently loaded kernel modules. The format of each line in `/proc/modules` is:

```
module_name size ref_count dependencies status address
```

Where:
- **module_name**: Name of the kernel module
- **size**: Size of the module in bytes
- **ref_count**: Number of references to this module
- **dependencies**: Comma-separated list of modules this module depends on (or "-" if none)
- **status**: Module status (usually "Live")
- **address**: Memory address where the module is loaded

## Requirements

- Python 3.6 or higher
- Linux system with `/proc/modules` available
- Read permissions for `/proc/modules`

## Testing

The project includes comprehensive unit tests that verify the script's output matches the standard `lsmod` command. The tests ensure:

- **Module names match exactly** between our script and `lsmod`
- **Module sizes are consistent** (converted from bytes to human-readable format)
- **Reference counts are identical**
- **Dependencies are parsed correctly** (including handling of status markers like `[permanent]`)
- **Output formatting is correct** for both simple and detailed views
- **Command-line options work as expected**

### Running Tests

```bash
# Run all tests
python3 test_kernel_modules.py

# Run with verbose output
python3 test_kernel_modules.py -v

# Run specific test class
python3 -m unittest test_kernel_modules.TestKernelModuleLister

# Run specific test method
python3 -m unittest test_kernel_modules.TestKernelModuleLister.test_module_names_match_lsmod
```

### Test Coverage

The test suite includes:

- **Unit Tests**: Test individual functions and parsing logic
- **Integration Tests**: Compare full output between our script and `lsmod`
- **Format Tests**: Verify output formatting and command-line options
- **Error Handling**: Test graceful handling of permission errors and missing files

### Test Files

- `test_kernel_modules.py`: Comprehensive test suite with 11 test cases covering all functionality
- Tests compare output against the standard `lsmod` command to ensure consistency
- Includes both unit tests and integration tests for thorough coverage

## About Loadable Kernel Modules (LKMs)

Loadable Kernel Modules (LKMs) allow adding code to the Linux kernel without recompiling and linking the kernel binary. They are used for various purposes including:

- Filesystem drivers
- Device drivers
- Network protocols
- System utilities

When compiling the Linux kernel, you can choose to incorporate modules as part of the kernel itself (built-in modules) or as separate `.ko` (kernel object) files. For already compiled kernels, modules can only be created as separate kernel object files that can be loaded using utilities like `insmod`.

## References

- [The Linux Concept Journey — Loadable Kernel Module (LKM)](https://medium.com/@boutnaru/the-linux-concept-journey-loadable-kernel-module-lkm-5eaa4db346a1) - Comprehensive article about Linux Loadable Kernel Modules
- [Linux Module HOWTO](https://tldp.org/HOWTO/Module-HOWTO/x73.html) - Official documentation on kernel modules
- [insmod manual page](https://man7.org/linux/man-pages/man8/insmod.8.html) - Manual for loading kernel modules
- [lsmod manual page](https://man7.org/linux/man-pages/man8/lsmod.8.html) - Manual for listing loaded modules
- [proc manual page](https://man7.org/linux/man-pages/man5/proc.5.html) - Documentation for /proc filesystem

## License

This project is licensed under the same terms as the LICENSE file in this repository.
