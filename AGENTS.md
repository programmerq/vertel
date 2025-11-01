# AGENTS.md

## AI Agent Development Notes

This document tracks the work done by AI agents on the Vertel project.

### Project Transformation (October 2025)

**Task**: Generalize from Teleport-specific to universal Go binary analyzer

**Agent**: GitHub Copilot Coding Agent

**Changes Made**:

1. **Removed Git Dependency**
   - Eliminated requirement for git repository checkout
   - Removed GitPython dependency
   - Simplified configuration (no longer needs repo_path)

2. **Created Binary Analysis Module** (`binary_analysis.py`)
   - Detects binary OS, architecture, and Go version using `file` command
   - Extracts Go version using `go version` command
   - Handles macOS universal binaries with `lipo` extraction
   - Uses `go tool objdump` to extract file:line pairs from binary debug info
   - Returns structured data about binary metadata and embedded source locations

3. **Updated Database Schema**
   - Replaced `tags` table with `binaries` table
   - Added columns: binary_name, version, os, arch, go_version
   - Maintained normalized structure for efficient storage
   - Updated indexes for optimal query performance

4. **Created New Indexing Command** (`index_binary.py`)
   - Replaced `vertel-newtags` with `vertel-index`
   - Accepts binary path and version as arguments
   - Automatically detects binary properties
   - Handles multi-architecture binaries
   - Stores results in SQLite database

5. **Updated Processing Command** (`process.py`)
   - Modified to work with new database schema
   - Now returns binary:version:os:arch format
   - Maintains backward compatibility in workflow

6. **Updated Documentation**
   - Rewrote README.md with new usage patterns
   - Added comprehensive how-it-works section
   - Documented requirements and limitations
   - Created this AGENTS.md file

**Design Decisions**:

- **Static Analysis Approach**: Using `go tool objdump` instead of runtime analysis provides several benefits:
  - Works without executing potentially untrusted binaries
  - Can analyze binaries from any platform
  - Extracts complete debug information in one pass

- **Schema Optimization**: The normalized database schema balances:
  - Storage efficiency (file paths stored once)
  - Query performance (indexed on common patterns)
  - Flexibility (supports multiple binary versions/architectures)

- **Universal Binary Support**: macOS universal binaries contain multiple architectures. The tool automatically extracts and indexes each architecture separately, allowing precise matching based on the actual architecture that produced the logs.

**Technical Challenges Addressed**:

1. **Binary Format Detection**: Different platforms use different executable formats (Mach-O, ELF, PE32). Used the `file` command as a universal detector.

2. **Go Version Extraction**: The `go version` command can read embedded build info from Go 1.18+ binaries.

3. **objdump Parsing**: The output format varies slightly. Used regex patterns that work across Go versions.

4. **Temporary File Management**: For universal binary extraction, implemented proper cleanup of temporary files.

**Future Improvements**:

- Add support for stripped binaries (extract partial information)
- Parallel processing for faster indexing of multiple binaries
- Web interface for easier querying
- Binary comparison tools (diff between versions)
- Support for vendored dependencies (extract vendor paths)

**Testing Notes**:

- No existing test infrastructure in the project
- Manual testing required for:
  - Binary indexing across different Go versions
  - Universal binary handling on macOS
  - Cross-platform binary analysis
  - Log pattern matching accuracy

**Migration from Old Version**:

Users of the old Teleport-specific version can migrate by:
1. Building or downloading binaries for each Teleport version
2. Running `vertel-index` on each binary with appropriate version tags
3. Using `vertel-process` as before (output format slightly different)

The database schema is incompatible with the old version (tags vs binaries), so a fresh database is required.
