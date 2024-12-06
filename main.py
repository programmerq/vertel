#!/Users/jeff/workspace/vertel/.venv/bin/python
import os
import sqlite3
import git
import re
from time import sleep
from tqdm import tqdm


def initialize_database(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS log_trace_index (
                        id INTEGER PRIMARY KEY,
                        tag TEXT,
                        file_path TEXT,
                        line_number INTEGER,
                        UNIQUE(tag, file_path, line_number))''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_file_line_tag ON log_trace_index (file_path, line_number, tag)''')
    conn.commit()
    conn.close()

def existing_tags(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    tags = [row[0] for row in cursor.execute('select distinct tag from log_trace_index').fetchall()]
    conn.commit()
    conn.close()
    return tags

#def initialize_database(db_path):
#    conn = sqlite3.connect(db_path)
#    cursor = conn.cursor()
#    cursor.execute('''CREATE TABLE IF NOT EXISTS log_trace_index (
#                        id INTEGER PRIMARY KEY,
#                        tag TEXT,
#                        file_path TEXT,
#                        line_number INTEGER,
#                        content TEXT)''')
#    conn.commit()
#    conn.close()

def index_repository(tag, repo_path, db_path):
    repo = git.Repo(repo_path)
    sleep(1)
    repo.git.checkout(tag)

    log_trace_patterns = [
        re.compile(r'\b[a-zA-Z_][a-zA-Z0-9_]*\.\w+\('), # Function definitions
    ]

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    pbar = tqdm(os.walk(repo_path), desc='scanning for .go files', leave=False)
    for root, dirs, files in pbar:
        files = tqdm(files, delay=0.2, leave=False)
        for file in files:
            if file.endswith('.go'):
                files.set_description(file)
                file_path = os.path.join(root, file)

                # do parent_dir/file.ext to avoid bloating the db.
                parfile = re.sub('^.*/(?P<pardir>[^/]+?)/(?P<file>.*)$', '\g<pardir>/\g<file>', file_path)
                with open(file_path, 'r') as f:
                    for i, line in enumerate(f, 1):
                        if any(pattern.search(line) for pattern in log_trace_patterns):
                            cursor.execute("INSERT OR REPLACE INTO log_trace_index (tag, file_path, line_number) VALUES (?, ?, ?)",
                                           (tag, parfile.removeprefix(repo_path), i))
                                           #(tag, file_path.removeprefix(repo_path), i)) # full repo path
    conn.commit()
    conn.close()

if __name__ == "__main__":
    db_path = 'log_trace_index.db'
    repo_path = '/Users/jeff/workspace/teleport/'  # Update this path

    initialize_database(db_path)
    print("initialized")
    done_tags = existing_tags(db_path)
    print(len(done_tags))

    repo = git.Repo(repo_path)
    tag_pattern = re.compile('^v1[0123456789]\.[0123456789\.]+$')
    repo_tags = [t.name for t in repo.tags if tag_pattern.match(t.name)]

    tags = [tag for tag in repo_tags if tag not in done_tags]
    if 'v11.0.0' in tags: tags.remove('v11.0.0')  # This tag is broken
    print("%s tags in repo. %s in db. Will index %s new tags" % (len(repo_tags), len(done_tags), len(tags)))

    tags = tqdm(tags)

    for tag in tags:
      tags.set_description(tag)
      index_repository(tag, repo_path, db_path)
