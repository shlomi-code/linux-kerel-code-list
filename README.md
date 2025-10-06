# Linux Kernel Module Lister

A fast, feature-rich tool to inspect Linux kernel modules. It parses `/proc/modules` and system metadata to produce readable CLI output and beautiful HTML reports—with sorting, search, summaries, signatures, and compact charts.

## Key Features

- **Dual sources**: Lists currently loaded modules and discovers builtin and unloaded modules from `/lib/modules/<version>`.
- **Multiple output formats**:
  - CLI table (simple or detailed)
  - JSON and CSV
  - HTML report with modern styling
- **Rich HTML report**:
  - System information summary and stats cards
  - Loadable, Builtin, and Unloaded modules sections
  - Search box, sortable headers, and collapsible sections
  - Medium-sized overview bar chart (Loaded/Builtin/Unloaded)
  - Privilege notice when not run as root
- **Module metadata**:
  - Size (human-readable), reference count, dependencies, status, address
  - File path and description (via ELF `.modinfo` or `modinfo` fallback)
- **Signature awareness (HTML CLI report)**:
  - Signed column derives from ELF `.modinfo` keys and the "Module signature appended" marker
  - Handles `.ko.zst` by temporary decompression (zstandard)
- **Robustness**:
  - Graceful error handling and safe fallbacks
  - Works with or without elevated privileges (some addresses may be masked)

## Installation

Python 3.8+ recommended.

Optional dependencies for enhanced features:

```bash
pip install pyelftools zstandard
```

These enable ELF parsing and `.ko.zst` decompression for descriptions and signature detection.

## Usage

### Basic
```bash
python3 list_kernel_modules.py
```

### Detailed CLI view
```bash
python3 list_kernel_modules.py --detailed
```

### Include builtin modules or show only builtin
```bash
python3 list_kernel_modules.py --builtin
python3 list_kernel_modules.py --builtin-only
```

### Counts only
```bash
python3 list_kernel_modules.py --count
```

### Filtering and sorting
```bash
# Wildcard filter
python3 list_kernel_modules.py --filter "snd*"

# Size and references
python3 list_kernel_modules.py --min-size 50000 --min-refs 2

# Sort by size descending
python3 list_kernel_modules.py --sort size --reverse
```

### Export formats
```bash
# JSON
python3 list_kernel_modules.py --json > modules.json

# CSV
python3 list_kernel_modules.py --csv > modules.csv

# HTML (recommended)
python3 list_kernel_modules.py --html -o report.html
```

The HTML report includes system info, statistics, searchable/sortable tables for Loadable, Builtin, and Unloaded modules, and a medium-sized bar chart summarizing module counts.

## How it works (high level)

- Parses `/proc/modules` for actively loaded modules.
- Uses kernel paths under `/lib/modules/<version>` to find builtin and unloaded modules.
- Extracts metadata from ELF `.modinfo` (via `pyelftools`) and falls back to `modinfo` as needed.
- Detects signatures by checking `.modinfo` keys and looking for the "Module signature appended" trailer; supports `.ko.zst` via `zstandard`.

## Requirements

- Linux system with `/proc/modules`
- Python 3.8+
- Optional: `pyelftools`, `zstandard` for richer metadata and compressed modules

## Tips and caveats

- Running as non-root may mask or hide some kernel addresses; the HTML report displays a notice and continues.
- Signature detection best-effort: absence of markers may show as "Unknown".

## Development and testing

Run tests:
```bash
python3 test_kernel_modules.py
```

Useful targets:
- Unit tests validate parsing and formatting
- Integration tests compare results with `lsmod`

## References

- [Linux Module HOWTO](https://tldp.org/HOWTO/Module-HOWTO/x73.html)
- [Kbuild: modules.builtin](https://www.kernel.org/doc/html/latest/kbuild/kbuild.html#modules-builtin)
- [man: insmod](https://man7.org/linux/man-pages/man8/insmod.8.html)
- [man: lsmod](https://man7.org/linux/man-pages/man8/lsmod.8.html)
- [man: proc](https://man7.org/linux/man-pages/man5/proc.5.html)

## License

See `LICENSE` in this repository.
