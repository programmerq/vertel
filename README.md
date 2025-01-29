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

This started out with me wondering if I could figure out whether the reported version matched the log output. I would navigate to the file and line number in the repo and look at the log message to see if it matched up. With some guess-and-check, I could narrow down what version produced the log. This project was a way to automate this.

## Alternate Approaches

This currently depends on looking at files checked out from git. This means that line numbers that aren't in the git repository (like dependencies) won't be considered. Older versions of Teleport used to check in dependencies into the `vendor/` path, but that no longer happens.

Instead of using git, the line number information can be extracted directly from the binaries.

```
go tool objdump /path/to/binary | grep '\.go:[0-9]\+.*CALL' | awk '{print $1}' > output.txt
```

On MacOS, if you have a universal binary, you'll need to extract the specific architecture you want before passing it to `go tool objdump`:

```
% file /usr/local/bin/teleport
/usr/local/bin/teleport: Mach-O universal binary with 2 architectures: [x86_64:Mach-O 64-bit executable x86_64] [arm64]
/usr/local/bin/teleport (for architecture x86_64):	Mach-O 64-bit executable x86_64
/usr/local/bin/teleport (for architecture arm64):	Mach-O 64-bit executable arm64
% lipo -thin x86_64 -output teleport-x86_64 /usr/local/bin/teleport
% lipo -thin arm64 -output teleport-arm64 /usr/local/bin/teleport
% file teleport-arm64
teleport-arm64: Mach-O 64-bit executable arm64
% file teleport-x86_64
teleport-x86_64: Mach-O 64-bit executable x86_64
```

The `objdump` raw output takes a few minutes, and outputs 2.3 GB of raw data for one binary. The `grep '\.go:[0-9]\+.*CALL'` returns only lines that are a function call, and have a `.go` filename with line number. For example, `api.go:178021`. The `awk '{print $1}' brings it down to _only_ the filename.go:line (with no other fields). Run that through `sort | uniq`, and the output from the 2.3 GB dump is only 15 MB.


