# earlyexit Regex Reference

Complete guide to pattern matching in earlyexit.

## Table of Contents

1. [Regex Engine Selection](#regex-engine-selection)
2. [Python Extended Regex (Default)](#python-extended-regex-default)
3. [Perl-Compatible Regex (-P)](#perl-compatible-regex--p)
4. [Common Patterns](#common-patterns)
5. [Best Practices](#best-practices)
6. [Examples](#examples)

## Regex Engine Selection

earlyexit supports two regex engines:

| Flag | Engine | Module | Installation |
|------|--------|--------|--------------|
| *(default)* | Python Extended | `re` | Built-in |
| `-E, --extended-regexp` | Python Extended | `re` | Built-in |
| `-P, --perl-regexp` | Perl-Compatible | `regex` | `pip install regex` |

### Usage

```bash
# Default Python regex
earlyexit 'ERROR' ./app

# Explicit Python regex (same as default)
earlyexit -E 'ERROR' ./app

# Perl-compatible regex (advanced)
earlyexit -P '(?<=ERROR: ).*' ./app
```

## Python Extended Regex (Default)

Uses Python's built-in `re` module. Compatible with `grep -E` and `egrep`.

### Basic Patterns

```bash
# Literal match
earlyexit 'ERROR' ./app

# Case-insensitive
earlyexit -i 'error' ./app
```

### Alternation

```bash
# Match any of multiple patterns
earlyexit 'ERROR|FATAL|CRITICAL' ./app

# Grouped alternation
earlyexit '(start|begin) process' ./app
```

### Character Classes

```bash
# Any single character in brackets
earlyexit '[Ee]rror' ./app                  # Error or error
earlyexit '[0-9]' ./app                     # Any digit
earlyexit '[a-z]' ./app                     # Any lowercase letter
earlyexit '[A-Za-z0-9]' ./app               # Alphanumeric

# Negated character class
earlyexit '[^0-9]' ./app                    # NOT a digit

# Predefined classes
earlyexit '\d' ./app                        # Digit [0-9]
earlyexit '\D' ./app                        # Non-digit [^0-9]
earlyexit '\w' ./app                        # Word char [a-zA-Z0-9_]
earlyexit '\W' ./app                        # Non-word char
earlyexit '\s' ./app                        # Whitespace [ \t\n\r\f\v]
earlyexit '\S' ./app                        # Non-whitespace
```

### Quantifiers

```bash
# Zero or more
earlyexit 'error.*' ./app                   # error followed by anything

# One or more
earlyexit 'error.+' ./app                   # error followed by something

# Zero or one (optional)
earlyexit 'errors?' ./app                   # error or errors

# Exact count
earlyexit 'error\d{3}' ./app                # error followed by 3 digits

# Range
earlyexit 'error\d{2,4}' ./app              # error followed by 2-4 digits

# At least N
earlyexit 'error\d{2,}' ./app               # error followed by 2+ digits

# Non-greedy (minimal matching)
earlyexit 'error.*?' ./app                  # Minimal match
```

### Anchors

```bash
# Start of line
earlyexit '^ERROR' ./app

# End of line
earlyexit 'ERROR$' ./app

# Word boundary
earlyexit '\berror\b' ./app                 # Whole word "error"
earlyexit '\Berror\B' ./app                 # "error" NOT as whole word
```

### Groups

```bash
# Capturing groups
earlyexit '(ERROR|WARN): (.*)' ./app

# Non-capturing groups
earlyexit '(?:ERROR|WARN): (.*)' ./app

# Backreferences
earlyexit '(\w+) \1' ./app                  # Repeated word
```

### Lookahead Assertions

```bash
# Positive lookahead
earlyexit 'ERROR(?= critical)' ./app        # ERROR followed by " critical"

# Negative lookahead
earlyexit 'ERROR(?! ignored)' ./app         # ERROR NOT followed by " ignored"
```

### Lookbehind Assertions (Limited)

```bash
# Fixed-length positive lookbehind
earlyexit '(?<=ERROR: ).*' ./app            # After "ERROR: "

# Fixed-length negative lookbehind
earlyexit '(?<!INFO: )ERROR' ./app          # ERROR not after "INFO: "

# ⚠️ Limitation: Must be fixed-length in Python re
# This FAILS: '(?<=ERROR:? ).*'             # Variable length
```

### Special Characters

```bash
# Escape special characters
earlyexit '\[ERROR\]' ./app                 # Literal [ERROR]
earlyexit '\$100' ./app                     # Literal $100

# Special: . matches any character except newline
earlyexit 'error.message' ./app

# Dot matches any character
earlyexit '.*' ./app
```

## Perl-Compatible Regex (-P)

Uses the `regex` module for advanced features. Compatible with `grep -P`.

**Installation:** `pip install regex` or `pip install earlyexit[perl]`

### Everything from Python re, PLUS:

### Variable-Length Lookbehinds

```bash
# Can have quantifiers in lookbehind!
earlyexit -P '(?<=ERROR:? ).*' ./app        # After "ERROR: " or "ERROR:"
earlyexit -P '(?<=ERROR:\s+).*' ./app       # After "ERROR:" + whitespace
```

### Possessive Quantifiers

```bash
# Possessive (no backtracking - faster)
earlyexit -P 'error.*+failed' ./app         # .*+ doesn't backtrack
earlyexit -P '\d++' ./app                   # Possessive one-or-more
earlyexit -P '\w*+' ./app                   # Possessive zero-or-more
```

### Atomic Groups

```bash
# Atomic group (no backtracking inside)
earlyexit -P '(?>error|errors)' ./app
earlyexit -P '(?>ERROR|FATAL): .*' ./app
```

### Recursive Patterns

```bash
# Match balanced parentheses
earlyexit -P '\(([^()]*|(?R))*\)' ./app

# Match nested braces
earlyexit -P '\{([^{}]*|(?R))*\}' ./app

# Match nested HTML tags (simple)
earlyexit -P '<(\w+)>([^<>]*|(?R))*</\1>' ./app
```

### Unicode Properties

```bash
# Letter in any language
earlyexit -P '\p{Letter}+' ./app
earlyexit -P '\p{L}+' ./app                 # Short form

# Specific scripts
earlyexit -P '\p{Han}+' ./app               # Chinese
earlyexit -P '\p{Cyrillic}+' ./app          # Russian
earlyexit -P '\p{Arabic}+' ./app            # Arabic

# Numbers
earlyexit -P '\p{Number}+' ./app
earlyexit -P '\p{N}+' ./app

# Punctuation
earlyexit -P '\p{Punctuation}+' ./app

# Whitespace
earlyexit -P '\p{Whitespace}+' ./app
```

### Advanced Lookarounds

```bash
# Complex lookbehinds
earlyexit -P '(?<=ERROR\s+\d+:\s+).*' ./app

# Multiple lookaheads
earlyexit -P '(?=.*error)(?=.*failed).*' ./app

# Lookbehind with alternation
earlyexit -P '(?<=(ERROR|FATAL): ).*' ./app
```

## Common Patterns

### Log Level Matching

```bash
# Any log level
earlyexit '\b(DEBUG|INFO|WARN|ERROR|FATAL)\b'

# Error levels only
earlyexit '\b(ERROR|FATAL|CRITICAL)\b'

# Case-insensitive log levels
earlyexit -i '\b(error|fatal)\b'
```

### Timestamps

```bash
# ISO 8601 timestamp
earlyexit '\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'

# Common log timestamp
earlyexit '\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'

# Unix timestamp
earlyexit '\d{10}'
```

### IP Addresses

```bash
# Simple IP pattern (not validating)
earlyexit '\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'

# More precise (still not perfect)
earlyexit '([0-9]{1,3}\.){3}[0-9]{1,3}'
```

### Email Addresses

```bash
# Simple email pattern
earlyexit '\w+@\w+\.\w+'

# More complete
earlyexit '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
```

### URLs

```bash
# HTTP/HTTPS URLs
earlyexit 'https?://[^\s]+'

# With optional www
earlyexit 'https?://(www\.)?[^\s]+'
```

### File Paths

```bash
# Unix paths
earlyexit '/[a-zA-Z0-9/_.-]+'

# With specific extensions
earlyexit '/[^\s]+\.(log|txt|json)'
```

### JSON Error Messages

```bash
# JSON with "error" key
earlyexit '"error":\s*"[^"]*"'

# JSON with error level
earlyexit '"level":\s*"(ERROR|FATAL)"'
```

### Stack Traces

```bash
# Java stack trace line
earlyexit 'at [a-zA-Z0-9.$]+\([^)]+\)'

# Python traceback
earlyexit 'File "[^"]+", line \d+'
```

## Best Practices

### 1. Start Simple, Add Complexity

```bash
# Start with basic match
earlyexit 'error'

# Add word boundaries
earlyexit '\berror\b'

# Add context
earlyexit 'error.*connection'
```

### 2. Use Anchors When Possible

```bash
# Less specific
earlyexit 'ERROR'

# More specific
earlyexit '^ERROR:'                         # Must be at line start
```

### 3. Escape Special Characters

```bash
# Wrong - . matches any character
earlyexit 'error.log'

# Right - \. matches literal dot
earlyexit 'error\.log'
```

### 4. Use Non-Capturing Groups for Grouping Only

```bash
# Capturing (memory overhead)
earlyexit '(ERROR|FATAL): .*'

# Non-capturing (faster)
earlyexit '(?:ERROR|FATAL): .*'
```

### 5. Choose the Right Engine

```bash
# Simple pattern? Use default (faster)
earlyexit 'ERROR|FATAL'

# Need advanced features? Use -P
earlyexit -P '(?<=ERROR: ).*'
```

### 6. Test Your Patterns

```bash
# Test with echo
echo "ERROR: test message" | earlyexit 'ERROR'

# Test different cases
echo "error" | earlyexit -i 'ERROR'
```

## Examples

### Example 1: Terraform Errors

```bash
# Basic error detection
earlyexit -i 'error' terraform apply

# More specific
earlyexit '^Error:' terraform apply

# Multiple error types
earlyexit '(Error|Fatal)' terraform apply
```

### Example 2: Build Failures

```bash
# Generic build failure
earlyexit -i 'failed|error' make

# Specific compiler errors
earlyexit 'error: ' make

# Multiple patterns
earlyexit '\b(error|fatal|failed)\b' make
```

### Example 3: Test Failures

```bash
# Pytest failures
earlyexit 'FAILED' pytest -v

# Jest failures
earlyexit '✕|FAIL' npm test

# Generic test failures
earlyexit -i '\bfail(ed|ure)?\b' npm test
```

### Example 4: Log Monitoring

```bash
# Any error level
earlyexit '\b(ERROR|FATAL|CRITICAL)\b' tail -f app.log

# With timestamp
earlyexit '\d{4}-\d{2}-\d{2}.*ERROR' tail -f app.log

# Exclude known issues
earlyexit -P '(?<!KNOWN )ERROR' tail -f app.log
```

### Example 5: Database Errors

```bash
# Connection errors
earlyexit -i 'connection.*error' ./db-migrate

# Timeout errors
earlyexit -i 'timeout|timed out' ./db-query

# SQL errors
earlyexit 'ERROR \d+:' ./mysql-import
```

### Example 6: Kubernetes Errors

```bash
# Pod failures
earlyexit 'CrashLoopBackOff|Error|Failed' kubectl get pods

# Container errors
earlyexit -i 'error|fatal' kubectl logs pod-name

# Multiple error types
earlyexit 'Error|Failed|CrashLoop|OOMKilled' kubectl describe pod
```

### Example 7: CI/CD Pipelines

```bash
# Build stage failure
earlyexit -i 'build.*fail' ./build.sh

# Test stage failure
earlyexit -i 'test.*fail|[0-9]+ failed' ./test.sh

# Deployment failure
earlyexit -i 'deploy.*fail|rollback' ./deploy.sh
```

### Example 8: API Errors

```bash
# HTTP error codes
earlyexit '\b(4[0-9]{2}|5[0-9]{2})\b' curl api.example.com

# JSON error responses
earlyexit '"error":|"status":\s*"error"' curl api.example.com

# Timeout errors
earlyexit -i 'timeout|timed out' curl api.example.com
```

## Regex Cheat Sheet

### Metacharacters

| Character | Meaning | Example |
|-----------|---------|---------|
| `.` | Any character (except newline) | `a.c` matches abc, a1c |
| `^` | Start of line | `^ERROR` |
| `$` | End of line | `ERROR$` |
| `*` | Zero or more | `ab*` matches a, ab, abb |
| `+` | One or more | `ab+` matches ab, abb |
| `?` | Zero or one | `ab?` matches a, ab |
| `{n}` | Exactly n | `a{3}` matches aaa |
| `{n,}` | n or more | `a{2,}` matches aa, aaa |
| `{n,m}` | Between n and m | `a{2,4}` |
| `|` | Alternation | `cat|dog` |
| `()` | Group | `(ab)+` |
| `[]` | Character class | `[abc]` |
| `\` | Escape | `\.` matches literal dot |

### Character Classes

| Class | Meaning | Equivalent |
|-------|---------|------------|
| `\d` | Digit | `[0-9]` |
| `\D` | Non-digit | `[^0-9]` |
| `\w` | Word character | `[a-zA-Z0-9_]` |
| `\W` | Non-word character | `[^a-zA-Z0-9_]` |
| `\s` | Whitespace | `[ \t\n\r\f\v]` |
| `\S` | Non-whitespace | `[^ \t\n\r\f\v]` |
| `\b` | Word boundary | - |
| `\B` | Non-word boundary | - |

### Lookarounds

| Type | Syntax | Example |
|------|--------|---------|
| Positive lookahead | `(?=...)` | `ERROR(?= critical)` |
| Negative lookahead | `(?!...)` | `ERROR(?! ignored)` |
| Positive lookbehind | `(?<=...)` | `(?<=ERROR: ).*` |
| Negative lookbehind | `(?<!...)` | `(?<!INFO: )ERROR` |

### Flags (via options)

| Option | Effect | Example |
|--------|--------|---------|
| `-i` | Case-insensitive | `earlyexit -i 'error'` |
| `-E` | Extended regex (default) | `earlyexit -E 'a|b'` |
| `-P` | Perl-compatible regex | `earlyexit -P '(?<=:).*'` |

## Troubleshooting

### Pattern Not Matching

1. Test your pattern with `echo`:
   ```bash
   echo "ERROR: test" | earlyexit 'ERROR'
   ```

2. Try case-insensitive:
   ```bash
   earlyexit -i 'error'
   ```

3. Check for special characters:
   ```bash
   # Wrong
   earlyexit 'test.'
   
   # Right
   earlyexit 'test\.'
   ```

### Regex Too Slow

1. Use possessive quantifiers (Perl):
   ```bash
   earlyexit -P '.*+ERROR'
   ```

2. Use atomic groups (Perl):
   ```bash
   earlyexit -P '(?>ERROR|FATAL)'
   ```

3. Be more specific:
   ```bash
   # Slower
   earlyexit '.*error.*'
   
   # Faster
   earlyexit 'error'
   ```

## Resources

- Python `re` documentation: https://docs.python.org/3/library/re.html
- Python `regex` module: https://pypi.org/project/regex/
- Regular Expressions 101 (testing): https://regex101.com/
- RegExr (testing): https://regexr.com/

## Version

- Document version: 1.0
- earlyexit version: 0.0.1
- Date: November 10, 2025

