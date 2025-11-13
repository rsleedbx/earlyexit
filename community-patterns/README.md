# Community Patterns

This directory contains validated patterns and configurations shared by the earlyexit community.

## Structure

```
community-patterns/
├── nodejs/          # Node.js, npm, yarn patterns
├── python/          # Python, pytest, pip patterns
├── rust/            # Cargo, rustc patterns
├── go/              # Go build, test patterns
├── iac/             # Terraform, Pulumi, CloudFormation
├── containers/      # Docker, Kubernetes patterns
└── generic/         # Cross-tool patterns
```

## Contributing a Pattern

### Option 1: Export Your Learned Patterns

```bash
# Export patterns for a specific project type
earlyexit-export --project-type python --mask-sensitive > python-patterns.json

# Fork this repo and add to appropriate directory
cp python-patterns.json community-patterns/python/your-username-YYYY-MM-DD.json

# Submit a PR with description
```

### Option 2: Manual Pattern Contribution

Create a JSON file following this format:

```json
{
  "version": "1.0",
  "contributor": "your-username",
  "tool": "pytest",
  "project_type": "python",
  "use_case": "Testing data science projects",
  "patterns": [
    {
      "pattern": "FAILED|ERROR|AssertionError",
      "description": "Catches pytest failures",
      "delay_exit": 10,
      "validation": {
        "tested_on_runs": 50,
        "precision": 0.95,
        "recall": 0.90,
        "f1_score": 0.92
      },
      "recommendation": "HIGHLY_RECOMMENDED",
      "notes": "Works well for unit tests, may need adjustment for integration tests"
    }
  ]
}
```

## Using Community Patterns

### Import Patterns

```bash
# Import a specific pattern file
earlyexit-import community-patterns/python/community-pytest.json

# Import all patterns for a language
cat community-patterns/python/*.json | earlyexit-import -
```

### Browse and Learn

Even if you don't import, browsing patterns can help you:
- Learn what patterns work for similar tools
- See typical timeout values for your use case
- Understand false positive/negative rates
- Get inspiration for your own configurations

## Pattern Validation Status

Patterns in this directory have different validation levels:

- 🟢 **HIGHLY_RECOMMENDED** - F1 > 0.75, extensively tested
- 🟡 **USE_WITH_CAUTION** - Good precision but lower recall, or vice versa
- 🟠 **EXPERIMENTAL** - Limited testing, use with care
- 🔴 **DEPRECATED** - Known issues, don't use

Each pattern file includes validation metrics so you can make informed decisions.

## Research Data

Aggregated (anonymized) data from these patterns is used to:
- Validate the early exit hypothesis
- Improve the ML recommendation system
- Publish research findings
- Build better defaults for common tools

## Privacy

All patterns in this directory:
- ✅ Have been sanitized of sensitive data
- ✅ Use generic examples, not real project secrets
- ✅ Include only public metrics and project types
- ❌ Do NOT contain actual command strings or paths

## Questions?

- General questions: [GitHub Discussions - Q&A](https://github.com/rsleedbx/earlyexit/discussions/categories/q-a)
- Pattern questions: [GitHub Discussions - Patterns](https://github.com/rsleedbx/earlyexit/discussions/categories/patterns)
- Data submission: [Use the issue template](https://github.com/rsleedbx/earlyexit/issues/new?template=data-submission.md)

