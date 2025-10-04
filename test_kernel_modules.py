#!/usr/bin/env python3
"""
Unit tests for the kernel module lister script.

This module tests the functionality of list_kernel_modules.py by comparing
its output against the standard lsmod command to ensure consistency.
"""

import unittest
import subprocess
import sys
import os
from typing import List, Dict, Set
import tempfile
import io
from contextlib import redirect_stdout

# Import our module
from list_kernel_modules import parse_proc_modules, KernelModule, format_size


class TestKernelModuleLister(unittest.TestCase):
    """Test cases for the kernel module lister functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.maxDiff = None  # Show full diff on assertion failures
        
    def test_parse_proc_modules_basic(self):
        """Test basic parsing of /proc/modules."""
        modules = parse_proc_modules()
        
        # Should return a list
        self.assertIsInstance(modules, list)
        
        # Should have at least some modules
        self.assertGreater(len(modules), 0)
        
        # All items should be KernelModule instances
        for module in modules:
            self.assertIsInstance(module, KernelModule)
            self.assertIsInstance(module.name, str)
            self.assertIsInstance(module.size, int)
            self.assertIsInstance(module.ref_count, int)
            self.assertIsInstance(module.dependencies, list)
            self.assertIsInstance(module.status, str)
            self.assertIsInstance(module.address, str)
            
            # Basic validation
            self.assertGreater(len(module.name), 0)
            self.assertGreaterEqual(module.size, 0)
            self.assertGreaterEqual(module.ref_count, 0)
            self.assertGreater(len(module.status), 0)
            self.assertGreater(len(module.address), 0)
    
    def test_format_size(self):
        """Test the size formatting function."""
        test_cases = [
            (1024, "1.0 KB"),
            (1536, "1.5 KB"),
            (1048576, "1.0 MB"),
            (1073741824, "1.0 GB"),
            (512, "512.0 B"),
            (0, "0.0 B"),
        ]
        
        for size_bytes, expected in test_cases:
            with self.subTest(size=size_bytes):
                result = format_size(size_bytes)
                self.assertEqual(result, expected)
    
    def test_module_names_match_lsmod(self):
        """Test that module names match between our script and lsmod."""
        # Get modules from our script
        our_modules = parse_proc_modules()
        our_names = {module.name for module in our_modules}
        
        # Get modules from lsmod
        lsmod_names = self._get_lsmod_module_names()
        
        # Module names should match exactly
        self.assertEqual(our_names, lsmod_names, 
                        "Module names should match between our script and lsmod")
    
    def test_module_sizes_match_lsmod(self):
        """Test that module sizes match between our script and lsmod."""
        # Get modules from our script
        our_modules = parse_proc_modules()
        our_sizes = {module.name: module.size for module in our_modules}
        
        # Get modules from lsmod
        lsmod_sizes = self._get_lsmod_module_sizes()
        
        # Sizes should match
        for name in our_sizes:
            with self.subTest(module=name):
                self.assertEqual(our_sizes[name], lsmod_sizes[name],
                               f"Size mismatch for module {name}")
    
    def test_module_ref_counts_match_lsmod(self):
        """Test that reference counts match between our script and lsmod."""
        # Get modules from our script
        our_modules = parse_proc_modules()
        our_ref_counts = {module.name: module.ref_count for module in our_modules}
        
        # Get modules from lsmod
        lsmod_ref_counts = self._get_lsmod_ref_counts()
        
        # Reference counts should match
        for name in our_ref_counts:
            with self.subTest(module=name):
                self.assertEqual(our_ref_counts[name], lsmod_ref_counts[name],
                               f"Reference count mismatch for module {name}")
    
    def test_module_dependencies_match_lsmod(self):
        """Test that module dependencies match between our script and lsmod."""
        # Get modules from our script
        our_modules = parse_proc_modules()
        our_deps = {module.name: set(module.dependencies) for module in our_modules}
        
        # Get modules from lsmod
        lsmod_deps = self._get_lsmod_dependencies()
        
        # Dependencies should match
        for name in our_deps:
            with self.subTest(module=name):
                self.assertEqual(our_deps[name], lsmod_deps[name],
                               f"Dependencies mismatch for module {name}")
    
    def test_script_output_format(self):
        """Test that the script produces properly formatted output."""
        # Capture stdout
        f = io.StringIO()
        with redirect_stdout(f):
            from list_kernel_modules import display_modules
            modules = parse_proc_modules()
            display_modules(modules, show_details=False)
        
        output = f.getvalue()
        
        # Should contain expected headers
        self.assertIn("Loaded Kernel Modules", output)
        self.assertIn("Module Name", output)
        self.assertIn("Size", output)
        self.assertIn("Ref Count", output)
        self.assertIn("Status", output)
        
        # Should contain some module data
        self.assertIn("Live", output)
    
    def test_script_detailed_output_format(self):
        """Test that the script produces properly formatted detailed output."""
        # Capture stdout
        f = io.StringIO()
        with redirect_stdout(f):
            from list_kernel_modules import display_modules
            modules = parse_proc_modules()
            display_modules(modules, show_details=True)
        
        output = f.getvalue()
        
        # Should contain expected headers
        self.assertIn("Loaded Kernel Modules", output)
        self.assertIn("Module:", output)
        self.assertIn("Size:", output)
        self.assertIn("Reference Count:", output)
        self.assertIn("Dependencies:", output)
        self.assertIn("Status:", output)
        self.assertIn("Address:", output)
    
    def test_count_option(self):
        """Test that the --count option works correctly."""
        # Run the script with --count option
        result = subprocess.run([
            sys.executable, 'list_kernel_modules.py', '--count'
        ], capture_output=True, text=True, cwd=os.path.dirname(__file__))
        
        self.assertEqual(result.returncode, 0)
        
        # Should output a count
        output = result.stdout.strip()
        self.assertTrue(output.startswith("Total loaded kernel modules:"))
        
        # Extract the number and verify it matches our parsing
        count_str = output.split(":")[1].strip()
        count = int(count_str)
        
        our_modules = parse_proc_modules()
        self.assertEqual(count, len(our_modules))
    
    def test_help_option(self):
        """Test that the --help option works correctly."""
        result = subprocess.run([
            sys.executable, 'list_kernel_modules.py', '--help'
        ], capture_output=True, text=True, cwd=os.path.dirname(__file__))
        
        self.assertEqual(result.returncode, 0)
        
        # Should contain help text
        self.assertIn("List all loaded kernel modules", result.stdout)
        self.assertIn("--detailed", result.stdout)
        self.assertIn("--count", result.stdout)
    
    def _get_lsmod_module_names(self) -> Set[str]:
        """Get module names from lsmod command."""
        try:
            result = subprocess.run(['lsmod'], capture_output=True, text=True, check=True)
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            names = set()
            for line in lines:
                if line.strip():
                    name = line.split()[0]
                    names.add(name)
            return names
        except subprocess.CalledProcessError:
            self.skipTest("lsmod command not available")
    
    def _get_lsmod_module_sizes(self) -> Dict[str, int]:
        """Get module sizes from lsmod command."""
        try:
            result = subprocess.run(['lsmod'], capture_output=True, text=True, check=True)
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            sizes = {}
            for line in lines:
                if line.strip():
                    parts = line.split()
                    name = parts[0]
                    size = int(parts[1])
                    sizes[name] = size
            return sizes
        except subprocess.CalledProcessError:
            self.skipTest("lsmod command not available")
    
    def _get_lsmod_ref_counts(self) -> Dict[str, int]:
        """Get reference counts from lsmod command."""
        try:
            result = subprocess.run(['lsmod'], capture_output=True, text=True, check=True)
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            ref_counts = {}
            for line in lines:
                if line.strip():
                    parts = line.split()
                    name = parts[0]
                    ref_count = int(parts[2])
                    ref_counts[name] = ref_count
            return ref_counts
        except subprocess.CalledProcessError:
            self.skipTest("lsmod command not available")
    
    def _get_lsmod_dependencies(self) -> Dict[str, Set[str]]:
        """Get module dependencies from lsmod command."""
        try:
            result = subprocess.run(['lsmod'], capture_output=True, text=True, check=True)
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            dependencies = {}
            for line in lines:
                if line.strip():
                    parts = line.split()
                    name = parts[0]
                    # Dependencies are in the "Used by" column (index 3+)
                    if len(parts) > 3:
                        deps_str = ' '.join(parts[3:])
                        deps = set(deps_str.split(',')) if deps_str else set()
                        # Remove empty strings and status markers
                        deps = {dep.strip() for dep in deps if dep.strip() and not dep.strip().startswith('[')}
                    else:
                        deps = set()
                    dependencies[name] = deps
            return dependencies
        except subprocess.CalledProcessError:
            self.skipTest("lsmod command not available")


class TestIntegration(unittest.TestCase):
    """Integration tests comparing full output."""
    
    def test_full_output_consistency(self):
        """Test that our script output is consistent with lsmod."""
        # Get our script output
        our_result = subprocess.run([
            sys.executable, 'list_kernel_modules.py'
        ], capture_output=True, text=True, cwd=os.path.dirname(__file__))
        
        self.assertEqual(our_result.returncode, 0)
        
        # Get lsmod output
        lsmod_result = subprocess.run(['lsmod'], capture_output=True, text=True)
        
        if lsmod_result.returncode != 0:
            self.skipTest("lsmod command not available")
        
        # Parse both outputs
        our_modules = self._parse_our_output(our_result.stdout)
        lsmod_modules = self._parse_lsmod_output(lsmod_result.stdout)
        
        # Should have same number of modules
        self.assertEqual(len(our_modules), len(lsmod_modules))
        
        # All modules should match
        for name in our_modules:
            with self.subTest(module=name):
                self.assertIn(name, lsmod_modules)
                our_mod = our_modules[name]
                lsmod_mod = lsmod_modules[name]
                
                self.assertEqual(our_mod['size'], lsmod_mod['size'])
                self.assertEqual(our_mod['ref_count'], lsmod_mod['ref_count'])
                # Skip dependency comparison for simple output format since it doesn't show dependencies
                # self.assertEqual(our_mod['dependencies'], lsmod_mod['dependencies'])
    
    def _parse_our_output(self, output: str) -> Dict[str, Dict]:
        """Parse our script's output into a structured format."""
        modules = {}
        lines = output.strip().split('\n')
        
        # Skip header lines
        data_lines = []
        in_data = False
        for line in lines:
            if line.startswith('Module Name'):
                in_data = True
                continue
            elif line.startswith('-'):
                continue
            elif in_data and line.strip():
                data_lines.append(line)
        
        for line in data_lines:
            parts = line.split()
            if len(parts) >= 4:
                name = parts[0]
                size_str = parts[1] + ' ' + parts[2]  # Size and unit are separate
                ref_count = int(parts[3])
                status = parts[4]
                
                # Convert size back to bytes
                size = self._parse_size_to_bytes(size_str)
                
                modules[name] = {
                    'size': size,
                    'ref_count': ref_count,
                    'status': status,
                    'dependencies': set()  # Not shown in simple output
                }
        
        return modules
    
    def _parse_lsmod_output(self, output: str) -> Dict[str, Dict]:
        """Parse lsmod output into a structured format."""
        modules = {}
        lines = output.strip().split('\n')[1:]  # Skip header
        
        for line in lines:
            if line.strip():
                parts = line.split()
                name = parts[0]
                size = int(parts[1])
                ref_count = int(parts[2])
                
                # Dependencies are in the "Used by" column
                if len(parts) > 3:
                    deps_str = ' '.join(parts[3:])
                    deps = set(deps_str.split(',')) if deps_str else set()
                    # Remove empty strings and status markers
                    deps = {dep.strip() for dep in deps if dep.strip() and not dep.strip().startswith('[')}
                else:
                    deps = set()
                
                modules[name] = {
                    'size': size,
                    'ref_count': ref_count,
                    'dependencies': deps
                }
        
        return modules
    
    def _parse_size_to_bytes(self, size_str: str) -> int:
        """Convert human-readable size back to bytes."""
        size_str = size_str.upper()
        if size_str.endswith(' B'):
            return int(float(size_str[:-2]))
        elif size_str.endswith(' KB'):
            return int(float(size_str[:-3]) * 1024)
        elif size_str.endswith(' MB'):
            return int(float(size_str[:-3]) * 1024 * 1024)
        elif size_str.endswith(' GB'):
            return int(float(size_str[:-3]) * 1024 * 1024 * 1024)
        else:
            return int(float(size_str))


if __name__ == '__main__':
    # Set up test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestKernelModuleLister))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
