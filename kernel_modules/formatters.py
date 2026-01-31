"""
Output formatters for kernel module data.

This module contains classes for formatting kernel module information
into different output formats (JSON, CSV, HTML).
"""

import json
import csv
import io
import datetime
import platform
import os
import glob
from typing import List, Dict, Union
from .models import KernelModule, BuiltinModule


class BaseFormatter:
    """Base class for all formatters."""
    
    def format(self, modules: List[Union[KernelModule, BuiltinModule]], 
               builtin_modules: List[BuiltinModule] = None,
               system_info: Dict = None) -> str:
        """
        Format modules into output string.
        
        Args:
            modules: List of loadable modules
            builtin_modules: List of builtin modules
            system_info: System information dictionary
            
        Returns:
            str: Formatted output
        """
        raise NotImplementedError


class JSONFormatter(BaseFormatter):
    """Formatter for JSON output."""
    
    def format(self, modules: List[Union[KernelModule, BuiltinModule]], 
               builtin_modules: List[BuiltinModule] = None,
               system_info: Dict = None) -> str:
        """Convert modules to JSON format."""
        data = {
            'loadable_modules': [],
            'builtin_modules': []
        }
        
        for module in modules:
            if isinstance(module, KernelModule):
                data['loadable_modules'].append(module.to_dict())
            else:
                data['builtin_modules'].append(module.to_dict())
        
        if builtin_modules:
            for module in builtin_modules:
                data['builtin_modules'].append(module.to_dict())
        
        return json.dumps(data, indent=2)


class CSVFormatter(BaseFormatter):
    """Formatter for CSV output."""
    
    def format(self, modules: List[Union[KernelModule, BuiltinModule]], 
               builtin_modules: List[BuiltinModule] = None,
               system_info: Dict = None) -> str:
        """Convert modules to CSV format."""
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


class HTMLFormatter(BaseFormatter):
    """Formatter for HTML output with professional styling."""
    
    @staticmethod
    def _get_unloaded_modules(loaded_modules: List[KernelModule]) -> List[Dict]:
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
                    description = HTMLFormatter._get_module_description_from_file(file_path)
                    
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
    
    @staticmethod
    def _get_module_description_from_file(file_path: str) -> str:
        """
        Get module description from ELF file.
        
        Args:
            file_path: Path to the module file
            
        Returns:
            str: Module description, or empty string if not found
        """
        try:
            from elftools.elf.elffile import ELFFile
            import tempfile
            import zstandard as zstd
            
            # Handle compressed modules
            if file_path.endswith('.ko.zst'):
                with tempfile.NamedTemporaryFile(suffix='.ko', delete=False) as temp_file:
                    temp_path = temp_file.name
                    
                    with open(file_path, 'rb') as compressed_file:
                        dctx = zstd.ZstdDecompressor()
                        with dctx.stream_reader(compressed_file) as reader:
                            temp_file.write(reader.read())
                    
                    # Extract description from decompressed file
                    description = HTMLFormatter._extract_description_from_elf_file(temp_path)
                    
                    # Clean up temporary file
                    os.unlink(temp_path)
                    
                    return description
            else:
                return HTMLFormatter._extract_description_from_elf_file(file_path)
                
        except Exception:
            return ""
    
    @staticmethod
    def _extract_description_from_elf_file(file_path: str) -> str:
        """
        Extract description from ELF file.
        
        Args:
            file_path: Path to the .ko file
            
        Returns:
            str: Module description, or empty string if not found
        """
        try:
            from elftools.elf.elffile import ELFFile
            
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
        except Exception:
            return ""
    
    def format(self, modules: List[Union[KernelModule, BuiltinModule]], 
               builtin_modules: List[BuiltinModule] = None,
               system_info: Dict = None) -> str:
        """Convert modules to HTML format with styled report."""
        
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
        unloaded_modules = self._get_unloaded_modules([m for m in modules if isinstance(m, KernelModule)])
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
        .column-selector {{
            margin-bottom: 12px;
            padding: 10px 14px;
            background: #f1f5f9;
            border-radius: 6px;
            border: 1px solid #e2e8f0;
        }}
        .column-selector .column-selector-label {{
            font-weight: 600;
            color: #475569;
            margin-right: 12px;
        }}
        .column-selector label {{
            margin-right: 14px;
            cursor: pointer;
            font-size: 0.95em;
            white-space: nowrap;
        }}
        .column-selector label:hover {{
            color: #1e40af;
        }}
        .column-selector input[type="checkbox"] {{
            margin-right: 4px;
            vertical-align: middle;
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
        .notice-warning {{
            background: #fff7ed;
            border: 1px solid #fed7aa;
            color: #9a3412;
            padding: 12px 16px;
            border-radius: 6px;
            margin: 0 0 20px 0;
        }}
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
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
        
        function setupColumnToggles() {{
            document.querySelectorAll('.column-selector').forEach(selectorEl => {{
                const tableId = selectorEl.getAttribute('data-for-table');
                const table = tableId ? document.getElementById(tableId) : null;
                if (!table) return;
                selectorEl.querySelectorAll('input[type="checkbox"][data-col]').forEach(cb => {{
                    const col = parseInt(cb.getAttribute('data-col'), 10);
                    const toggleColumn = (show) => {{
                        table.querySelectorAll('tr').forEach(tr => {{
                            const cell = tr.cells[col];
                            if (cell) cell.style.display = show ? '' : 'none';
                        }});
                    }};
                    cb.addEventListener('change', () => toggleColumn(cb.checked));
                    toggleColumn(cb.checked);
                }});
            }});
        }}
        
        // Initialize sorting, collapsible, and chart when page loads
        document.addEventListener('DOMContentLoaded', () => {{
            makeSortable();
            makeCollapsible();
            setupColumnToggles();
            try {{
                const ov = document.getElementById('overviewChart');
                if (ov) {{
                    new Chart(ov, {{
                        type: 'bar',
                        data: {{
                            labels: ['Loaded', 'Builtin', 'Unloaded'],
                            datasets: [{{
                                data: [{loadable_count}, {builtin_count}, {unloaded_count}],
                                backgroundColor: ['#1e40af','#f59e0b','#94a3b8'],
                                maxBarThickness: 18,
                                borderRadius: 4
                            }}]
                        }},
                        options: {{
                            maintainAspectRatio: false,
                            plugins: {{ legend: {{ display: false }} }},
                            scales: {{
                                y: {{ beginAtZero: true, ticks: {{ precision: 0 }} }},
                                x: {{ grid: {{ display: false }} }}
                            }},
                            layout: {{ padding: 0 }}
                        }}
                    }});
                }}
            }} catch (e) {{
                // no-op
            }}
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
            <div class="section">
                <h2>Descriptive Analysis</h2>
                <div style="display:flex; gap:16px; flex-wrap:wrap; align-items:flex-start;">
                    <div style="flex:0 0 auto; width:480px; height:240px;">
                        <h3 style="margin:0 0 8px 0; color:#0c4a6e;">Modules Overview</h3>
                        <div style="position:relative; width:100%; height:200px;">
                            <canvas id="overviewChart"></canvas>
                        </div>
                    </div>
                </div>
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
                <div class="stat-number">{self._format_size(total_size)}</div>
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
            
            {"""
            Add a privilege notice when not run as root. We only display a message; data remains as-is.
            """}
            {('<div class="notice-warning">\n'
              '  Note: Running without root privileges. Addresses of loaded kernel modules may be unavailable or masked due to restricted privileges.\n'
              '</div>') if (hasattr(os, 'geteuid') and os.geteuid() != 0) else ''}

            <div class="search-box">
                <input type="text" id="searchInput" placeholder="Search modules..." onkeyup="searchModules()">
            </div>
            
            <div class="section">
                <h2>Loadable Kernel Modules ({loadable_count})</h2>
                <div class="column-selector" data-for-table="table-loadable">
                    <span class="column-selector-label">Columns:</span>
                    <label><input type="checkbox" data-col="0" checked> Name</label>
                    <label><input type="checkbox" data-col="1" checked> Size</label>
                    <label><input type="checkbox" data-col="2" checked> Ref Count</label>
                    <label><input type="checkbox" data-col="3" checked> Dependencies</label>
                    <label><input type="checkbox" data-col="4" checked> File Path</label>
                    <label><input type="checkbox" data-col="5" checked> Description</label>
                    <label><input type="checkbox" data-col="6" checked> Address</label>
                </div>
                <table class="module-table" id="table-loadable">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Size</th>
                            <th>Ref Count</th>
                            <th>Dependencies</th>
                            <th>File Path</th>
                            <th>Description</th>
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
                            <td>{self._format_size(module.size)}</td>
                            <td>{module.ref_count}</td>
                            <td class="dependencies" title="{deps_str}">{deps_str}</td>
                            <td><code>{file_path}</code></td>
                            <td>{description}</td>
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
                    <div class="column-selector" data-for-table="table-builtin">
                        <span class="column-selector-label">Columns:</span>
                        <label><input type="checkbox" data-col="0" checked> Name</label>
                        <label><input type="checkbox" data-col="1" checked> Description</label>
                    </div>
                    <table class="module-table" id="table-builtin">
                        <thead>
                        <tr>
                            <th>Name</th>
                            <th>Description</th>
                        </tr>
                        </thead>
                        <tbody>"""
            
            for module in builtin_modules:
                html += f"""
                            <tr>
                                <td><strong>{module.name}</strong></td>
                                <td>{module.description or 'N/A'}</td>
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
                    <div class="column-selector" data-for-table="table-unloaded">
                        <span class="column-selector-label">Columns:</span>
                        <label><input type="checkbox" data-col="0" checked> Name</label>
                        <label><input type="checkbox" data-col="1" checked> Size</label>
                        <label><input type="checkbox" data-col="2" checked> File Path</label>
                        <label><input type="checkbox" data-col="3" checked> Description</label>
                    </div>
                    <table class="module-table" id="table-unloaded">
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
                                <td>{self._format_size(module['size'])}</td>
                                <td><code>{file_path}</code></td>
                                <td>{description}</td>
                            </tr>"""
            
            html += """
                        </tbody>
                    </table>
                </div>"""
        
        # Module Status Summary removed per request
        
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
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Convert bytes to human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
