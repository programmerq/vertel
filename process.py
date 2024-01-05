import re
import sqlite3
from collections import defaultdict


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

    for match in matches:
        file_path, line_number = match
        print(f"  Looking for {file_path}:{line_number}...")
        cursor.execute("SELECT tag FROM log_trace_index WHERE file_path LIKE ? AND line_number = ?",
                       ('%' + file_path, line_number))

        tags = cursor.fetchall()
        for tag in tags:
            version_counts[tag[0]] += 1
            version_details[tag[0]].add((file_path, line_number))

    conn.close()

    if not version_counts:
        print("No version matches found for the provided patterns.")
        return

    # Finding the most likely versions
    max_count = max(version_counts.values())
    most_likely_versions = [version for version, count in version_counts.items() if count == max_count]

    print("Most Likely Version Candidates:")
    for version in most_likely_versions:
        print(f"Version: {version}, Matched Patterns: {version_details[version]}")


if __name__ == "__main__":
    db_path = 'log_trace_index.db'  # Update this path if different
    import sys
    log_trace_input = sys.stdin.read()

    process_log_or_trace(log_trace_input, db_path)
