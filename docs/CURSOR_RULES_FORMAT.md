# Cursor Rules Format: `.mdc` vs `.md` vs `.cursorrules`

## TL;DR

**Correct format for Cursor (discovered 2025-01-13):**
```
.cursor/
  rules/
    useearlyexit.mdc    ← Use this! (.mdc with frontmatter)
```

**Old/incorrect formats:**
```
.cursorrules             ← Doesn't work (no extension, deprecated)
.cursorrules.md          ← Doesn't work (wrong location/format)
.cursor/rules/file.md    ← Doesn't work (need .mdc, not .md)
```

---

## The Correct Format: `.mdc`

### File Location

```
project-root/
├── .cursor/
│   └── rules/
│       ├── useearlyexit.mdc      ← Main rule
│       ├── typescript-style.mdc  ← Additional rules
│       └── api-patterns.mdc      ← More rules
```

### File Structure

```markdown
---
alwaysApply: true
---

# Your Rule Title

Your rule content here in markdown...
```

### Frontmatter Options

```yaml
---
alwaysApply: true    # Apply to ALL chat interactions (recommended)
---
```

OR

```yaml
---
alwaysApply: false   # Only apply when explicitly referenced
---
```

---

## What is `.mdc`?

**MDC = Markdown with Components**

- Standard Markdown content
- YAML frontmatter for Cursor-specific configuration
- Allows Cursor to:
  - Control when rules apply (`alwaysApply`)
  - Add metadata
  - Future extensibility

---

## Format Comparison

| Format | Works? | Location | Notes |
|--------|--------|----------|-------|
| `.cursor/rules/*.mdc` | ✅ YES | `.cursor/rules/` | **CORRECT** - Use this! |
| `.cursorrules` (no ext) | ❌ NO | Project root | Deprecated/doesn't work |
| `.cursorrules.md` | ❌ NO | Project root | Wrong format |
| `.cursor/rules/*.md` | ❌ NO | `.cursor/rules/` | Need `.mdc`, not `.md` |

---

## Migration Guide

### If you have `.cursorrules` (Old Format)

```bash
# 1. Create the new directory structure
mkdir -p .cursor/rules

# 2. Create new .mdc file
cat > .cursor/rules/useearlyexit.mdc << 'EOF'
---
alwaysApply: true
---

[Your rules content from .cursorrules here]
EOF

# 3. Optional: Remove old file
rm .cursorrules
```

### Example Migration

**OLD: `.cursorrules` (Doesn't Work)**
```markdown
# My Rules

Never suggest timeout | tee without stdbuf...
```

**NEW: `.cursor/rules/useearlyexit.mdc` (Works!)**
```markdown
---
alwaysApply: true
---

# My Rules

Never suggest timeout | tee without stdbuf...
```

**Key difference:** Add frontmatter and use `.mdc` extension in `.cursor/rules/` directory.

---

## Multiple Rules

You can have multiple `.mdc` files for different purposes:

```
.cursor/
  rules/
    useearlyexit.mdc        ← Shell command rules
    typescript-style.mdc    ← TypeScript coding standards
    api-conventions.mdc     ← API design patterns
    security.mdc            ← Security best practices
```

Each file can have its own `alwaysApply` setting.

---

## Testing Your Rules

### 1. Verify File Structure

```bash
ls -la .cursor/rules/
# Should show: useearlyexit.mdc

cat .cursor/rules/useearlyexit.mdc
# Should show frontmatter (---) at top
```

### 2. Check in Cursor

1. Open Cursor
2. Go to Settings → Cursor Settings → Rules
3. Look under "Project Rules"
4. You should see your rule file(s) listed

### 3. Test with Prompt

Ask Cursor: "How do I run terraform apply with a timeout and save output?"

**Good response (rules working):**
```bash
ee -t 600 'Error' terraform apply
```

**Bad response (rules not working):**
```bash
timeout 600 terraform apply 2>&1 | tee /tmp/terraform.log
```

---

## Common Mistakes

### Mistake 1: Wrong File Extension

```bash
# ❌ WRONG - uses .md instead of .mdc
.cursor/rules/useearlyexit.md

# ✅ CORRECT - uses .mdc
.cursor/rules/useearlyexit.mdc
```

### Mistake 2: Missing Frontmatter

```markdown
❌ WRONG - no frontmatter

# My Rules
Content here...
```

```markdown
✅ CORRECT - has frontmatter

---
alwaysApply: true
---

# My Rules
Content here...
```

### Mistake 3: Wrong Directory

```bash
# ❌ WRONG - wrong location
.cursorrules
.cursor/useearlyexit.mdc

# ✅ CORRECT - right location
.cursor/rules/useearlyexit.mdc
```

---

## Why This Matters

### Before (Incorrect Format)

User creates `.cursorrules` (no extension):
- Cursor doesn't recognize it
- Rules don't apply
- AI continues suggesting broken patterns
- User frustrated

### After (Correct Format)

User creates `.cursor/rules/useearlyexit.mdc`:
- Cursor recognizes it
- Rules apply to all interactions (`alwaysApply: true`)
- AI suggests correct patterns
- User happy!

---

## Advanced: Conditional Rules

You can create rules that only apply in certain contexts:

```markdown
---
alwaysApply: false
---

# Experimental Feature Rules

Only use when user explicitly asks for experimental features...
```

Then reference it explicitly in your prompt:
> "Using the experimental-features rule, show me..."

---

## earlyexit Project Structure

**Current structure (correct):**
```
earlyexit/
├── .cursor/
│   └── rules/
│       └── useearlyexit.mdc    ✅ Active rule
├── .cursorrules                ⚠️ Deprecated (can be removed)
├── docs/
│   ├── CURSOR_RULES_TEMPLATE.md    ← Updated to show .mdc format
│   └── CURSOR_RULES_FORMAT.md      ← This file!
```

---

## For Other Projects

### Quick Setup

```bash
# Copy the earlyexit rule to your project
mkdir -p .cursor/rules
cp /path/to/earlyexit/.cursor/rules/useearlyexit.mdc .cursor/rules/
```

### Customize

Edit `.cursor/rules/useearlyexit.mdc` to add your project-specific patterns.

---

## References

- **Cursor Settings:** Settings → Cursor Settings → Rules
- **Docs:** Click "Docs" link in Cursor Settings for official documentation
- **earlyexit Template:** `docs/CURSOR_RULES_TEMPLATE.md`

---

## Summary

| Question | Answer |
|----------|--------|
| **What format?** | `.mdc` (Markdown with frontmatter) |
| **Where?** | `.cursor/rules/` directory |
| **Extension?** | `.mdc` (NOT `.md`, NOT no extension) |
| **Frontmatter?** | Required (`alwaysApply: true` recommended) |
| **Multiple files?** | Yes, create multiple `.mdc` files |
| **Old `.cursorrules`?** | Deprecated, doesn't work |

---

**Bottom line:** Use `.cursor/rules/*.mdc` with frontmatter. Everything else doesn't work! ✅

