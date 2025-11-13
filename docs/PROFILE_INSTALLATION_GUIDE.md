# Profile Installation Guide

Complete guide to installing, managing, and sharing earlyexit profiles.

---

## Quick Reference

```bash
# List all profiles
earlyexit-profile list

# Show profile details
earlyexit-profile show npm

# Install from URL
earlyexit-profile install https://example.com/profile.json

# Install from local file
earlyexit-profile install ./my-profile.json

# Use installed profile
earlyexit --profile my-profile npm test
```

---

## Installing Profiles

### From URL

Install profiles directly from the web:

```bash
# Install from GitHub
earlyexit-profile install https://raw.githubusercontent.com/rsleedbx/earlyexit/master/community-patterns/nodejs/npm-example.json

# Install from any URL
earlyexit-profile install https://mysite.com/profiles/my-custom-profile.json

# Specify a custom name
earlyexit-profile install https://example.com/profile.json --name my-npm
```

**What happens:**
1. Downloads the JSON file
2. Validates the format
3. Installs to `~/.earlyexit/profiles/`
4. Makes it available via `--profile` flag

### From Local File

Install profiles from your filesystem:

```bash
# Relative path
earlyexit-profile install ./profiles/my-profile.json

# Absolute path
earlyexit-profile install /path/to/profile.json

# Home directory (~)
earlyexit-profile install ~/Downloads/pytest-advanced.json

# With custom name
earlyexit-profile install ./custom.json --name my-custom
```

**Common scenarios:**

```bash
# Downloaded from GitHub
cd ~/Downloads
earlyexit-profile install npm-advanced.json

# Cloned the repo
git clone https://github.com/rsleedbx/earlyexit
earlyexit-profile install earlyexit/community-patterns/python/example-pytest.json

# Created your own
earlyexit-profile install ./my-project-profile.json --name my-project
```

---

## Managing Profiles

### List Profiles

```bash
# Basic list
earlyexit-profile list

# With validation metrics
earlyexit-profile list --validation
earlyexit-profile list -v
```

Output shows:
- Profile name
- Built-in vs user-installed
- Description
- Pattern
- Validation metrics (if `--validation` flag used)

### Show Profile Details

```bash
# Show specific profile
earlyexit-profile show npm
earlyexit-profile show my-custom-profile
```

Shows:
- Full description
- Pattern used
- All options (delay-exit, timeouts, etc.)
- Validation metrics
- Recommendation level
- Usage examples

### Remove Profiles

```bash
# Remove user-installed profile
earlyexit-profile remove my-profile

# Built-in profiles cannot be removed
earlyexit-profile remove npm  # ❌ Error: Cannot remove built-in
```

---

## Using Installed Profiles

After installation, use profiles like built-ins:

```bash
# Use installed profile
earlyexit --profile my-profile npm test

# Override settings
earlyexit --profile my-profile --delay-exit 20 npm test

# Show what it does
earlyexit-profile show my-profile
```

---

## Creating Shareable Profiles

### Basic Format

```json
{
  "name": "my-tool",
  "description": "Description of what this profile does",
  "pattern": "ERROR|FAIL|CRASH",
  "options": {
    "delay_exit": 10,
    "idle_timeout": 30,
    "overall_timeout": 1800
  },
  "validation": {
    "precision": 0.90,
    "recall": 0.88,
    "f1_score": 0.89,
    "tested_runs": 25
  },
  "recommendation": "HIGHLY_RECOMMENDED",
  "notes": [
    "Works well with...",
    "May have issues with..."
  ]
}
```

### Required Fields

- `name` - Profile identifier (used with `--profile`)
- `description` - What the profile is for
- `pattern` - Regex pattern to match

### Optional Fields

- `options` - Dict of CLI options (delay_exit, idle_timeout, etc.)
- `validation` - Performance metrics
- `recommendation` - HIGHLY_RECOMMENDED, RECOMMENDED, USE_WITH_CAUTION, etc.
- `notes` - Array of usage notes
- `contributor` - Your name/username
- `source` - URL where the profile can be found

### Example: Create and Share

```bash
# 1. Create your profile
cat > my-react-profile.json << 'EOF'
{
  "name": "react-testing",
  "description": "React app testing with Jest",
  "pattern": "FAIL|Error|●|✕",
  "options": {
    "delay_exit": 8,
    "idle_timeout": 30,
    "overall_timeout": 600
  },
  "validation": {
    "precision": 0.92,
    "recall": 0.88,
    "f1_score": 0.90,
    "tested_runs": 30
  },
  "recommendation": "HIGHLY_RECOMMENDED"
}
EOF

# 2. Test it locally
earlyexit-profile install ./my-react-profile.json
earlyexit --profile react-testing npm test

# 3. Share it
# Option A: Submit to community repo via PR
git clone https://github.com/rsleedbx/earlyexit
cp my-react-profile.json earlyexit/community-patterns/nodejs/
# Submit PR

# Option B: Host on your site
# Upload to your website/GitHub
# Share the URL: https://yoursite.com/profiles/react-testing.json
# Others can install: earlyexit-profile install https://yoursite.com/profiles/react-testing.json
```

---

## Community Profiles

### Official Repository

Browse community profiles:
https://github.com/rsleedbx/earlyexit/tree/master/community-patterns

Organized by tool type:
- `nodejs/` - npm, yarn, node
- `python/` - pytest, pip, python
- `rust/` - cargo, rustc
- `go/` - go test, go build
- `iac/` - terraform, pulumi
- `containers/` - docker, kubernetes
- `generic/` - cross-tool patterns

### Installing Community Profiles

```bash
# Direct from GitHub
earlyexit-profile install https://raw.githubusercontent.com/rsleedbx/earlyexit/master/community-patterns/python/example-pytest.json

# Clone repo first
git clone https://github.com/rsleedbx/earlyexit
cd earlyexit
earlyexit-profile install community-patterns/nodejs/npm-example.json
earlyexit-profile install community-patterns/python/example-pytest.json
earlyexit-profile install community-patterns/rust/cargo-profile.json
```

### Contributing to Community

1. **Test your profile extensively** (25+ runs recommended)
2. **Document validation metrics** (precision, recall, F1)
3. **Add usage notes** (what works, what doesn't)
4. **Submit as PR** or **share the URL**

---

## Profile Storage

### Location

User-installed profiles are stored in:
```
~/.earlyexit/profiles/
```

### File Structure

```
~/.earlyexit/
├── telemetry.db          # Usage data
└── profiles/             # User profiles
    ├── my-profile.json
    ├── react-testing.json
    └── custom-pytest.json
```

### Precedence

When you use `--profile NAME`:
1. Check user profiles in `~/.earlyexit/profiles/`
2. If not found, check built-in profiles
3. User profiles override built-ins with same name

---

## Advanced Usage

### Profile Inheritance

You can install multiple versions of a profile:

```bash
# Install base profile
earlyexit-profile install https://example.com/npm-base.json --name npm-base

# Install extended version
earlyexit-profile install https://example.com/npm-extended.json --name npm-ext

# Use whichever fits your needs
earlyexit --profile npm-base npm test
earlyexit --profile npm-ext npm test
```

### Project-Specific Profiles

```bash
# Create profile for your project
cat > .earlyexit-profile.json << 'EOF'
{
  "name": "myapp",
  "description": "Profile for myapp testing",
  "pattern": "FAILED|ERROR|CRASH",
  "options": {
    "delay_exit": 15,
    "idle_timeout": 45
  }
}
EOF

# Install for your team
earlyexit-profile install .earlyexit-profile.json

# Add to README
echo "earlyexit-profile install .earlyexit-profile.json" >> README.md
echo "earlyexit --profile myapp npm test" >> README.md
```

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Install earlyexit profile
  run: |
    pip install earlyexit
    earlyexit-profile install ${{ github.workspace }}/.earlyexit-profile.json

- name: Run tests with profile
  run: earlyexit --profile myapp npm test
```

---

## Troubleshooting

### Profile Not Found

```bash
❌ Profile 'my-profile' not found
```

**Solutions:**
1. Check spelling: `earlyexit-profile list`
2. Make sure it's installed: `earlyexit-profile install ...`
3. Check location: `ls ~/.earlyexit/profiles/`

### Download Failed

```bash
❌ Failed to download profile: HTTP Error 404
```

**Solutions:**
1. Check URL is correct
2. Make sure URL points to raw JSON (not HTML page)
3. For GitHub, use `raw.githubusercontent.com` URLs

### Invalid JSON

```bash
❌ Error: Invalid JSON format
```

**Solutions:**
1. Validate JSON at https://jsonlint.com
2. Check for trailing commas (not allowed in JSON)
3. Ensure all strings use double quotes (not single)

### Permission Denied

```bash
❌ Permission denied: ~/.earlyexit/profiles/
```

**Solutions:**
```bash
# Create directory with proper permissions
mkdir -p ~/.earlyexit/profiles
chmod 755 ~/.earlyexit/profiles
```

---

## Examples

### Install Community npm Profile

```bash
$ earlyexit-profile install https://raw.githubusercontent.com/rsleedbx/earlyexit/master/community-patterns/nodejs/npm-example.json

📥 Downloading profile from https://raw.githubusercontent...
✅ Profile 'npm-community' installed successfully!

Usage:
  earlyexit --profile npm-community your-command

Show details:
  earlyexit-profile show npm-community
```

### Install and Use Local Profile

```bash
$ cat my-profile.json
{
  "name": "my-tests",
  "pattern": "FAIL|ERROR",
  "options": {"delay_exit": 10}
}

$ earlyexit-profile install ./my-profile.json
📥 Installing profile from /Users/you/my-profile.json...
✅ Profile 'my-tests' installed successfully!

$ earlyexit --profile my-tests npm test
📋 Using profile: my-tests
[... runs with profile settings ...]
```

### Override Built-in Profile

```bash
# Install custom version of npm profile
$ earlyexit-profile install ./my-npm.json --name npm

⚠️  Warning: This profile name 'npm' matches a built-in profile.
   Your custom profile will take precedence when using --profile npm

✅ Profile 'npm' installed successfully!

# Now using your custom version
$ earlyexit --profile npm npm test
📋 Using profile: npm (user)
```

---

## Best Practices

### For Users

1. **Try built-ins first** - They're validated across many users
2. **Test community profiles** - Validate metrics match your experience
3. **Read the notes** - Profile authors share important details
4. **Override when needed** - Don't be afraid to customize

### For Profile Creators

1. **Test extensively** - 25+ runs minimum
2. **Calculate real metrics** - Track TP/TN/FP/FN accurately
3. **Document edge cases** - What doesn't work?
4. **Keep patterns simple** - Complexity → false positives
5. **Version your profiles** - Use names like `npm-v2` if patterns change

### For Teams

1. **Share project profiles** - Commit `.earlyexit-profile.json`
2. **Document in README** - Installation and usage instructions
3. **Validate in CI** - Test profile works in automated environment
4. **Update based on feedback** - Improve as you learn

---

## See Also

- [Quickstart with Profiles](./QUICKSTART_WITH_PROFILES.md)
- [Creating Custom Profiles](./community-patterns/README.md)
- [Profile System Summary](../PROFILE_SYSTEM_SUMMARY.md)

---

**Questions? Open an issue or discussion on GitHub!**

