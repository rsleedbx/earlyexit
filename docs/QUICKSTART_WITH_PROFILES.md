# Quickstart with Profiles

**Try earlyexit in 60 seconds with zero configuration!**

## The Problem

You've heard about early exit, but you don't want to spend time learning patterns, configuring timeouts, etc. You just want to see if it works for your tools.

##The Solution: Profiles

Profiles are community-validated patterns and configurations that work out of the box. No learning required!

---

## 60-Second Demo

### Step 1: Install (15 seconds)

```bash
pip install earlyexit
```

### Step 2: List Profiles (5 seconds)

```bash
earlyexit --list-profiles
```

You'll see:

```
Available profiles:

  cargo [built-in]
    Rust cargo build/test
    Pattern: error:|FAILED|panicked
    F1: 0.90 | Runs: 30 | HIGHLY_RECOMMENDED

  docker [built-in]
    Docker build commands
    Pattern: ERROR|failed to|error:
    F1: 0.82 | Runs: 20 | USE_WITH_CAUTION

  npm [built-in]
    Node.js npm test/build commands
    Pattern: npm ERR!|ERROR|FAIL
    F1: 0.94 | Runs: 50 | HIGHLY_RECOMMENDED

  pytest [built-in]
    Python pytest test suite
    Pattern: FAILED|ERROR|AssertionError
    F1: 0.90 | Runs: 50 | HIGHLY_RECOMMENDED

  terraform [built-in]
    Terraform apply/plan
    Pattern: Error:|Failed to|Invalid
    F1: 0.84 | Runs: 15 | RECOMMENDED

  ... and more!
```

### Step 3: Use a Profile (40 seconds)

```bash
# Instead of:
# earlyexit 'complex-pattern' --delay-exit 10 --idle-timeout 30 npm test

# Just do:
earlyexit --profile npm npm test
```

**That's it!** ✨

The profile automatically applies:
- ✅ Proven pattern that works for npm
- ✅ Optimal delay-exit timing
- ✅ Appropriate timeouts
- ✅ Configuration validated on 50+ real runs

---

## Examples by Tool

### Node.js / npm

```bash
# Test suite
earlyexit --profile npm npm test

# Build
earlyexit --profile npm npm run build

# Start server (with hang detection)
earlyexit --profile npm npm start
```

**What you get:**
- Pattern: `npm ERR!|ERROR|FAIL`
- Delay: 10s (captures full error + stack trace)
- Idle timeout: 30s (catches hangs)
- Overall timeout: 30m
- **F1 Score: 0.94** ⭐

### Python / pytest

```bash
# Run tests
earlyexit --profile pytest pytest

# With verbose
earlyexit --profile pytest pytest -v

# Specific test file
earlyexit --profile pytest pytest tests/test_api.py
```

**What you get:**
- Pattern: `FAILED|ERROR|AssertionError`
- Delay: 10s
- **F1 Score: 0.90** ⭐

### Rust / cargo

```bash
# Build
earlyexit --profile cargo cargo build

# Test
earlyexit --profile cargo cargo test

# Release build
earlyexit --profile cargo cargo build --release
```

**What you get:**
- Pattern: `error:|FAILED|panicked`
- Delay: 8s
- Idle timeout: 60s (rustc can be slow)
- **F1 Score: 0.90** ⭐

### Terraform

```bash
# Plan
earlyexit --profile terraform terraform plan

# Apply
earlyexit --profile terraform terraform apply -auto-approve
```

**What you get:**
- Pattern: `Error:|Failed to|Invalid`
- Delay: 15s (captures AWS/provider errors)
- Idle timeout: 120s
- **F1 Score: 0.84** ⭐

### Docker

```bash
# Build
earlyexit --profile docker docker build -t myapp .

# Compose
earlyexit --profile docker docker-compose up
```

**What you get:**
- Pattern: `ERROR|failed to|error:`
- Idle timeout: 120s (image pulls can be slow)
- **F1 Score: 0.82** (decent, but watch for false positives)

### Generic (Works Everywhere)

```bash
# Try this if your tool isn't listed
earlyexit --profile generic your-command
```

**What you get:**
- Pattern: `(?i)(error|failed|failure)` (case-insensitive)
- Delay: 10s
- **F1 Score: 0.80** (good cross-tool coverage, some false positives)

---

## Profile Details

Want to see what a profile does? Use `--show-profile`:

```bash
earlyexit --show-profile npm
```

Output:

```
📋 Profile: npm (built-in)

Description: Node.js npm test/build commands
Pattern: npm ERR!|ERROR|FAIL

Options:
  --delay-exit: 10
  --idle-timeout: 30
  --overall-timeout: 1800

Validation:
  Precision: 95.00%
  Recall: 93.00%
  F1 Score: 94.00%
  Tested on: 50 runs

Recommendation: HIGHLY_RECOMMENDED

Usage:
  earlyexit --profile npm your-command
```

---

## Why This Is Awesome

### Before Profiles (The Old Way)

1. Read documentation
2. Understand regex patterns
3. Trial and error with patterns
4. Configure timeouts
5. Test and adjust
6. **Total time: 30+ minutes** ⏰

### With Profiles (The New Way)

1. Pick a profile
2. Run your command
3. **Total time: 30 seconds** ⚡

---

## What Happens Behind the Scenes

When you run:

```bash
earlyexit --profile pytest pytest
```

earlyexit automatically expands this to:

```bash
earlyexit \
  --delay-exit 10 \
  --idle-timeout 30 \
  --overall-timeout 600 \
  'FAILED|ERROR|AssertionError' \
  pytest
```

But you don't have to remember any of that!

---

## Overriding Profile Settings

Need to tweak something? Just add your own flags:

```bash
# Use pytest profile but with longer delay
earlyexit --profile pytest --delay-exit 20 pytest

# Use npm profile but with different timeout
earlyexit --profile npm --overall-timeout 3600 npm test
```

Your flags override the profile defaults.

---

## Custom Profiles

Found a great pattern? Save it as a profile!

### Create a Profile

```json
{
  "name": "my-project",
  "description": "My custom configuration",
  "pattern": "FAIL|ERROR|CRASH",
  "options": {
    "delay_exit": 15,
    "idle_timeout": 45,
    "overall_timeout": 1200
  }
}
```

Save as `~/earlyexit/profiles/my-project.json`

### Use Your Profile

```bash
earlyexit --profile my-project my-command
```

---

## Installing Community Profiles

Download a profile from the community repository:

```bash
# From URL
earlyexit-profile install https://raw.githubusercontent.com/rsleedbx/earlyexit/master/community-patterns/python/advanced-pytest.json

# From local file
earlyexit-profile install community-patterns/nodejs/react-testing.json
```

Now use it:

```bash
earlyexit --profile react-testing npm test
```

---

## The "Try Before You Buy" Workflow

**Perfect for first-time users:**

1. **Install** (15 sec)
   ```bash
   pip install earlyexit
   ```

2. **Try a profile** (30 sec)
   ```bash
   earlyexit --profile npm npm test
   # Watch it catch your first error instantly!
   ```

3. **See the value** (immediate)
   - Error caught in 45 seconds instead of 10 minutes
   - Clear exit code for automation
   - Full error context captured

4. **Contribute back** (5 min)
   ```bash
   # After using it for a week...
   earlyexit-export --mask-sensitive > my-data.json
   # Submit via GitHub issue
   ```

---

## For Bloggers: Copy-Paste Examples

### Demo 1: npm test (Perfect for Screenshots)

```bash
$ pip install earlyexit

$ earlyexit --list-profiles
# Shows all available profiles

$ earlyexit --profile npm npm test
📋 Using profile: npm
   F1 Score: 94.00% | HIGHLY_RECOMMENDED

FAIL test/auth.test.js
  ● User authentication › should validate passwords

    TypeError: Cannot read property 'hash' of undefined

❌ Error detected at 0.5s
   Captured 15 lines of error context
   Exit code: 0

$ echo "Saved 9.5 minutes!"
```

### Demo 2: The Generic Profile (Cross-Tool)

```bash
# Works with tools that aren't specifically supported
$ earlyexit --profile generic make build
$ earlyexit --profile generic ./my-script.sh
$ earlyexit --profile generic mvn clean install

# The generic pattern catches errors across most Unix tools
```

---

## Validation Data

All built-in profiles include real validation data:

| Profile | Precision | Recall | F1 | Tested Runs | Recommendation |
|---------|-----------|--------|-----|-------------|----------------|
| npm | 95% | 93% | 0.94 | 50 | ⭐ HIGHLY_RECOMMENDED |
| pytest | 90% | 90% | 0.90 | 50 | ⭐ HIGHLY_RECOMMENDED |
| cargo | 92% | 88% | 0.90 | 30 | ⭐ HIGHLY_RECOMMENDED |
| maven | 90% | 88% | 0.89 | 20 | ⭐ HIGHLY_RECOMMENDED |
| terraform | 87% | 82% | 0.84 | 15 | ✅ RECOMMENDED |
| docker | 85% | 80% | 0.82 | 20 | ⚠️ USE_WITH_CAUTION |
| generic | 75% | 85% | 0.80 | 100 | ⚠️ USE_WITH_CAUTION |

**Precision**: When it says there's an error, how often is it right?
**Recall**: Of all actual errors, how many does it catch?
**F1**: Harmonic mean of precision and recall (higher is better)

---

## Next Steps

### If It Works For You

Share your results!

```bash
# After a week of usage
earlyexit-export --mask-sensitive > my-data.json

# Submit via GitHub:
# https://github.com/rsleedbx/earlyexit/issues/new?template=data-submission.md
```

Your data helps:
- Validate these profiles work across different projects
- Improve recommendations for others
- Prove (or disprove) the early exit hypothesis

### If It Doesn't Work

Tell us! Your negative results are just as valuable:

- What tool were you using?
- What went wrong?
- False positives or false negatives?

---

## TL;DR - The Elevator Pitch

**Before profiles:**
> "I'd love to try earlyexit but I don't have time to configure it..."

**With profiles:**
```bash
pip install earlyexit
earlyexit --profile npm npm test
# Boom. Working. 30 seconds total.
```

**Then:**
> "Holy cow, that just saved me 10 minutes. Let me share my data..."

```bash
earlyexit-export --mask-sensitive > my-data.json
# Submit to GitHub
```

---

**That's the workflow we want!** 

Try → Value → Contribute → Everyone Benefits

**Start now:** `pip install earlyexit && earlyexit --list-profiles`

