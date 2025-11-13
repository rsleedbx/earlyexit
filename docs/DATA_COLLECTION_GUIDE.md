# Data Collection Guide for earlyexit

This guide explains how earlyexit collects data and how you can contribute to validating the early exit hypothesis.

## Overview

earlyexit is an **experiment** to test whether ML early exit principles apply to command-line tools. To prove (or disprove) this, we need real-world data from diverse users and use cases.

## What We Have ✅

### 1. Local Telemetry System
- SQLite database at `~/.earlyexit/telemetry.db`
- Tracks execution metrics, match events, validation outcomes
- Automatic PII scrubbing (passwords, tokens, emails, IPs)
- Can be completely disabled with `--no-telemetry` or `EARLYEXIT_NO_TELEMETRY=1`

### 2. Export Functionality
```bash
earlyexit-export --mask-sensitive > my-data.json
```
- Exports learned settings with sensitive data masked
- Includes validation metrics (TP/TN/FP/FN)
- Safe to share publicly

### 3. Import Functionality
```bash
earlyexit-import community-patterns.json
```
- Import patterns from others
- Build on community knowledge

## What We Need from You 🙏

### Phase 1: Manual Submission (Current)

**Step 1: Use earlyexit on your projects**
```bash
# Try it on your workflows
earlyexit 'Error|FAIL' npm test
earlyexit 'error' cargo build
earlyexit 'FAILED' pytest
```

**Step 2: Let it learn**
```bash
# Or use watch mode to teach it
earlyexit npm test
# Press Ctrl+C when you see an error
# Answer the interactive prompts
```

**Step 3: Export your data**
```bash
# After some usage (10+ runs ideal), export
earlyexit-export --mask-sensitive > my-earlyexit-data.json
```

**Step 4: Submit to GitHub**

Choose one method:

1. **GitHub Issue** (preferred for structured data)
   - https://github.com/rsleedbx/earlyexit/issues/new?template=data-submission.md
   - Fill out the template with context
   - Paste or attach your JSON

2. **GitHub Discussion** (better for conversation)
   - https://github.com/rsleedbx/earlyexit/discussions/categories/data-sharing
   - Share your experience and results
   - Others can comment and compare

3. **Pull Request** (for curated patterns)
   - Fork the repo
   - Add your JSON to `community-patterns/[language]/`
   - Submit PR with description

## What Gets Collected

### In Local Database (Private)

**Stored Locally:**
- Full command strings (scrubbed of passwords/tokens)
- Pattern configurations
- Timing metrics (runtime, time to first match, etc.)
- Match events with line content (PII scrubbed)
- Validation outcomes (TP/TN/FP/FN)
- User feedback

**Sensitivity Levels:**
- 🌐 **PUBLIC**: Project type, exit codes, metrics, timing
- 🔒 **PRIVATE**: Working directory (hashed), command basename (hashed)
- 🔐 **SENSITIVE**: Full commands, custom patterns, file paths, output lines

### In Export (Shareable)

**Included in masked export:**
```json
{
  "command_hash": "a3f2e9c1...",        // 16-char hash (not reversible)
  "project_type": "nodejs",              // Safe to share
  "learned_parameters": {
    "pattern": "<masked>",               // Your pattern is hidden
    "timeout": 1800,                     // Safe to share
    "delay_exit": 10                     // Safe to share
  },
  "validation": {
    "counts": {
      "true_positives": 18,              // Anonymous counts
      "true_negatives": 32,
      "false_positives": 2,
      "false_negatives": 1
    },
    "metrics": {
      "precision": 0.90,                 // Performance metrics
      "recall": 0.95,
      "f1_score": 0.92
    }
  },
  "recommendation": "HIGHLY_RECOMMENDED"
}
```

**NOT included in masked export:**
- Your actual patterns (only placeholder `<masked>`)
- Command arguments
- File paths
- Working directory (only hashed version)
- Any matched output lines
- Anything that could identify you or your project

## What Happens to Your Data

### Immediate Use
1. **Aggregated Statistics**: Weekly summaries of all submissions
   - "50 users tested on Node.js projects"
   - "Average F1 score: 0.87 across 23 tools"
   - "False positive rate: 3.2%"

2. **Pattern Validation**: Cross-reference patterns across users
   - "Pattern X works for 45/50 pytest users"
   - "Pattern Y has high false positive rate in CI/CD"

3. **Tool Improvement**: Fix issues discovered in your data
   - Performance bottlenecks
   - Edge cases
   - Better defaults

### Long-term Use
1. **Research Paper**: Community-driven validation study
   - You can be listed as contributor (opt-in)
   - Aggregated results published
   - Hypothesis validated or invalidated

2. **Pattern Library**: Curated best practices
   - Tool-specific recommendations
   - Proven configurations
   - Community knowledge base

3. **ML Enhancement**: If hypothesis validates
   - Better pattern suggestions
   - Improved timeout predictions
   - Cross-project learning

## Privacy & Ethics

### Your Control
- ✅ **Opt-in**: You manually export and submit
- ✅ **Inspect first**: Review JSON before sharing
- ✅ **Selective sharing**: Export only specific project types
- ✅ **Complete disable**: `EARLYEXIT_NO_TELEMETRY=1`

### Our Promises
- ✅ **No cloud upload** without your explicit action
- ✅ **No tracking** of individuals
- ✅ **No reverse engineering** of masked data
- ✅ **Transparent use** of all submitted data
- ✅ **Credit contributors** (if desired)
- ✅ **Open results** - all findings public

### What We Won't Do
- ❌ Never decrypt/unmask your sensitive data
- ❌ Never sell or share data with third parties
- ❌ Never use data for commercial purposes beyond the tool itself
- ❌ Never try to identify individual users from submissions
- ❌ Never share raw data, only aggregated statistics

## What We're Trying to Learn

### Primary Questions
1. **Does early exit save time in practice?**
   - Hypothesis: Yes, but how much varies by tool
   - Need: Time savings data across diverse projects

2. **Do patterns generalize across similar tools?**
   - Hypothesis: Tool-specific patterns > generic patterns
   - Need: Multi-tool data from same users

3. **Are false positives acceptable?**
   - Hypothesis: <5% false positive rate is acceptable
   - Need: User tolerance data and FP/FN counts

4. **Does ML validation help?**
   - Hypothesis: TP/TN/FP/FN metrics guide better patterns
   - Need: User feedback on whether metrics were useful

### Secondary Questions
1. Optimal delay-exit times per tool category
2. Idle timeout sweet spots for different workflows
3. Pattern complexity vs effectiveness trade-offs
4. CI/CD vs local development behavior differences

## Roadmap

### Phase 1: Manual Collection (Current)
- ✅ Built: Export/import functionality
- ✅ Built: Privacy-preserving masking
- ✅ Built: Validation metrics (TP/TN/FP/FN)
- 🚧 Need: Your data submissions!

### Phase 2: Automated Sharing (If Phase 1 succeeds)
- 🔮 Feature: `earlyexit --share-anonymously` flag
- 🔮 Feature: Periodic opt-in data sync
- 🔮 Feature: Differential privacy techniques
- 🔮 Feature: Local aggregation before sharing

### Phase 3: Federated Learning (If Phase 2 succeeds)
- 🔮 Community pattern server
- 🔮 Automatic pattern recommendations from aggregated data
- 🔮 Real-time validation status updates
- 🔮 Cross-project transfer learning

## FAQ

**Q: Will this slow down my commands?**
A: No. Telemetry overhead is <0.3% in benchmarks. If disabled completely, zero overhead.

**Q: Can I see what's in my local database?**
A: Yes. It's SQLite at `~/.earlyexit/telemetry.db`. Open with any SQLite browser.

**Q: Can I delete my local data?**
A: Yes. `rm -rf ~/.earlyexit/` or use `earlyexit stats --clear` (coming soon).

**Q: What if I submitted data I shouldn't have?**
A: Comment on your issue/PR and we'll delete it immediately. No questions asked.

**Q: Will you add a feature I suggest?**
A: If data shows it's useful, absolutely! This is community-driven.

**Q: What if the hypothesis is wrong?**
A: Then we publish that! Negative results are valuable. Either way, we learn.

## Get Started

```bash
# 1. Install
pip install earlyexit

# 2. Try it
earlyexit 'Error' your-command

# 3. Export after some usage
earlyexit-export --mask-sensitive > my-data.json

# 4. Submit
# Go to: https://github.com/rsleedbx/earlyexit/issues/new?template=data-submission.md
```

**Thank you for helping validate (or invalidate) this hypothesis!** 🚀

---

*Questions? Open an issue or discussion on GitHub.*

