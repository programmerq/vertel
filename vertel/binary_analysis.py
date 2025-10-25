#!/usr/bin/env python
"""
Module for analyzing Go binaries to extract debug information.
"""
import os
import re
import subprocess
import tempfile
from pathlib import Path


def detect_binary_info(binary_path):
    """
    Detect OS, architecture, and Go version from a binary.
    
    Returns a dict with keys: os, arch, go_version, or None if detection fails.
    """
    try:
        # Use 'file' command to get basic info
        result = subprocess.run(['file', binary_path], capture_output=True, text=True, timeout=10)
        file_output = result.stdout
        
        # Detect OS
        os_name = None
        if 'Mach-O' in file_output or 'Darwin' in file_output:
            os_name = 'darwin'
        elif 'ELF' in file_output:
            os_name = 'linux'
        elif 'PE32' in file_output or 'MS Windows' in file_output:
            os_name = 'windows'
        
        # Detect architecture
        arch = None
        if 'x86-64' in file_output or 'x86_64' in file_output:
            arch = 'amd64'
        elif 'aarch64' in file_output or 'arm64' in file_output:
            arch = 'arm64'
        elif '386' in file_output or 'Intel 80386' in file_output:
            arch = '386'
        elif 'ARM' in file_output:
            arch = 'arm'
        
        # Try to get Go version using 'go version' command on the binary
        go_version = None
        try:
            go_result = subprocess.run(['go', 'version', binary_path], 
                                      capture_output=True, text=True, timeout=10)
            if go_result.returncode == 0:
                # Output format: "binary: go1.21.0"
                match = re.search(r'go(\d+\.\d+(?:\.\d+)?)', go_result.stdout)
                if match:
                    go_version = match.group(1)
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        
        if os_name and arch:
            return {
                'os': os_name,
                'arch': arch,
                'go_version': go_version
            }
    except Exception as e:
        print(f"Error detecting binary info: {e}")
    
    return None


def handle_universal_binary(binary_path, arch=None):
    """
    Handle macOS universal binaries by extracting a specific architecture.
    
    If arch is None, extracts all architectures and returns a list of temp files.
    Returns a list of (arch, temp_file_path) tuples.
    """
    result = subprocess.run(['file', binary_path], capture_output=True, text=True)
    if 'universal binary' not in result.stdout.lower():
        # Not a universal binary, return original
        return [(None, binary_path)]
    
    # Extract architectures from file output
    archs_in_binary = []
    if 'x86_64' in result.stdout:
        archs_in_binary.append('x86_64')
    if 'arm64' in result.stdout:
        archs_in_binary.append('arm64')
    
    if arch and arch not in archs_in_binary:
        print(f"Warning: Requested architecture {arch} not found in universal binary")
        return []
    
    extracted = []
    archs_to_extract = [arch] if arch else archs_in_binary
    
    for a in archs_to_extract:
        # Create temp file
        temp_fd, temp_path = tempfile.mkstemp(suffix=f'_{a}')
        os.close(temp_fd)
        
        try:
            # Use lipo to extract
            subprocess.run(['lipo', '-thin', a, '-output', temp_path, binary_path],
                         check=True, capture_output=True)
            extracted.append((a, temp_path))
        except subprocess.CalledProcessError as e:
            print(f"Warning: Could not extract {a}: {e}")
            os.unlink(temp_path)
    
    return extracted


def extract_go_file_line_pairs(binary_path):
    """
    Extract file.go:line pairs from a Go binary using go tool objdump.
    
    Returns a set of (relative_file_path, line_number) tuples.
    """
    pairs = set()
    
    try:
        # Run go tool objdump
        result = subprocess.run(['go', 'tool', 'objdump', binary_path],
                              capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            print(f"Error running objdump: {result.stderr}")
            return pairs
        
        # Pattern to match lines like: "path/to/file.go:123"
        # We're looking for .go files with line numbers
        pattern = re.compile(r'\s+([a-zA-Z0-9_/.-]+\.go):(\d+)\s')
        
        for line in result.stdout.splitlines():
            match = pattern.search(line)
            if match:
                file_path = match.group(1)
                line_number = int(match.group(2))
                pairs.add((file_path, line_number))
        
        print(f"Extracted {len(pairs)} unique file:line pairs")
        
    except subprocess.TimeoutExpired:
        print("Error: objdump timed out")
    except FileNotFoundError:
        print("Error: 'go' command not found. Make sure Go is installed and in PATH.")
    except Exception as e:
        print(f"Error extracting file:line pairs: {e}")
    
    return pairs


def analyze_binary(binary_path, arch_hint=None):
    """
    Analyze a Go binary and extract all relevant information.
    
    Args:
        binary_path: Path to the Go binary
        arch_hint: Optional architecture hint for universal binaries
    
    Returns:
        A list of dicts with keys: binary_name, version, os, arch, go_version, file_line_pairs
    """
    results = []
    binary_name = Path(binary_path).name
    
    # Check if it's a universal binary
    binaries_to_process = handle_universal_binary(binary_path, arch_hint)
    
    for arch_label, bin_path in binaries_to_process:
        try:
            # Detect binary info
            info = detect_binary_info(bin_path)
            if not info:
                print(f"Could not detect binary info for {bin_path}")
                continue
            
            # Extract file:line pairs
            pairs = extract_go_file_line_pairs(bin_path)
            
            if pairs:
                results.append({
                    'binary_name': binary_name,
                    'version': None,  # Version must be provided externally
                    'os': info['os'],
                    'arch': info['arch'] or arch_label,
                    'go_version': info['go_version'],
                    'file_line_pairs': pairs
                })
        finally:
            # Clean up temp files if we created them
            if arch_label and bin_path != binary_path:
                try:
                    os.unlink(bin_path)
                except:
                    pass
    
    return results
