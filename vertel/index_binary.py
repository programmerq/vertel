#!/usr/bin/env python
"""
Command to index Go binaries into the database.
"""
import os
import sqlite3
import sys
from pathlib import Path
from tqdm import tqdm

from vertel.config import load_config
from vertel.binary_analysis import analyze_binary


def initialize_database(db_path):
    """Initialize the database with the new schema for binary analysis."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create binaries table (replaces tags table)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS binaries (
            binary_id INTEGER PRIMARY KEY,
            binary_name TEXT NOT NULL,
            version TEXT,
            os TEXT NOT NULL,
            arch TEXT NOT NULL,
            go_version TEXT,
            UNIQUE(binary_name, version, os, arch)
        )
    ''')
    
    # Create files table (same as before but simpler)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            file_id INTEGER PRIMARY KEY,
            file_path TEXT NOT NULL UNIQUE
        )
    ''')
    
    # Create log_trace_index table with new schema
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS log_trace_index (
            binary_id INTEGER NOT NULL,
            file_id INTEGER NOT NULL,
            line_number INTEGER NOT NULL,
            PRIMARY KEY (binary_id, file_id, line_number),
            FOREIGN KEY(binary_id) REFERENCES binaries(binary_id),
            FOREIGN KEY(file_id) REFERENCES files(file_id)
        ) WITHOUT ROWID
    ''')
    
    # Create indexes for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_log_trace_index_file_line ON log_trace_index (file_id, line_number, binary_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_path ON files(file_path)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_binaries_name ON binaries(binary_name)')
    
    conn.commit()
    conn.close()


def get_binary_id(conn, binary_name, version, os_name, arch, go_version, binary_cache):
    """Get or create a binary_id for the given binary metadata."""
    cache_key = (binary_name, version, os_name, arch)
    if cache_key in binary_cache:
        return binary_cache[cache_key]
    
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO binaries (binary_name, version, os, arch, go_version)
        VALUES (?, ?, ?, ?, ?)
    ''', (binary_name, version, os_name, arch, go_version))
    cursor.execute('''
        SELECT binary_id FROM binaries 
        WHERE binary_name = ? AND version = ? AND os = ? AND arch = ?
    ''', (binary_name, version, os_name, arch))
    
    result = cursor.fetchone()
    if result is None:
        raise ValueError(f"Failed to create or retrieve binary_id for {binary_name}:{version}:{os_name}:{arch}")
    
    binary_id = result[0]
    binary_cache[cache_key] = binary_id
    return binary_id


def get_file_id(conn, file_path, file_cache):
    """Get or create a file_id for the given file_path."""
    if file_path in file_cache:
        return file_cache[file_path]
    
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO files (file_path) VALUES (?)', (file_path,))
    cursor.execute('SELECT file_id FROM files WHERE file_path = ?', (file_path,))
    file_id = cursor.fetchone()[0]
    file_cache[file_path] = file_id
    return file_id


def index_binary(binary_path, version, db_path):
    """
    Index a Go binary into the database.
    
    Args:
        binary_path: Path to the binary to analyze
        version: Version string for this binary (e.g., "v1.2.3")
        db_path: Path to the SQLite database
    """
    print(f"Analyzing binary: {binary_path}")
    
    # Analyze the binary
    results = analyze_binary(binary_path)
    
    if not results:
        print(f"Could not analyze binary: {binary_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    binary_cache = {}
    file_cache = {}
    
    for result in results:
        binary_name = result['binary_name']
        os_name = result['os']
        arch = result['arch']
        go_version = result['go_version']
        pairs = result['file_line_pairs']
        
        print(f"Indexing {binary_name} (version={version}, os={os_name}, arch={arch}, go={go_version})")
        print(f"Found {len(pairs)} file:line pairs")
        
        # Get or create binary_id
        binary_id = get_binary_id(conn, binary_name, version, os_name, arch, go_version, binary_cache)
        
        # Insert all file:line pairs
        cursor = conn.cursor()
        for file_path, line_number in tqdm(pairs, desc=f"Indexing {arch}", leave=False):
            file_id = get_file_id(conn, file_path, file_cache)
            cursor.execute('''
                INSERT OR IGNORE INTO log_trace_index (binary_id, file_id, line_number)
                VALUES (?, ?, ?)
            ''', (binary_id, file_id, line_number))
        
        conn.commit()
    
    conn.close()
    print(f"Successfully indexed {binary_path}")
    return True


def main():
    """Main entry point for the index-binary command."""
    import argparse
    from vertel.binary_analysis import detect_version_from_binary
    
    parser = argparse.ArgumentParser(
        description='Index a Go binary by extracting file:line debug information'
    )
    parser.add_argument('binary', help='Path to the Go binary to index')
    parser.add_argument('--version', '-v', help='Version string for this binary (e.g., v1.2.3). If not provided, will attempt to auto-detect.')
    parser.add_argument('--db', help='Path to database (overrides config)')
    
    args = parser.parse_args()
    
    # Load config
    config = load_config()
    db_path = args.db or config["db_path"]
    
    # Validate binary path
    if not os.path.exists(args.binary):
        print(f"Error: Binary not found: {args.binary}")
        sys.exit(1)
    
    if not os.access(args.binary, os.X_OK):
        print(f"Warning: Binary is not executable: {args.binary}")
    
    # Determine version
    version = args.version
    if not version:
        print("No version specified, attempting to auto-detect...")
        version = detect_version_from_binary(args.binary)
        if version:
            print(f"Auto-detected version: {version}")
        else:
            print("Error: Could not auto-detect version. Please provide --version explicitly.")
            print("Tried running binary with: version, --version, -version, -v")
            sys.exit(1)
    
    # Initialize database
    initialize_database(db_path)
    
    # Index the binary
    success = index_binary(args.binary, version, db_path)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
