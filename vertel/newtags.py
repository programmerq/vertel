#!/usr/bin/env python
import os
import sqlite3
import git
import re
from time import sleep
from tqdm import tqdm

from vertel.config import load_config


def initialize_database(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Create normalized schema
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            tag_id INTEGER PRIMARY KEY,
            tag TEXT NOT NULL UNIQUE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            file_id INTEGER PRIMARY KEY,
            file_path TEXT NOT NULL UNIQUE
        )
    ''')

    # WITHOUT ROWID table with composite primary key
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS log_trace_index (
            tag_id INTEGER NOT NULL,
            file_id INTEGER NOT NULL,
            line_number INTEGER NOT NULL,
            PRIMARY KEY (tag_id, file_id, line_number),
            FOREIGN KEY(tag_id) REFERENCES tags(tag_id),
            FOREIGN KEY(file_id) REFERENCES files(file_id)
        ) WITHOUT ROWID
    ''')

    # Create Indexes for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_log_trace_index_file_line_tag ON log_trace_index (file_id, line_number, tag_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_path ON files(file_path)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag)')

    conn.commit()
    conn.close()

def existing_tags(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    tags = [row[0] for row in cursor.execute('SELECT tag FROM tags').fetchall()]
    conn.commit()
    conn.close()
    return tags

def get_tag_id(conn, tag, tag_cache):
    """Get or create a tag_id for the given tag."""
    if tag in tag_cache:
        return tag_cache[tag]
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO tags (tag) VALUES (?)', (tag,))
    cursor.execute('SELECT tag_id FROM tags WHERE tag = ?', (tag,))
    tag_id = cursor.fetchone()[0]
    tag_cache[tag] = tag_id
    return tag_id

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

def index_repository(tag, repo_path, db_path):
    repo = git.Repo(repo_path)
    sleep(1)
    repo.git.checkout(tag)

    log_trace_patterns = [
        re.compile(r'\b[a-zA-Z_][a-zA-Z0-9_]*\.\w+\('), # Example pattern as before
    ]

    conn = sqlite3.connect(db_path)
    # Caches for tag and file ids to speed up lookups
    tag_cache = {}
    file_cache = {}

    tag_id = get_tag_id(conn, tag, tag_cache)

    pbar = tqdm(os.walk(repo_path), desc='scanning for .go files', leave=False)
    cursor = conn.cursor()
    for root, dirs, files in pbar:
        files = tqdm(files, delay=0.2, leave=False)
        for file in files:
            if file.endswith('.go'):
                files.set_description(file)
                file_path = os.path.join(root, file)
                parfile = re.sub('^.*/(?P<pardir>[^/]+?)/(?P<file>.*)$', r'\g<pardir>/\g<file>', file_path)
                rel_path = parfile.removeprefix(repo_path)
                file_id = get_file_id(conn, rel_path, file_cache)

                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    for i, line in enumerate(f, 1):
                        if any(pattern.search(line) for pattern in log_trace_patterns):
                            # Insert into log_trace_index
                            cursor.execute('INSERT OR IGNORE INTO log_trace_index (tag_id, file_id, line_number) VALUES (?, ?, ?)',
                                           (tag_id, file_id, i))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    config = load_config()

    repo_path = config["repo_path"]
    db_path = config["db_path"]

    initialize_database(db_path)
    print("initialized")
    done_tags = existing_tags(db_path)
    print(len(done_tags))

    repo = git.Repo(repo_path)
    tag_pattern = re.compile('^v1[0123456789]\.[0123456789\.]+$')
    repo_tags = [t.name for t in repo.tags if tag_pattern.match(t.name)]

    tags = [tag for tag in repo_tags if tag not in done_tags]
    if 'v11.0.0' in tags:
        tags.remove('v11.0.0')  # This tag is broken
    print("%s tags in repo. %s in db. Will index %s new tags" % (len(repo_tags), len(done_tags), len(tags)))

    tags = tqdm(tags)

    for tag in tags:
        tags.set_description(tag)
        index_repository(tag, repo_path, db_path)
