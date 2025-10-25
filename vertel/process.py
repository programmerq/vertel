#!/usr/bin/env python
import re
import sqlite3
import csv
import itertools
from tqdm import tqdm
from collections import defaultdict
from natsort import natsorted
import sys

from vertel.config import load_config


def process_log_or_trace(log_trace, db_path):
    pattern = re.compile(r'\b(\w+/\w+\.go):(\d+)')
    matches = set(pattern.findall(log_trace))

    if not matches:
        print("No matches found in the log/stack trace.")
        return

    print(f"Found {len(matches)} file.go:line pairs to consider")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    binary_counts = defaultdict(int)
    binary_details = defaultdict(set)

    # Build the query dynamically for multiple conditions:
    # (f.file_path = ? AND l.line_number = ?) OR (f.file_path = ? AND l.line_number = ?) ...
    conditions = ' OR '.join(['(f.file_path = ? AND l.line_number = ?)'] * len(matches))
    query = f"""
        SELECT f.file_path, l.line_number, b.binary_name, b.version, b.os, b.arch, b.go_version
        FROM log_trace_index l
        JOIN binaries b ON l.binary_id = b.binary_id
        JOIN files f ON l.file_id = f.file_id
        WHERE {conditions}
    """

    # Flatten parameters from matches (each match is (file_path, line_number))
    params = tuple(itertools.chain.from_iterable((fp, ln) for fp, ln in matches))

    cursor.execute(query, params)
    rows = cursor.fetchall()

    for file_path, line_number, binary_name, version, os_name, arch, go_version in rows:
        # Create a key that includes binary metadata
        key = f"{binary_name}:{version}:{os_name}:{arch}"
        binary_counts[key] += 1
        binary_details[key].add(f"{file_path}:{line_number}")

    conn.close()

    if not binary_counts:
        print("No binary matches found for the provided patterns.")
        return

    # Find the max number of matches any binary has
    max_count = max(len(p) for p in binary_details.values())
    # Get binaries with the top counts
    most_likely_binaries = natsorted([b for b, p in binary_details.items() if len(p) >= max_count])

    print("Top Binary Version Candidates:")
    for binary in most_likely_binaries:
        print(f"Binary: {binary}, Matched {len(binary_details[binary])} Patterns: {binary_details[binary]}")

    generate_csv(binary_details, "./output.csv")


def generate_csv(version_details, output_file):
    # Extract all unique file:line patterns
    all_patterns = {pattern for details in version_details.values() for pattern in details}
    sorted_patterns = sorted(all_patterns)

    # Prepare data for CSV
    csv_data = []
    for version, patterns in version_details.items():
        row = [version] + ['X' if pattern in patterns else '' for pattern in sorted_patterns]
        csv_data.append(row)

    # Write to CSV
    with open(output_file, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        # Writing header (Version + all file:line patterns)
        csvwriter.writerow(['Version'] + sorted_patterns)
        # Writing data
        csvwriter.writerows(csv_data)

    print(f"CSV file '{output_file}' generated successfully.")


def main():
    config = load_config()
    db_path = config["db_path"]
    log_trace_input = sys.stdin.read()
    process_log_or_trace(log_trace_input, db_path)


if __name__ == "__main__":
    main()
