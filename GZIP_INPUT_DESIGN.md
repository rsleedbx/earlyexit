# Gzip Input Support Design

## Goal

Support reading compressed input (like `zgrep`), making `ee` work seamlessly with compressed log files.

## Use Cases

```bash
# Read compressed log file
ee 'ERROR' /var/log/app.log.gz

# Pipe compressed data
zcat /var/log/app.log.gz | ee 'ERROR'

# Auto-detect compression (like zgrep)
ee -Z 'ERROR' /var/log/app.log.gz

# Multiple compression formats
ee -Z 'ERROR' /var/log/app.log.xz
ee -Z 'ERROR' /var/log/app.log.bz2
```

## grep Compatibility

### grep/zgrep Flags

```
-Z, --decompress    Force grep to behave as zgrep
-z, --decompress    (GNU grep alias)
-J, --bz2           Decompress bzip2 files
-X, --xz            Decompress xz files
--lzma              Decompress lzma files
```

### Our Current `-z` Conflict

**Problem:** We already use `-z` for `--gzip` (compress OUTPUT)

```bash
# Current behavior
ee -z 'ERROR' cmd  # Compresses OUTPUT logs
```

**Solution:** Keep `-z` for output compression, use `-Z` for input decompression (matches BSD grep)

## Proposed Implementation

### 1. Flags

```python
parser.add_argument('-Z', '--decompress', action='store_true',
                   help='Decompress input (auto-detects gzip, bzip2, xz, like zgrep)')
parser.add_argument('-J', '--bzip2', action='store_true',
                   help='Decompress bzip2 input')
parser.add_argument('-X', '--xz', action='store_true',
                   help='Decompress xz input')
```

### 2. Auto-Detection (Magic Bytes)

```python
def detect_compression(stream_or_file):
    """
    Detect compression format from magic bytes
    
    Returns: 'gzip', 'bzip2', 'xz', 'lzma', or None
    """
    # Read first few bytes
    magic = stream_or_file.peek(6) if hasattr(stream_or_file, 'peek') else b''
    
    if magic.startswith(b'\x1f\x8b'):  # gzip
        return 'gzip'
    elif magic.startswith(b'BZh'):     # bzip2
        return 'bzip2'
    elif magic.startswith(b'\xfd7zXZ\x00'):  # xz
        return 'xz'
    elif magic.startswith(b'\x5d\x00\x00'):  # lzma
        return 'lzma'
    
    return None
```

### 3. Decompression Wrapper

```python
def open_input(stream_or_path, decompress=False):
    """
    Open input stream, auto-decompressing if needed
    
    Args:
        stream_or_path: sys.stdin, file path, or file object
        decompress: Force decompression (like -Z flag)
    
    Returns:
        Text stream (decompressed if needed)
    """
    import gzip
    import bz2
    import lzma
    
    # If it's stdin, check for compression
    if stream_or_path == sys.stdin:
        if decompress:
            # Auto-detect from magic bytes
            compression = detect_compression(sys.stdin.buffer)
            if compression == 'gzip':
                return io.TextIOWrapper(gzip.GzipFile(fileobj=sys.stdin.buffer))
            elif compression == 'bzip2':
                return io.TextIOWrapper(bz2.BZ2File(sys.stdin.buffer))
            elif compression == 'xz' or compression == 'lzma':
                return io.TextIOWrapper(lzma.LZMAFile(sys.stdin.buffer))
        return sys.stdin
    
    # If it's a file path
    if isinstance(stream_or_path, str):
        # Auto-detect from extension or magic bytes
        if stream_or_path.endswith('.gz'):
            return gzip.open(stream_or_path, 'rt')
        elif stream_or_path.endswith('.bz2'):
            return bz2.open(stream_or_path, 'rt')
        elif stream_or_path.endswith(('.xz', '.lzma')):
            return lzma.open(stream_or_path, 'rt')
        else:
            return open(stream_or_path, 'r')
    
    return stream_or_path
```

### 4. Integration with Pipe Mode

```python
# In main(), pipe mode section:
if not is_command_mode:
    # Pipe mode: process stdin
    input_stream = sys.stdin
    
    # Auto-decompress if requested
    if args.decompress or args.bzip2 or args.xz:
        input_stream = open_input(sys.stdin, decompress=True)
    
    # Process stream
    process_stream(input_stream, pattern, args, ...)
```

## Examples

### Basic Usage

```bash
# Auto-detect compression from stdin
zcat /var/log/app.log.gz | ee -Z 'ERROR'

# Read compressed file directly (if we add file support)
ee -Z 'ERROR' /var/log/app.log.gz

# Specific compression format
ee -J 'ERROR' /var/log/app.log.bz2  # bzip2
ee -X 'ERROR' /var/log/app.log.xz   # xz
```

### Combined with Output Compression

```bash
# Decompress input, compress output
zcat app.log.gz | ee -Z -z --file-prefix /tmp/errors 'ERROR'
# Reads gzipped input, writes gzipped output
```

### Real-World Use Cases

```bash
# Search compressed logs
ee -Z 'ERROR' /var/log/syslog.1.gz

# Monitor compressed log rotation
tail -f /var/log/app.log.gz | ee -Z 'ERROR'

# Process old logs
for log in /var/log/*.gz; do
    ee -Z 'CRITICAL' "$log"
done
```

## Implementation Priority

### Phase 1: Pipe Mode (High Value)
```bash
zcat file.gz | ee -Z 'ERROR'
```
- ✅ Auto-detect compression from stdin
- ✅ Support gzip, bzip2, xz
- ✅ `-Z` flag

**Effort:** 30 min  
**Value:** High (works with existing workflows)

### Phase 2: File Arguments (Future)
```bash
ee -Z 'ERROR' file.gz
```
- Read files directly (not just stdin)
- Auto-detect from extension
- Multiple file support

**Effort:** 1 hour  
**Value:** Medium (nice to have)

## Compatibility Notes

### Flag Conflicts

| Flag | grep/zgrep | ee Current | ee Proposed |
|------|------------|------------|-------------|
| `-z` | Decompress input (GNU) | Compress output | **Keep as compress output** |
| `-Z` | Decompress input (BSD) | Not used | **Use for decompress input** |
| `-J` | bzip2 input | Not used | **Use for bzip2 input** |
| `-X` | xz input | Not used | **Use for xz input** |

**Decision:** Use `-Z` (BSD style) to avoid conflict with our `-z` (compress output)

### Why This Makes Sense

```bash
# Input decompression (read compressed logs)
zcat app.log.gz | ee -Z 'ERROR'

# Output compression (write compressed logs)
ee -z --file-prefix /tmp/errors 'ERROR' cmd

# Both (decompress input, compress output)
zcat app.log.gz | ee -Z -z --file-prefix /tmp/filtered 'ERROR'
```

## Dependencies

All compression formats supported by Python stdlib:
- `gzip` - Built-in
- `bz2` - Built-in
- `lzma` - Built-in (Python 3.3+)

No external dependencies needed!

## Testing

```bash
# Test gzip
echo "ERROR test" | gzip | ee -Z 'ERROR'

# Test bzip2
echo "ERROR test" | bzip2 | ee -Z 'ERROR'

# Test xz
echo "ERROR test" | xz | ee -Z 'ERROR'

# Test auto-detection
gzip -c /var/log/syslog | ee -Z 'ERROR'
```

## Documentation Updates

### USER_GUIDE.md

```markdown
Compression Options:
  -z, --gzip             Compress output logs (like tar -z)
  -Z, --decompress       Decompress input (auto-detects gzip/bzip2/xz, like zgrep)
  -J, --bzip2            Decompress bzip2 input
  -X, --xz               Decompress xz input
```

### Examples

```markdown
## Working with Compressed Logs

### Reading Compressed Input

```bash
# Auto-detect compression
zcat /var/log/app.log.gz | ee -Z 'ERROR'

# Specific format
bzcat /var/log/app.log.bz2 | ee -J 'ERROR'
xzcat /var/log/app.log.xz | ee -X 'ERROR'
```

### Compress Output

```bash
# Write compressed logs
ee -z --file-prefix /tmp/errors 'ERROR' ./app
# Creates: /tmp/errors.log.gz
```

### Both (Decompress Input, Compress Output)

```bash
zcat old.log.gz | ee -Z -z --file-prefix new 'ERROR'
# Reads compressed, writes compressed
```
```

## Benefits

1. ✅ **zgrep replacement** - Works with compressed logs
2. ✅ **No external tools** - Pure Python (gzip/bz2/lzma stdlib)
3. ✅ **Auto-detection** - Smart magic byte detection
4. ✅ **Multiple formats** - gzip, bzip2, xz, lzma
5. ✅ **Bidirectional** - Decompress input (-Z), compress output (-z)
6. ✅ **grep compatible** - Uses standard flags (-Z, -J, -X)

## Recommendation

**Implement Phase 1 (Pipe Mode) now** - 30 minutes, high value, makes `ee` a complete `zgrep` replacement.

Phase 2 (File Arguments) can wait for user demand.




