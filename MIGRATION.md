# Migration Guide

## Migrating from Git-Based to Binary-Based Analysis

If you were using the previous version of Vertel that analyzed git repository tags (specifically for Teleport), this guide will help you migrate to the new binary-based analysis system.

### Key Changes

**Old Approach (v0.1.0-git)**:
- Required a git repository checkout
- Used `vertel-newtags` to index tags from the repository
- Checked out each tag and scanned `.go` files for log patterns
- Database schema: `tags`, `files`, `log_trace_index`

**New Approach (v0.1.0+)**:
- Works directly with compiled binaries
- Uses `vertel-index` to analyze binaries
- Extracts debug information using `go tool objdump`
- Database schema: `binaries`, `files`, `log_trace_index`

### Migration Steps

1. **Save your old database** (optional):
   ```bash
   cp "$HOME/Library/Application Support/vertel/log_trace_index.db" ~/old_vertel_db_backup.db
   ```

2. **Remove old database** (required - schemas are incompatible):
   ```bash
   rm "$HOME/Library/Application Support/vertel/log_trace_index.db"
   ```

3. **Update Vertel**:
   ```bash
   cd /path/to/vertel
   git pull
   pip install --upgrade .
   ```

4. **Collect or build binaries** for each version you want to analyze:
   - Download pre-built binaries from releases
   - Or build from source for each tag:
     ```bash
     git checkout <tag>
     go build -o mybinary-<tag>
     ```

5. **Index binaries**:
   ```bash
   vertel-index /path/to/mybinary-v1.0.0 --version v1.0.0
   vertel-index /path/to/mybinary-v1.1.0 --version v1.1.0
   vertel-index /path/to/mybinary-v1.2.0 --version v1.2.0
   # ... repeat for all versions
   ```

6. **Use vertel-process as before**:
   ```bash
   cat your-log.txt | vertel-process
   ```

### Differences in Output

**Old format:**
```
Version: v15.4.3, Matched 7 Patterns: {...}
```

**New format:**
```
Binary: mybinary:v15.4.3:linux:amd64, Matched 7 Patterns: {...}
```

The new format includes:
- Binary name
- Version
- Operating system
- Architecture

### Advantages of the New Approach

1. **No Git Repository Required**: Work directly with binaries from any source
2. **Cross-Platform**: Analyze binaries built for different OS/architectures
3. **More Complete**: Includes debug info from all dependencies (not just files in the repo)
4. **Faster Setup**: No need to checkout hundreds of git tags
5. **Universal**: Works with any Go binary, not just specific projects

### Disadvantages / Trade-offs

1. **Requires Binaries**: You need access to compiled binaries for each version
2. **Storage**: Binaries take more disk space than a git repository
3. **Initial Indexing**: Takes a few minutes per binary
4. **Go Toolchain**: Requires `go tool objdump` to be available

### Automation Scripts

If you need to index many versions, consider creating a script:

```bash
#!/bin/bash
# index-all-versions.sh

BINARY_DIR="/path/to/binaries"
VERSIONS="v1.0.0 v1.1.0 v1.2.0 v1.3.0"

for version in $VERSIONS; do
    binary="${BINARY_DIR}/mybinary-${version}"
    if [ -f "$binary" ]; then
        echo "Indexing ${version}..."
        vertel-index "$binary" --version "$version"
    else
        echo "Warning: Binary not found: $binary"
    fi
done

echo "Indexing complete!"
```

### For Teleport Users

If you were using this tool specifically for Teleport:

1. Download Teleport binaries from: https://goteleport.com/download/
2. Or build from tags in the repository:
   ```bash
   cd /path/to/teleport
   for tag in v15.0.0 v15.1.0 v15.2.0; do
       git checkout $tag
       make release  # or appropriate build command
       vertel-index ./build/teleport --version $tag
   done
   ```

3. Continue using logs as before - the pattern matching works the same way

### Troubleshooting

**"Binary must contain debug information"**
- Ensure binaries are built with debug symbols (not stripped)
- Go binaries include debug info by default unless built with `-ldflags="-s -w"`

**"go tool objdump not found"**
- Install the Go toolchain
- Ensure `go` is in your PATH

**"No matches found in the log"**
- Check that your log includes file.go:line patterns
- Verify the patterns match what's in your binary
- Try: `go tool objdump /path/to/binary | grep main.go:` to see indexed patterns

### Getting Help

If you encounter issues during migration:
1. Check the README.md for updated usage instructions
2. Verify your binaries contain debug information: `file /path/to/binary`
3. Test with a simple binary first before indexing many versions

### Database Location

The database location hasn't changed:
- macOS: `$HOME/Library/Application Support/vertel/log_trace_index.db`
- Others: Check `~/.config/vertel/config.json`

However, the schema has changed, so old databases are not compatible with the new version.
