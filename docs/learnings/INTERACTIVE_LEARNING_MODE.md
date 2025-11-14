# Interactive Learning Mode - Design Document

## Vision

Make `earlyexit` learn from user behavior to provide zero-configuration intelligent monitoring:

```bash
# Current: User must know pattern and timeout
earlyexit -t 300 'ERROR|FAIL' -- npm test

# Future: Just run it, earlyexit learns
earlyexit npm test
# User watches output, presses Ctrl+C when they see error
# earlyexit: "I noticed 'FAIL' appeared 5 times. Should I watch for this?"
```

## Problem Statement

**Current friction points:**
1. Users don't know what error patterns to watch for
2. Users don't know appropriate timeout values
3. Requires reading docs before first use
4. Not discoverable by AI assistants
5. Each user learns in isolation (no community benefit)

**Target user experience:**
1. First time: `earlyexit npm test` → Watch mode, learn from Ctrl+C
2. Second time: `earlyexit npm test` → "Suggestion: watch for 'FAIL' (from last run)"
3. Third+ time: `earlyexit --auto-tune npm test` → Applies learned settings automatically

## Phase 1: Interactive Watch Mode (MVP)

### 1.1 Zero-Config Command Execution

**Syntax detection:**
```bash
# If no pattern provided and command detected, enter watch mode
earlyexit npm test              # Watch mode
earlyexit -- npm test           # Watch mode (explicit)
earlyexit watch npm test        # Watch mode (explicit)

# Pattern provided = normal mode
earlyexit 'ERROR' npm test      # Normal mode
earlyexit 'ERROR' -- npm test   # Normal mode
```

**Watch mode behavior:**
- Pass through all output (no filtering)
- Monitor both stdout and stderr
- Record all output with timestamps
- Track line numbers and content
- Capture system metrics (runtime, output volume)

### 1.2 Intelligent Ctrl+C Handling

**On SIGINT (Ctrl+C):**

1. **Capture context:**
   - Last 100 lines of output
   - Last 20 lines on screen (terminal visible area)
   - Time when Ctrl+C pressed
   - Total runtime so far
   - Process state (running/hanging)

2. **Interactive feedback:**
   ```
   ⚠️  Interrupted at 45.3s (output stopped at 42.1s)
   
   What made you stop?
   1. 🚨 Error detected (I saw failure output)
   2. ⏱️  Taking too long (timeout needed)
   3. 🔇 No output (process hung/stuck)
   4. ✅ Success (I saw what I needed)
   5. 👤 Other (manual stop)
   
   Your choice [1-5]: _
   ```

3. **Pattern extraction (if option 1):**
   ```
   Last 20 lines before you stopped:
   
   18: Running test suite...
   19: ✓ test_basic passed
   20: ✗ test_advanced FAILED
   21:   Expected: 200
   22:   Got: 500
   23: ERROR: Test suite failed
   24: Build failed with 1 error
   
   I found these potential patterns:
   1. FAILED (appeared 1 time, line 20)
   2. ERROR (appeared 1 time, line 23)
   3. failed (appeared 2 times, lines 23, 24)
   4. [Custom pattern]
   
   Which pattern should I watch for? [1-4]: _
   ```

4. **Timeout suggestion (if option 2):**
   ```
   You stopped after 45.3s.
   Last output was at 42.1s (hung for 3.2s).
   
   Recommended timeouts:
   • Overall: 50s (10% buffer)
   • Idle: 5s (detect hangs faster)
   
   Save these settings for next time? [y/n]: _
   ```

5. **Save to telemetry:**
   - User's choice (error/timeout/hang/success)
   - Selected pattern (if any)
   - Suggested timeout values
   - Command and project context
   - Anonymized output excerpt (opt-in)

### 1.3 Smart Suggestions on Next Run

**Command history matching:**
```bash
$ earlyexit npm test

💡 Suggestion based on your last run (45s ago):
   Pattern: 'FAILED|ERROR'
   Timeout: 50s (overall), 5s (idle)
   Delay: 10s (capture error context)

Use suggestion? [Y/n/edit]: _

[Y] → Runs with suggested settings
[n] → Runs in watch mode again
[edit] → Prompts for custom settings
```

**Project-specific learning:**
- Detects project type (package.json → Node, pyproject.toml → Python)
- Stores settings per project
- Different projects get different suggestions

### 1.4 Implementation Plan

**Files to modify:**

1. **`earlyexit/cli.py`**:
   - Detect when no pattern provided
   - Add watch mode flag/logic
   - Implement SIGINT handler with user prompts
   - Pattern extraction from recent output
   - Integration with telemetry

2. **`earlyexit/telemetry.py`**:
   - New table: `user_sessions`
     ```sql
     CREATE TABLE user_sessions (
       session_id TEXT PRIMARY KEY,
       command TEXT,
       project_path TEXT,
       project_type TEXT,
       stop_reason TEXT,  -- 'error', 'timeout', 'hung', 'success', 'manual'
       stop_time REAL,
       selected_pattern TEXT,
       suggested_timeout REAL,
       output_excerpt TEXT,  -- last 100 lines (PII-scrubbed)
       timestamp REAL
     );
     ```
   - New table: `learned_settings`
     ```sql
     CREATE TABLE learned_settings (
       command TEXT,
       project_type TEXT,
       pattern TEXT,
       overall_timeout REAL,
       idle_timeout REAL,
       delay_exit REAL,
       confidence REAL,  -- 0-1, based on success rate
       uses INTEGER,
       last_used REAL,
       PRIMARY KEY (command, project_type)
     );
     ```

3. **`earlyexit/interactive.py`** (new):
   - `watch_mode()` - Main watch mode orchestration
   - `handle_interrupt()` - SIGINT handler with prompts
   - `extract_patterns()` - Find common error patterns
   - `suggest_from_output()` - Analyze recent lines
   - `prompt_user()` - Interactive CLI prompts
   - `save_session()` - Save learning session

4. **`earlyexit/suggestion.py`** (new):
   - `get_suggestions()` - Retrieve learned settings
   - `rank_suggestions()` - Score by recency, success, context
   - `apply_suggestions()` - Auto-apply learned settings
   - `format_suggestion_prompt()` - Display suggestions

## Phase 2: AI Assistant Discoverability

### 2.1 README Restructure

**New "Quick Start" at top:**
```markdown
# 🚀 Quick Start (First Time Users)

Never used `earlyexit` before? Start here:

## 1. First Run: Watch & Learn
```bash
earlyexit npm test
# Watch output, press Ctrl+C when you see an error or timeout
# earlyexit learns from your behavior
```

## 2. Next Run: Smart Suggestions
```bash
earlyexit npm test
# "💡 Watch for 'FAILED|ERROR'? [Y/n]"
# Press Y to use learned settings
```

## 3. Always Use Learned Settings
```bash
earlyexit --auto-tune npm test
# Automatically applies best settings based on history
```

## Why earlyexit vs timeout/tee?

| Tool | Purpose | Limitation | earlyexit Solution |
|------|---------|------------|-------------------|
| `timeout 100 cmd 2>&1 \| tee log` | Time limit + log | Fixed timeout, no pattern matching | ✅ Learns optimal timeout from your behavior |
| `cmd \| grep -m1 ERROR` | Stop on error | Doesn't run command, no context | ✅ Runs command, captures full error context |
| Manual watching | Spot errors | Requires human attention | ✅ Watches for you, captures context automatically |
```

### 2.2 AI-Friendly Documentation

**New file: `AI_ASSISTANT_GUIDE.md`**
- Clear use case patterns for AI to recommend
- Copy-paste ready examples
- Decision tree for when to use earlyexit
- Integration examples (CI/CD, local dev)

**Keyword optimization:**
- "alternative to timeout"
- "intelligent timeout with error detection"
- "automatically stop on error"
- "capture error context"
- "learn from command failures"

### 2.3 Shell Integration

**Post-install helper:**
```bash
# After `pip install earlyexit`
earlyexit setup

Options:
1. Add shell alias: alias ee='earlyexit'
2. Add intelligent wrapper: timeout() { earlyexit -t "$@"; }
3. Add shell completion
4. Enable telemetry sharing (help improve suggestions)
5. Skip setup

Your choice: _
```

**Shell completion:**
- Bash/Zsh completion scripts
- Suggest recently used commands
- Show available patterns for command

## Phase 3: Community Telemetry (Future)

### 3.1 Opt-In Sharing

**Privacy-first design:**
```bash
earlyexit telemetry enable --share

What would you like to share?
1. ✅ Command patterns (e.g., "npm test" → watch for "FAIL")
2. ✅ Optimal timeouts per command
3. ✅ Project type patterns (Node, Python, etc.)
4. ⬜ Anonymized output excerpts (helps pattern detection)
5. ⬜ Error message templates

Sharing preferences saved.
Your contributions help 1,247 other users!
```

**What's shared:**
- Command name (not full path, not arguments with secrets)
- Pattern that worked
- Timeout values
- Project type
- Success/failure outcome
- Opt-in: Anonymized output excerpts (PII-scrubbed)

**What's NOT shared:**
- Usernames, paths, file contents
- API keys, tokens, credentials
- Company/project names
- Specific error messages (unless opted in and scrubbed)

### 3.2 Backend Service

**API endpoints:**
```
GET /api/v1/suggest?command=npm+test&project_type=node
→ Returns community-voted patterns and timeouts

POST /api/v1/contribute
→ Submits anonymized telemetry

GET /api/v1/patterns?search=pytest
→ Returns all known patterns for command
```

**Community voting:**
- Users can upvote/downvote suggestions
- Patterns ranked by effectiveness (success rate)
- Version-specific patterns (e.g., pytest 7.x vs 8.x)

**Registration (optional):**
- Track contributions
- Reputation/karma system
- Access to premium patterns (e.g., enterprise tools)
- Priority support

### 3.3 Integration Architecture

```
┌─────────────┐
│ Local User  │
└──────┬──────┘
       │
       ├─ Local SQLite (always works, offline-first)
       │  └─ ~/.earlyexit/telemetry.db
       │
       └─ HTTP Backend (optional, opt-in)
          ├─ Fetch community suggestions
          ├─ Submit anonymized telemetry
          └─ Sync learned patterns across machines

┌──────────────────────────────────────┐
│ Backend (Future)                     │
├──────────────────────────────────────┤
│ • Pattern aggregation                │
│ • Community voting                   │
│ • ML-powered recommendations         │
│ • Cross-user pattern discovery       │
│ • Enterprise private deployments     │
└──────────────────────────────────────┘
```

## Implementation Roadmap

### Sprint 1: Interactive Watch Mode (1-2 weeks)
- [ ] Detect no-pattern mode → watch mode
- [ ] SIGINT handler with user prompts
- [ ] Pattern extraction from output
- [ ] Save to telemetry (new tables)
- [ ] Basic suggestions on next run
- [ ] Tests for interactive mode

### Sprint 2: Smart Suggestions (1 week)
- [ ] `learned_settings` table and logic
- [ ] Confidence scoring
- [ ] Auto-tune flag implementation
- [ ] Project-type detection enhancement
- [ ] Command history matching

### Sprint 3: Documentation & Discoverability (1 week)
- [ ] README restructure (Quick Start first)
- [ ] AI_ASSISTANT_GUIDE.md
- [ ] Shell completion scripts
- [ ] `earlyexit setup` command
- [ ] Example gallery (common use cases)

### Sprint 4: Community Prep (Future)
- [ ] Backend API design
- [ ] Privacy controls UI
- [ ] Contribution/sharing CLI
- [ ] Beta testing with early adopters
- [ ] Marketing/outreach to AI tool makers

## Success Metrics

### Phase 1 (Interactive Mode):
- 80%+ of users try watch mode on first use
- 60%+ of users accept suggestions on second use
- Average time to first successful pattern: < 5 minutes

### Phase 2 (Discoverability):
- Recommendations by AI assistants (Cursor, Claude, etc.)
- 50%+ of new users come from AI tool recommendations
- GitHub stars growth rate

### Phase 3 (Community):
- 1000+ users opt-in to sharing
- 100+ community-contributed patterns
- 90%+ pattern accuracy for top 50 commands

## Open Questions

1. **Pattern extraction algorithm**: Regex? ML? Simple keyword frequency?
2. **Timeout calculation**: Percentile-based? Mean + std dev? User preference?
3. **Privacy review**: External audit before community launch?
4. **Monetization**: Free tier + paid enterprise? Open source + hosted service?
5. **AI partnership**: Direct integration with Cursor/Claude/GitHub Copilot?

## Next Steps

1. Implement Sprint 1 (Interactive Watch Mode)
2. User testing with 10-20 beta users
3. Iterate based on feedback
4. Document lessons learned
5. Plan Phase 2 rollout

---

**Status**: Design phase - Ready for implementation
**Owner**: Core team
**Timeline**: Phase 1 (4 weeks), Phase 2 (2 weeks), Phase 3 (TBD)




