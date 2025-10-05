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
        writer.writerow(['Name', 'Type', 'Size', 'Ref Count', 'Status', 'Dependencies', 'Description'])
        
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
                    ''
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
                    module.description
                ])
        
        return output.getvalue()


class HTMLFormatter(BaseFormatter):
    """Formatter for HTML output with professional styling."""
    
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
        }}
        .module-table th {{
            background: #1e40af;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 500;
        }}
        .module-table td {{
            padding: 12px;
            border-bottom: 1px solid #e2e8f0;
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
        .notice-warning {{
            background: #fff7ed;
            border: 1px solid #fed7aa;
            color: #9a3412;
            padding: 12px 16px;
            border-radius: 6px;
            margin: 0 0 20px 0;
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
                <div class="stat-label">Total Modules</div>
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
                <table class="module-table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Type</th>
                            <th>Size</th>
                            <th>Ref Count</th>
                            <th>Status</th>
                            <th>Dependencies</th>
                            <th>Address</th>
                        </tr>
                    </thead>
                    <tbody>"""
        
        # Add loadable modules
        for module in modules:
            if isinstance(module, KernelModule):
                deps_str = ', '.join(module.dependencies) if module.dependencies else 'None'
                status_class = f"status-{module.status.lower()}"
                html += f"""
                        <tr>
                            <td><strong>{module.name}</strong></td>
                            <td><span class="module-type type-loadable">Loadable</span></td>
                            <td>{self._format_size(module.size)}</td>
                            <td>{module.ref_count}</td>
                            <td><span class="{status_class}">{module.status}</span></td>
                            <td class="dependencies" title="{deps_str}">{deps_str}</td>
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
                                <th>Type</th>
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
                                <td><span class="module-type type-builtin">Builtin</span></td>
                                <td>{module.description or 'N/A'}</td>
                                <td>{module.version or 'N/A'}</td>
                                <td>{module.author or 'N/A'}</td>
                                <td>{module.license or 'N/A'}</td>
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
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Convert bytes to human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
