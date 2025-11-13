# Research: Short Flag for `--no-auto-log`

## Current Situation

- `--no-auto-log` has no short flag
- It disables auto-logging (which is ON by default)
- Used rarely (opt-out behavior)

## Used Short Flags

Currently taken:
- `-a` = `--append` (tee-compatible)
- `-E` = `--extended-regexp` (grep-compatible)
- `-i` = `--ignore-case` (grep-compatible)
- `-m` = `--max-count` (grep-compatible)
- `-n` = `--line-number` (grep-compatible)
- `-P` = `--perl-regexp` (grep-compatible)
- `-q` = `--quiet` (grep-compatible)
- `-t` = `--timeout` (timeout-compatible)
- `-v` = `--invert-match` (grep-compatible)

## Common Unix Patterns for "Disable" Flags

### 1. No Short Flag (Common for Negatives)

Many tools keep `--no-` options long-form only:

```bash
git commit --no-verify      # No short flag
git push --no-verify        # No short flag
npm install --no-save       # No short flag
```

**Rationale:** Disabling default behavior is the exception, not the rule.

### 2. `-n` (Dry-run/No-execute)

```bash
make -n      # Dry run (don't execute)
ssh -N       # No command
rsync -n     # Dry run
```

**Problem:** We already use `-n` for `--line-number` (grep-compatible)

### 3. Tool-Specific Patterns

| Tool | Flag | Meaning |
|------|------|---------|
| ls | `-L` | Follow symlinks (not "no") |
| grep | `-L` | Files WITHOUT match |
| tar | `-L` | Follow symlinks |
| curl | `-L` | Follow redirects |
| find | `-L` | Follow symlinks |

**Note:** `-L` commonly means "Links/Follow" in Unix

### 4. `-D` (Disable)

Not commonly used as a standalone "disable" flag in standard Unix tools.

### 5. Capital Letters for "Not"

Some tools use capitals for negation:
- Git: Uses `--no-` prefix exclusively
- Docker: Uses `--no-` prefix

## Available Options for earlyexit

### Option 1: No Short Flag ✅ **RECOMMENDED**

```bash
ee --no-auto-log npm test
```

**Pros:**
- Clear and unambiguous
- Follows git/npm convention for `--no-` options
- Disabling is rare (most users want logging)
- Doesn't consume a short flag

**Cons:**
- More typing (but rare use case)

### Option 2: `-L` (no Log)

```bash
ee -L npm test
```

**Pros:**
- Mnemonic: "L" for Log
- Short and convenient

**Cons:**
- Conflicts with Unix convention (L usually means Links/Follow)
- Could be confused with "follow Links"
- Against grep convention (`-L` = files without match)

### Option 3: `-N` (No/None)

```bash
ee -N npm test
```

**Pros:**
- Mnemonic: "N" for No
- Clear negative meaning

**Cons:**
- Not a common pattern
- Could be confused with ssh `-N` (no command)

### Option 4: `-D` (Disable)

```bash
ee -D npm test
```

**Pros:**
- Mnemonic: "D" for Disable
- Unambiguous

**Cons:**
- Not commonly used in Unix tools
- `-d` is often "debug" or "directory"

## Recommendation

### **Keep `--no-auto-log` long-form only** ✅

**Reasoning:**

1. **Follows Unix Convention**
   - Most `--no-` options don't have short flags
   - Examples: `--no-verify`, `--no-cache`, `--no-save`

2. **Rarely Needed**
   - Auto-logging is the desired default
   - Most users won't disable it
   - When they do, clarity > brevity

3. **Saves Short Flags**
   - Short flags are precious
   - Reserve them for frequently-used options
   - We might need more grep/tee-compatible flags later

4. **Clear Intent**
   - `--no-auto-log` is self-documenting
   - No ambiguity about what it does

### Alternative: Add Alias `--no-log`

If we want shorter (but still no single letter):

```bash
ee --no-log npm test  # Shorter
ee --no-auto-log npm test  # Current
```

Both could work (aliases).

## Comparison with Similar Tools

| Tool | "Disable" Option | Has Short Flag? |
|------|------------------|----------------|
| git commit | `--no-verify` | ❌ No |
| git push | `--no-verify` | ❌ No |
| npm install | `--no-save` | ❌ No |
| docker run | `--no-cache` | ❌ No |
| pytest | `--no-header` | ❌ No |
| eslint | `--no-eslintrc` | ❌ No |

**Pattern:** Modern CLI tools keep `--no-` options long-form.

## Usage Examples

### Current (No Short Flag)

```bash
# Normal use (auto-logging ON)
ee 'ERROR' npm test

# Disable logging (rare)
ee --no-auto-log 'ERROR' npm test

# Very rare, so long flag is fine
```

### If We Add Short Flag `-L`

```bash
# Normal use
ee 'ERROR' npm test

# Disable logging
ee -L 'ERROR' npm test

# But could be confused with grep -L (files without match)
```

## Decision Matrix

| Option | Clarity | Brevity | Unix Convention | Conflicts |
|--------|---------|---------|----------------|-----------|
| No short flag | ✅ | ⚠️ | ✅ | ✅ |
| `-L` | ⚠️ | ✅ | ❌ | ⚠️ (grep) |
| `-N` | ⚠️ | ✅ | ⚠️ | ⚠️ (ssh) |
| `--no-log` alias | ✅ | ✅ | ✅ | ✅ |

## Final Recommendation

1. **Primary:** Keep `--no-auto-log` with no short flag
2. **Optional:** Add alias `--no-log` for slightly shorter typing
3. **Do NOT add:** Single-letter short flag (conflicts with Unix conventions)

### Implementation

```python
# Current
parser.add_argument('--no-auto-log', action='store_true',
                   help='Disable automatic log file creation')

# With alias (optional)
parser.add_argument('--no-auto-log', '--no-log', action='store_true',
                   help='Disable automatic log file creation')
```

Then users can use either:
```bash
ee --no-auto-log npm test   # Full name (clearest)
ee --no-log npm test        # Shorter alias
```

**No single-letter flag needed** ✅

