# Interactive Learning Mode - Implementation Roadmap

## Executive Summary

Transform `earlyexit` from "expert tool with complex flags" to "intelligent assistant that learns from you" through three phases:

1. **Phase 1 (MVP)**: Interactive watch mode with Ctrl+C learning
2. **Phase 2**: AI assistant discoverability and shell integration  
3. **Phase 3**: Community-powered telemetry sharing

## Phase 1: Interactive Watch Mode (MVP) - 4 weeks

### Week 1: Core Watch Mode

**Goal**: `earlyexit npm test` runs in watch mode, captures all output

**Tasks**:
1. Update argument parser to detect no-pattern mode
   ```python
   # If no pattern and command provided → watch mode
   if not args.pattern and args.command:
       return run_watch_mode(args)
   ```

2. Create `earlyexit/watch_mode.py`:
   ```python
   def run_watch_mode(command, output_buffer_size=1000):
       """Run command in watch mode, capture all output"""
       - Track all output lines with timestamps
       - Monitor both stdout/stderr
       - Store in circular buffer (last N lines)
       - Pass through to terminal in real-time
       - Return on normal exit or SIGINT
   ```

3. Register SIGINT handler:
   ```python
   signal.signal(signal.SIGINT, handle_interrupt)
   ```

4. Tests:
   - Watch mode activates when no pattern
   - All output captured
   - SIGINT handled gracefully

**Deliverable**: User can run `earlyexit npm test`, see all output, Ctrl+C to stop

---

### Week 2: Interactive Learning (Ctrl+C Handler)

**Goal**: When user hits Ctrl+C, ask what they saw and learn from it

**Tasks**:
1. Implement interactive prompts in `earlyexit/interactive.py`:
   ```python
   def handle_interrupt(output_buffer, start_time):
       """Handle Ctrl+C with learning prompts"""
       1. Show context (runtime, last lines, hang detection)
       2. Ask: Why did you stop? (error/timeout/hang/success/other)
       3. If error: Extract patterns from output
       4. If timeout: Calculate suggested timeouts
       5. Save to telemetry
   ```

2. Pattern extraction algorithm:
   ```python
   def extract_patterns(output_lines):
       """Find potential error patterns in output"""
       - Look for: ERROR, FAIL, Exception, Traceback, etc.
       - Frequency analysis (words appearing 1-5 times)
       - Line context (errors often near end)
       - Return top 5 candidates
   ```

3. Timeout calculation:
   ```python
   def suggest_timeouts(runtime, last_output_time):
       """Suggest timeout values based on behavior"""
       - Overall: runtime + 10% buffer
       - Idle: (runtime - last_output_time) * 1.5
       - Delay-exit: Keep default 10s
   ```

4. Save session data:
   ```sql
   INSERT INTO user_sessions (
       command, stop_reason, selected_pattern,
       suggested_timeout, output_excerpt
   );
   ```

5. Tests:
   - Prompt displays correctly
   - Pattern extraction finds common errors
   - Timeout calculation reasonable
   - Session saved to DB

**Deliverable**: User gets intelligent prompts on Ctrl+C, choices saved

---

### Week 3: Smart Suggestions

**Goal**: On second run, suggest learned settings

**Tasks**:
1. Check for previous runs before starting:
   ```python
   def check_suggestions(command, project_type):
       """Look up learned settings from previous runs"""
       - Query user_sessions for this command
       - Calculate confidence (recency, success rate)
       - Return top suggestion
   ```

2. Display suggestion prompt:
   ```
   💡 Last time you watched for 'FAIL' and stopped after 45s
   
   Apply these settings?
     Pattern: 'FAIL|ERROR'
     Timeout: 50s (overall), 5s (idle)
   
   [Y] Yes  [n] No (watch mode)  [e] Edit  [?] Explain
   ```

3. Implement `--auto-tune` flag:
   ```python
   if args.auto_tune:
       suggestions = get_best_suggestions(command)
       apply_suggestions_silently(suggestions)
   ```

4. Create `learned_settings` table:
   ```sql
   CREATE TABLE learned_settings (
       command TEXT,
       project_type TEXT,
       pattern TEXT,
       overall_timeout REAL,
       idle_timeout REAL,
       confidence REAL,
       uses INTEGER,
       PRIMARY KEY (command, project_type)
   );
   ```

5. Tests:
   - Suggestions retrieved correctly
   - Auto-tune applies settings
   - Confidence scoring works
   - User can override suggestions

**Deliverable**: Second run shows suggestions, auto-tune works

---

### Week 4: Polish & Documentation

**Goal**: Phase 1 ready for beta users

**Tasks**:
1. Error handling and edge cases
2. Add `earlyexit watch COMMAND` explicit syntax
3. Documentation:
   - Quick start guide
   - Interactive mode tutorial
   - Video demo (animated GIF)
4. Tests:
   - Integration tests
   - User workflow tests
   - Telemetry tests
5. Beta user testing (10-20 users)

**Deliverable**: Phase 1 MVP ready for release

---

## Phase 2: AI Discoverability - 2 weeks

### Week 5: Documentation Restructure

**Goal**: Make earlyexit easy for AI assistants to recommend

**Tasks**:
1. README restructure:
   ```markdown
   # Quick Start (for first-time users)
   ## Common Use Cases
   ### vs timeout
   ### vs grep
   ### vs manual watching
   ```

2. Create `AI_ASSISTANT_GUIDE.md`:
   - When to recommend earlyexit
   - Copy-paste examples
   - Decision tree
   - Integration patterns

3. Keyword optimization:
   - "intelligent timeout"
   - "automatic error detection"
   - "learn from command behavior"

4. Example gallery:
   - npm test
   - pytest
   - terraform apply
   - docker build
   - CI/CD integration

**Deliverable**: AI-friendly documentation

---

### Week 6: Shell Integration

**Goal**: Make earlyexit easy to adopt

**Tasks**:
1. Post-install setup command:
   ```bash
   earlyexit setup
   # Interactive prompts for:
   # - Shell alias (ee)
   # - Completion scripts
   # - Telemetry preferences
   ```

2. Shell completion:
   ```bash
   # Bash
   complete -C earlyexit-completion earlyexit
   
   # Zsh
   compdef _earlyexit earlyexit
   ```

3. Helpful tips in output:
   ```
   ✅ Pattern matched!
   💡 Tip: Run 'earlyexit --auto-tune npm test' next time for automatic settings
   ```

4. Tests:
   - Setup command works
   - Completion scripts work
   - Tips display correctly

**Deliverable**: Easy setup, discoverable features

---

## Phase 3: Community Telemetry (Future - 6-8 weeks)

### Architecture

```
Local-first, opt-in sharing:
  1. All features work offline (SQLite)
  2. Sharing is explicit opt-in
  3. Privacy controls at every step
  4. Backend is optional enhancement
```

### Implementation Steps

1. **Backend API** (2 weeks):
   - FastAPI or Flask
   - PostgreSQL database
   - Pattern aggregation endpoints
   - Community voting

2. **Privacy Controls** (1 week):
   - Opt-in sharing CLI
   - Review what's shared
   - Revoke at any time
   - PII scrubbing audit

3. **Contribution Flow** (1 week):
   - `earlyexit telemetry share`
   - Upload anonymized data
   - Track contributions
   - Reputation system

4. **Community Features** (2 weeks):
   - Pattern search
   - Voting on patterns
   - Version-specific patterns
   - Enterprise private deployments

5. **Testing & Launch** (2 weeks):
   - Beta with early adopters
   - Security audit
   - Privacy review
   - Public launch

---

## Success Criteria

### Phase 1:
- ✅ 80%+ users try watch mode
- ✅ 60%+ accept suggestions on run 2
- ✅ < 5min to first successful pattern

### Phase 2:
- ✅ AI assistants recommend earlyexit
- ✅ 50%+ new users from AI tools
- ✅ 2x GitHub star growth

### Phase 3:
- ✅ 1000+ users sharing
- ✅ 100+ community patterns
- ✅ 90%+ accuracy for top commands

---

## Resource Requirements

### Phase 1 (MVP):
- **Developer time**: 1 dev, 4 weeks full-time
- **Beta testers**: 10-20 users
- **Infrastructure**: None (local SQLite)

### Phase 2 (Discoverability):
- **Developer time**: 1 dev, 2 weeks
- **Documentation writer**: Optional (can be dev)
- **Marketing**: Outreach to AI tool makers

### Phase 3 (Community):
- **Developer time**: 1-2 devs, 6-8 weeks
- **Backend infrastructure**: 
  - Hosting: $50-100/month initially
  - Database: PostgreSQL
  - Monitoring: Sentry, Datadog
- **Security audit**: $5k-10k (one-time)
- **Legal review**: Privacy policy, terms

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Users don't engage with prompts | High | Make prompts optional, default to watch mode |
| Pattern extraction too noisy | Medium | Allow custom patterns, improve algorithm |
| Privacy concerns | High | Strict opt-in, transparent sharing, audit |
| Backend costs escalate | Medium | Start with free tier limits, freemium model |
| AI tools don't adopt | High | Direct partnerships, clear value prop |

---

## Next Actions

1. **Immediate**: Approve Phase 1 implementation plan
2. **This week**: Start Week 1 tasks (watch mode core)
3. **Week 2**: User testing of watch mode
4. **Week 4**: Beta release announcement
5. **Month 2**: Phase 2 rollout
6. **Month 3-4**: Evaluate Phase 3 need based on adoption

---

**Status**: Ready for implementation  
**Decision needed**: Approve Phase 1 scope and timeline  
**Next review**: Weekly progress check-ins




