# Linux Kernel Module Lister

A comprehensive, feature-rich tool for inspecting Linux kernel modules. It parses `/proc/modules` and system metadata to produce readable CLI output, beautiful HTML reports, and structured data exports—with advanced filtering, sorting, search capabilities, and detailed module analysis.

## 🚀 Key Features

### 📊 **Comprehensive Module Discovery**
- **Loadable modules**: Currently loaded modules from `/proc/modules`
- **Builtin modules**: Kernel built-in modules with descriptions from `modules.builtin.modinfo`
- **Unloaded modules**: Available but not loaded modules from `/lib/modules/<version>`

### 🎨 **Multiple Output Formats**
- **CLI table**: Simple or detailed console output with color support
- **JSON**: Structured data for programmatic processing
- **CSV**: Spreadsheet-compatible format
- **HTML report**: Professional web-based reports with interactive features

### 🔍 **Advanced Filtering & Sorting**
- **Pattern filtering**: Wildcard support (e.g., `snd*`, `*usb*`)
- **Size filtering**: Min/max size constraints
- **Reference filtering**: Filter by module reference count
- **Status filtering**: Filter by module status (Live, Dead, Unloading)
- **Flexible sorting**: By name, size, references, or status (ascending/descending)

### 📈 **Rich HTML Reports**
- **System information**: Hostname, kernel version, architecture, processor
- **Statistics dashboard**: Module counts, total sizes, status breakdowns
- **Interactive tables**: Searchable, sortable, collapsible sections
- **Visual charts**: Overview bar charts showing module distribution
- **Responsive design**: Modern, professional styling with mobile support
- **Privilege awareness**: Notifications when running without root privileges

### 🔐 **Module Signature Detection**
- **ELF parsing**: Extracts signature information from `.modinfo` sections
- **Compressed support**: Handles `.ko.zst` files via zstandard decompression
- **Signature markers**: Detects "Module signature appended" indicators
- **Fallback support**: Graceful degradation when signatures unavailable

### 📋 **Detailed Module Metadata**
- **Basic info**: Name, size (human-readable), reference count, status, memory address
- **Dependencies**: Module dependency chains and relationships
- **File paths**: Full paths to module files (`.ko` or `.ko.zst`)
- **Descriptions**: Module descriptions extracted from ELF or `modinfo`
- **Builtin metadata**: Descriptions for builtin modules from kernel sources

### 🛠 **Developer-Friendly Features**
- **Modular architecture**: Clean separation of concerns with reusable components
- **Comprehensive testing**: Unit tests and integration tests included
- **Error handling**: Robust error handling with informative messages
- **Verbose mode**: Detailed debugging information when needed
- **API support**: Programmatic access via Python modules

## 📦 Installation

### Requirements
- **Python 3.8+** (recommended: Python 3.9+)
- **Linux system** with `/proc/modules`
- **Root privileges** (optional, for full address visibility)

### Optional Dependencies
For enhanced features including ELF parsing and compressed module support:

```bash
pip install pyelftools zstandard
```

These enable:
- Module description extraction from ELF files
- Signature detection in kernel modules
- Support for compressed `.ko.zst` modules
- Enhanced metadata extraction

## 🚀 Usage

### Basic Commands

```bash
# Simple list of loaded modules
python3 list_kernel_modules.py

# Detailed information with all metadata
python3 list_kernel_modules.py --detailed

# Show only module counts
python3 list_kernel_modules.py --count
```

### Module Discovery

```bash
# Include builtin modules
python3 list_kernel_modules.py --builtin

# Show only builtin modules
python3 list_kernel_modules.py --builtin-only

# Show all modules (loaded + builtin + unloaded)
python3 list_kernel_modules.py --builtin --html
```

### Filtering

```bash
# Wildcard pattern filtering
python3 list_kernel_modules.py --filter "snd*"           # Audio modules
python3 list_kernel_modules.py --filter "*usb*"          # USB-related modules
python3 list_kernel_modules.py --filter "nvidia*"        # NVIDIA modules

# Size-based filtering
python3 list_kernel_modules.py --min-size 50000          # Modules >= 50KB
python3 list_kernel_modules.py --max-size 100000         # Modules <= 100KB
python3 list_kernel_modules.py --min-size 10000 --max-size 50000

# Reference count filtering
python3 list_kernel_modules.py --min-refs 2              # Modules with 2+ references
python3 list_kernel_modules.py --min-refs 5 --max-refs 10

# Status filtering
python3 list_kernel_modules.py --status Live             # Only live modules
python3 list_kernel_modules.py --status Dead             # Only dead modules
```

### Sorting

```bash
# Sort by different fields
python3 list_kernel_modules.py --sort name               # Alphabetical (default)
python3 list_kernel_modules.py --sort size               # By size (smallest first)
python3 list_kernel_modules.py --sort refs               # By reference count
python3 list_kernel_modules.py --sort status             # By status

# Reverse sort order
python3 list_kernel_modules.py --sort size --reverse     # Largest modules first
python3 list_kernel_modules.py --sort refs --reverse     # Most referenced first
```

### Output Formats

```bash
# JSON output (structured data)
python3 list_kernel_modules.py --json > modules.json
python3 list_kernel_modules.py --builtin --json > all_modules.json

# CSV output (spreadsheet compatible)
python3 list_kernel_modules.py --csv > modules.csv
python3 list_kernel_modules.py --detailed --csv > detailed_modules.csv

# HTML report (recommended)
python3 list_kernel_modules.py --html -o report.html
python3 list_kernel_modules.py --builtin --html -o complete_report.html
```

### Advanced Options

```bash
# Quiet mode (suppress headers)
python3 list_kernel_modules.py --quiet

# Disable colored output
python3 list_kernel_modules.py --no-color

# Verbose debugging
python3 list_kernel_modules.py --verbose

# Show version
python3 list_kernel_modules.py --version
```

### Complex Examples

```bash
# Find large audio modules that are currently loaded
python3 list_kernel_modules.py --filter "snd*" --min-size 100000 --status Live

# Generate comprehensive HTML report with all modules
python3 list_kernel_modules.py --builtin --html -o system_modules.html

# Export large modules to CSV for analysis
python3 list_kernel_modules.py --min-size 200000 --sort size --reverse --csv > large_modules.csv

# Find modules with many dependencies
python3 list_kernel_modules.py --min-refs 5 --detailed --sort refs --reverse
```

## 🏗 Architecture

### Modular Design
The tool is built with a clean, modular architecture:

- **`models.py`**: Data structures for kernel modules and builtin modules
- **`parsers.py`**: Parsing logic for `/proc/modules`, builtin modules, and metadata extraction
- **`formatters.py`**: Output formatting for CLI, JSON, CSV, and HTML
- **`filters.py`**: Filtering and sorting functionality
- **`__init__.py`**: Package initialization and public API

### Data Sources
- **`/proc/modules`**: Currently loaded modules
- **`/lib/modules/<version>/modules.builtin`**: Builtin module names
- **`/lib/modules/<version>/modules.builtin.modinfo`**: Builtin module metadata
- **ELF files**: Module descriptions and signatures from `.modinfo` sections
- **`modinfo` command**: Fallback for metadata extraction

## 🧪 Testing

Run the comprehensive test suite:

```bash
python3 test_kernel_modules.py
```

The test suite includes:
- **Unit tests**: Individual component testing
- **Integration tests**: End-to-end functionality validation
- **Comparison tests**: Results validation against `lsmod`
- **Error handling tests**: Edge case and error condition testing

## 📊 HTML Report Features

The HTML reports provide a professional, interactive interface:

### Dashboard
- **System information**: Complete system details
- **Statistics cards**: Module counts, sizes, and distributions
- **Visual charts**: Bar charts showing module distribution
- **Privilege notices**: Warnings when running without root

### Interactive Tables
- **Search functionality**: Real-time module name filtering
- **Sortable columns**: Click headers to sort by any field
- **Collapsible sections**: Expandable/collapsible module categories
- **Responsive design**: Works on desktop and mobile devices

### Module Categories
- **Loadable modules**: Currently loaded modules with full metadata
- **Builtin modules**: Kernel built-in modules with descriptions
- **Unloaded modules**: Available but not loaded modules

## 🔧 Development

### Project Structure
```
linux-kerel-code-list/
├── list_kernel_modules.py      # Main script
├── kernel_modules/             # Modular package
│   ├── __init__.py
│   ├── models.py              # Data models
│   ├── parsers.py             # Parsing logic
│   ├── formatters.py          # Output formatting
│   └── filters.py             # Filtering/sorting
├── example_usage.py           # Usage examples
├── test_kernel_modules.py     # Test suite
├── README.md                  # This file
└── LICENSE                    # License information
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📚 References

- [Linux Module HOWTO](https://tldp.org/HOWTO/Module-HOWTO/x73.html)
- [Kbuild: modules.builtin](https://www.kernel.org/doc/html/latest/kbuild/kbuild.html#modules-builtin)
- [man: insmod](https://man7.org/linux/man-pages/man8/insmod.8.html)
- [man: lsmod](https://man7.org/linux/man-pages/man8/lsmod.8.html)
- [man: proc](https://man7.org/linux/man-pages/man5/proc.5.html)
- [ELF Specification](https://refspecs.linuxfoundation.org/elf/elf.pdf)

## ⚠️ Notes and Caveats

- **Root privileges**: Running as non-root may mask kernel addresses; the HTML report displays appropriate notices
- **Signature detection**: Best-effort detection; absence of markers may show as "Unknown"
- **Compressed modules**: Requires `zstandard` package for `.ko.zst` support
- **ELF parsing**: Requires `pyelftools` for enhanced metadata extraction

## 📄 License

See `LICENSE` file in this repository for license information.

---

**Linux Kernel Module Lister** - Comprehensive kernel module inspection and analysis tool for Linux systems.