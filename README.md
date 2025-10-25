# Vertel - Go Binary Version Detector

This project automates the process of checking Go binary logs to determine the version and build that produced them. It works by extracting debug information directly from compiled Go binaries and matching log patterns against a database of known file:line mappings.

## Overview

Vertel analyzes compiled Go binaries (across different OS, architecture, and Go versions) to extract file path and line number information embedded in the binary's debug data. This information is stored in a SQLite database and can be queried to identify which binary version produced a given log output.

## Features

- **Universal Binary Support**: Works with any Go binary, not just specific projects
- **Multi-Platform**: Handles Linux, macOS (including universal binaries), and Windows binaries
- **Multi-Architecture**: Supports amd64, arm64, 386, and arm architectures
- **Static Analysis**: Extracts information directly from binaries without execution
- **Efficient Storage**: Uses normalized SQLite database with optimized indexes
- **Fast Matching**: Quickly identifies binary versions from log patterns

## Installation

Use any Python environment you'd like. A virtualenv is recommended:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install .
```

This will create two scripts in your PATH:

* `vertel-index` - Index a Go binary into the database
* `vertel-process` - Match log patterns against the database

## Usage

### Indexing Binaries

First, you need to index one or more Go binaries. For each binary, you should provide a version identifier:

```bash
# Index a binary with a version tag
vertel-index /path/to/mybinary --version v1.2.3

# Index multiple versions
vertel-index /path/to/mybinary-v1.0.0 --version v1.0.0
vertel-index /path/to/mybinary-v1.1.0 --version v1.1.0
vertel-index /path/to/mybinary-v1.2.0 --version v1.2.0
```

The tool will:
1. Detect the OS, architecture, and Go version used to build the binary
2. Handle macOS universal binaries by extracting each architecture separately
3. Use `go tool objdump` to extract all file.go:linenumber pairs
4. Store this information in a SQLite database at `~/Library/Application Support/vertel/log_trace_index.db`

**Note**: The indexing process can take a few minutes per binary and requires the `go` toolchain to be installed.

### Version Detection

Once you have indexed binaries, you can analyze logs to determine which version produced them:

```bash
cat your-log-file.txt | vertel-process
```

Example output:

```
Found 8 file.go:line pairs to consider
Top Binary Version Candidates:
Binary: mybinary:v1.2.3:linux:amd64, Matched 7 Patterns: {'service/signals.go:249', 'service/service.go:6216', ...}
Binary: mybinary:v1.2.4:linux:amd64, Matched 7 Patterns: {'service/signals.go:249', 'service/service.go:6216', ...}
CSV file './output.csv' generated successfully.
```

The tool:
- Extracts file.go:line patterns from the log input
- Queries the database for matching binaries
- Ranks results by the number of matched patterns
- Generates a CSV file showing which patterns matched which binaries

## Database Location

By default, the database is stored at:
- macOS: `~/Library/Application Support/vertel/log_trace_index.db`
- Linux/Windows: `~/.config/vertel/log_trace_index.db` (configurable)

You can override this with the `--db` option:

```bash
vertel-index /path/to/binary --version v1.0.0 --db /custom/path/database.db
```

## How It Works

### Binary Analysis

Go binaries contain embedded debug information that maps machine code back to source files and line numbers. Vertel uses `go tool objdump` to extract this information:

1. **Detection**: Uses the `file` command to detect OS and architecture
2. **Go Version**: Extracts Go version using `go version <binary>`
3. **Universal Binary Handling**: For macOS universal binaries, uses `lipo` to extract individual architectures
4. **Debug Info Extraction**: Runs `go tool objdump` and parses output for .go file references
5. **Storage**: Stores extracted patterns in a normalized SQLite schema

### Database Schema

The database uses a normalized schema for efficient storage:

- **binaries**: Stores binary metadata (name, version, OS, arch, Go version)
- **files**: Stores unique file paths
- **log_trace_index**: Maps binaries to file:line pairs (composite primary key, WITHOUT ROWID)

This design optimizes for:
- Small database size (file paths stored once, referenced by ID)
- Fast lookups (indexed on common query patterns)
- Easy binary version comparison

### Log Pattern Matching

When processing logs:
1. Extract all file.go:line patterns using regex
2. Query database for binaries containing those patterns
3. Rank by number of matches
4. Present top candidates with detailed pattern lists

## Requirements

- Python 3.7+
- Go toolchain (for `go tool objdump` and `go version`)
- `file` command (usually pre-installed on Unix systems)
- `lipo` command (for macOS universal binaries, pre-installed on macOS)

## Limitations

- Requires Go toolchain to be installed
- Binary must contain debug information (not stripped)
- Indexing is CPU and disk intensive (several minutes per binary)
- Database size grows with number of binaries indexed

## Tips

- Index multiple versions of the same binary to compare across releases
- Use meaningful version strings (e.g., semver tags like v1.2.3)
- For large deployments, consider maintaining a central database
- The CSV output helps visualize which patterns are unique to certain versions

## Background

This tool generalizes the concept of version detection from log patterns. Many Go applications include file path and line number information in their logs (e.g., using `log.Printf` with caller information). This information is already embedded in the compiled binary and can be extracted for matching purposes.

This approach works because:
- Go binaries contain debug information by default
- The `go tool objdump` can extract this information
- File paths and line numbers are stable identifiers for code locations
- Logs often include this information when errors or significant events occur

## See Also

- [AGENTS.md](AGENTS.md) - Information about AI agents working on this project
- [Go objdump documentation](https://pkg.go.dev/cmd/objdump)

## Migration from Previous Versions

If you were using an older version of Vertel that worked with git repositories, see [MIGRATION.md](MIGRATION.md) for detailed migration instructions.
