#!/Users/jeff/workspace/vertel/.venv/bin/python
import re
import sqlite3
import csv
import itertools
from tqdm import tqdm
from collections import defaultdict
from natsort import natsorted


def process_log_or_trace(log_trace, db_path):
    #pattern = re.compile(r'\b([\w/]+\.go):(\d+)\b')
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

    #matches = tqdm(matches, delay=1.0, maxinterval=1.0)
    #query = f"SELECT tag FROM log_trace_index WHERE file_path || ":" || line_number IN ( ? )";

    if matches:
        query = f"SELECT file_path, line_number, tag FROM log_trace_index WHERE {' OR '.join(['(file_path = ? AND line_number = ?)' for x in matches])}"
        #params = tuple([file_path, line_number for file_path, line_number in matches])
        #params = tuple(itertools.chain.from_iterable([(f"%{x}", str(y)) for x, y in matches]))
        params = tuple(itertools.chain.from_iterable([(f"{x}", str(y)) for x, y in matches]))
        print(query)
        print(params)
        cursor.execute(query, params)
        #file_path, line_number = match
        #matches.set_description(f"{file_path}:{line_number} ")
        #cursor.execute("SELECT tag FROM log_trace_index WHERE file_path LIKE ? AND line_number = ?",
                       #('%' + file_path, line_number))

        tags = cursor.fetchall()
        for tag in tags:
            version_counts[tag[2]] += 1
            version_details[tag[2]].add(f"{tag[0]}:{tag[1]}")

    conn.close()

    if not version_counts:
        print("No version matches found for the provided patterns.")
        return

    # Finding the most likely versions
    max_count = max([len(version_details[version]) for version in version_details.keys()])
    most_likely_versions = natsorted([version for version, count in version_counts.items() if count > max_count-1])
    most_likely_versions = natsorted([version for version in version_details.keys() if len(version_details[version]) > max_count-1][:10])


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

    # Write to CSV file
    with open(output_file, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        # Writing header (Version + all file:line patterns)
        csvwriter.writerow(['Version'] + sorted_patterns)
        # Writing data
        csvwriter.writerows(csv_data)

    print(f"CSV file '{output_file}' generated successfully.")


if __name__ == "__main__":
    db_path = '/Users/jeff/workspace/vertel/log_trace_index.db'
    import sys
    log_trace_input = sys.stdin.read()

    process_log_or_trace(log_trace_input, db_path)
