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

    version_counts = defaultdict(int)
    version_details = defaultdict(set)

    # Build the query dynamically for multiple conditions:
    # (f.file_path = ? AND l.line_number = ?) OR (f.file_path = ? AND l.line_number = ?) ...
    conditions = ' OR '.join(['(f.file_path = ? AND l.line_number = ?)'] * len(matches))
    query = f"""
        SELECT f.file_path, l.line_number, t.tag
        FROM log_trace_index l
        JOIN tags t ON l.tag_id = t.tag_id
        JOIN files f ON l.file_id = f.file_id
        WHERE {conditions}
    """

    # Flatten parameters from matches (each match is (file_path, line_number))
    params = tuple(itertools.chain.from_iterable((fp, ln) for fp, ln in matches))

    # Debug:
    # print(query)
    # print(params)

    cursor.execute(query, params)
    rows = cursor.fetchall()

    for file_path, line_number, tag in rows:
        version_counts[tag] += 1
        version_details[tag].add(f"{file_path}:{line_number}")

    conn.close()

    if not version_counts:
        print("No version matches found for the provided patterns.")
        return

    # Find the max number of matches any version has
    max_count = max(len(p) for p in version_details.values())
    # Get versions with the top counts
    most_likely_versions = natsorted([v for v, p in version_details.items() if len(p) >= max_count])

    print("Top Version Candidates:")
    for version in most_likely_versions:
        print(f"Version: {version}, Matched {len(version_details[version])} Patterns: {version_details[version]}")

    generate_csv(version_details, "./output.csv")

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

if __name__ == "__main__":
    config = load_config()
    db_path = config["db_path"]
    log_trace_input = sys.stdin.read()
    process_log_or_trace(log_trace_input, db_path)
