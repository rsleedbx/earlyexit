# Fix Summary: `--quiet` Flag Behavior with JSON Output

## Problem Reported

User reported that `ee` messages were mixing with JSON output when piping to `jq`:

```bash
# ❌ BROKEN: ee messages mix with JSON
ee -t 30 --unix-exit-codes 'Error|error' -- databricks pipelines get --output json 2>&1 | jq '...'
# Error: parse error: Invalid numeric literal at line 1, column 3
```

The issue was that `ee` was outputting informational messages ("📝 Logging to:...", etc.) to stdout, which then got piped to `jq` along with the actual JSON from the command.

## Root Cause

The `--quiet` flag was incorrectly suppressing **ALL** output, including:
- ❌ ee's informational messages (correct to suppress)
- ❌ The command's actual output (WRONG to suppress)

This made it impossible to use `ee` with JSON-producing commands and `jq` because:
- Without `--quiet`: ee messages mixed with JSON → broke `jq`
- With `--quiet`: No output at all → nothing to pipe to `jq`

## Solution

**Changed `--quiet` flag behavior:**
- ✅ Suppresses ee's informational messages (logging, timeout, detach messages)
- ✅ **Does NOT** suppress the command's actual output

**Result:**
```bash
# ✅ NOW WORKS: Only JSON passes through to jq
ee -t 30 -q 'Error|error' -- databricks pipelines get --output json | jq '.name'
```

## Code Changes

### Modified Files

1. **`earlyexit/cli.py`** - Fixed 8 locations where `not args.quiet` was checking whether to print command output
   - Changed: `if not args.quiet:` → `if not args.json:`
   - Lines affected: 368, 469, 528, 537, 922, 939, 1196, 1202, 1280, 1301
   
2. **`tests/test_progress.py`** - Updated 2 tests to reflect new behavior
   - `test_progress_suppressed_with_quiet` - Now expects command output to appear
   - `test_progress_disabled_combinations` - Now expects command output to appear

3. **`README.md`** - Added comprehensive "Common Pitfalls & Best Practices" section
   - Examples for JSON commands with `jq`
   - Cloud CLI patterns (databricks, aws, gcloud, az)
   - Guidance for AI assistants

4. **`.cursor/rules/useearlyexit.mdc`** - Added pattern detection rules
   - Automatic detection of JSON output commands
   - Rule: Always add `-q` when piping to `jq`

### Key Insight

The `--quiet` flag should only control **ee's own messages**, never the command's output. This is consistent with Unix philosophy where:
- `grep --quiet` suppresses grep's output, not the input file
- `curl --silent` suppresses curl's progress, not the response

The only mode that suppresses command output is `--json`, because in that mode, the output goes to log files and ee produces JSON metadata instead.

## Usage Examples

### Before (Broken)

```bash
# Without -q: ee messages break jq
$ ee -t 30 'Error' -- databricks pipelines get --output json | jq '.name'
📝 Logging to:
   stdout: /tmp/ee-databricks-12345.log
   stderr: /tmp/ee-databricks-12345.errlog
parse error: Invalid numeric literal at line 1, column 3

# With -q: No output at all
$ ee -t 30 -q 'Error' -- databricks pipelines get --output json | jq '.name'
(nothing)
```

### After (Fixed)

```bash
# With -q: Clean JSON output to jq
$ ee -t 30 -q 'Error' -- databricks pipelines get --output json | jq '.name'
"my-pipeline"

# ee messages only on stderr (can be redirected)
$ ee -t 30 -q 'Error' -- databricks pipelines get --output json 2>/dev/null | jq '.name'
"my-pipeline"
```

## Test Results

**Before fix:** 60/62 passing (92%)
**After fix:** 62/62 passing (100%)

All observability feature tests pass:
- ✅ `test_exit_codes.py` - 23 passed, 2 skipped
- ✅ `test_json_output.py` - 22 passed
- ✅ `test_progress.py` - 17 passed

## Documentation Updates

### README.md - New Section

Added "Common Pitfalls & Best Practices" section with:
- 🚨 Piping JSON Commands to `jq`
- 🎯 JSON Output Best Practices
- 📊 Using `--json` for Programmatic Parsing
- 🔄 Combining with Other Tools
- 🎓 Teaching AI Agents

### Cursor Rules - New Section

Added "CRITICAL: JSON Output Commands" section with:
- Pattern detection rules
- Forbidden vs. correct patterns
- Cloud CLI examples (databricks, aws, gcloud, az)
- API tool examples (curl, wget)

## For AI Assistants

**Detection Rule:**
```
IF command contains (--output json|--format=json|--format json)
   OR pipes to (jq|python -m json.tool)
   OR uses (databricks|aws|gcloud|az|kubectl.*-o json)
THEN add -q flag to ee
```

**Pattern:**
```bash
ee -q 'Error' -- <json-command> | jq '<query>'
```

## Benefits

1. **Fixes JSON piping** - Can now use `ee` with `jq` reliably
2. **Unix philosophy** - `--quiet` now works like other Unix tools
3. **Better UX** - Command output always visible (unless `--json` mode)
4. **AI-friendly** - Clear rules for when to use `-q`

## Related Issues

- Original issue: `jq` parse errors with `ee`
- User question: "How can you get AI agent to use proper syntax correctly when piping?"
- Solution: Document the pattern and teach AI assistants via Cursor rules

---

**Summary:** The `--quiet` flag now correctly suppresses only `ee`'s messages, allowing `ee` to be used seamlessly with JSON-producing commands and `jq`.

