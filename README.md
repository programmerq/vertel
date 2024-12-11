# Teleport Version Checker

This project automates the process of checking a Teleport log's signature to determine the version that produced it.


## Installation

Use any python environment you'd like. I prefer a virtualenv, but it isn't strictly necessary.

```
% pip install .
```

This will create two scripts in your PATH:

* `vertel-newtags`
* `vertel-process`

## Usage

### Tag Importing

First, you'll need a git checkout of teleport.

The first time you invoke either command, it will ask for a path to the
checkout. Enter it, and the script will make sure the path is a valid git repo.
The repo should be clean, so `git stash` any changes before running.

```
% vertel-newtags
```

This will list all tags from 10.0.0 and newer. It uses a regex to only consider semver compliant tags that don't include letters after the initial `v`. This will build an SQLITE database with all the tag information. It stores that in `~/Library/Application Support/vertel/log_trace_index.db`. Note that this takes up about 1.3 GiB as of v17.0.4 on Wed Dec 11 2024.

There are some tags it filters out: v11.0.0 is broken. v999.* is ignored too.

If the git library returns an error, you may need to inspect the repository and 'git stash' or otherwise clean it up. There are several changes to the codebase over time, and it's possible for checkouts to cause conflicts. Make sure you don't have this git checkout loaded in any IDE that will rescan the working directory.

This script doesn't do any `git fetch`, and expects you'll have done that already.

Make sure you fetch tags:

```
% git fetch ... --tags
```

Tip: add `teleport-private` as a second origin to pull in tags from that repo too (enterprise-only security tags only appear there)

I usually do `git fetch -a --all --tags` to fetch all origins and all tags.

### Version Detection

```
% cat logtoconsider.txt | vertel-process
Found 8 file.go:line pairs to consider
Top Version Candidates:
Version: v15.4.3, Matched 7 Patterns: {'service/signals.go:249', 'service/service.go:6216', 'upgradewindow/upgradewindow.go:298', 'service/connect.go:464', 'service/service.go:971', 'join/join.go:253', 'labels/cloud.go:153'}
Version: v15.4.4, Matched 7 Patterns: {'service/signals.go:249', 'service/service.go:6216', 'upgradewindow/upgradewindow.go:298', 'service/connect.go:464', 'service/service.go:971', 'join/join.go:253', 'labels/cloud.go:153'}
CSV file './output.csv' generated successfully.
```

The `./output.csv` always goes to the current directory. It lists all tags and
all patterns. It puts an X for matches, and nothing for non-matches. This helps
visually identify the candidates (helpful in some cases)

## Background

This started out with me wondering 
