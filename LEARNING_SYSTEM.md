# Self-Learning System Design

## Overview

`earlyexit` captures execution telemetry in a local SQLite database (`~/.earlyexit/telemetry.db`) to enable:
- **Pattern effectiveness analysis**: Which patterns actually catch errors vs false positives
- **Optimal timing/delay tuning**: ML-driven recommendations for timeout values
- **Anomaly detection**: Identify unusual command behavior patterns
- **Error-driven learning**: Continuous improvement from user feedback

## Data Capture Schema

### 1. Execution Records Table

```sql
CREATE TABLE executions (
    execution_id TEXT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Command Information
    command TEXT NOT NULL,
    command_hash TEXT,  -- SHA256 of command for grouping similar runs
    working_directory TEXT,
    environment_vars TEXT,  -- JSON of relevant env vars
    
    -- Pattern Configuration
    pattern TEXT NOT NULL,
    pattern_type TEXT,  -- 'python_re', 'perl_regex'
    case_insensitive INTEGER,
    invert_match INTEGER,
    max_count INTEGER,
    
    -- Stream Configuration
    match_mode TEXT,  -- 'stdout', 'stderr', 'both'
    fd_patterns TEXT,  -- JSON: {fd_num: pattern}
    
    -- Timeout Configuration
    overall_timeout REAL,
    idle_timeout REAL,
    first_output_timeout REAL,
    delay_exit REAL,
    
    -- Execution Results
    exit_code INTEGER NOT NULL,
    exit_reason TEXT,  -- 'match', 'timeout_overall', 'timeout_idle', 'timeout_first_output', 'completed', 'error'
    
    -- Timing Metrics
    total_runtime REAL,
    time_to_first_output REAL,
    time_to_first_match REAL,
    time_from_match_to_exit REAL,
    idle_periods_count INTEGER,
    longest_idle_period REAL,
    
    -- Match Information
    match_count INTEGER DEFAULT 0,
    match_line_numbers TEXT,  -- JSON array of line numbers
    false_positive_flag INTEGER DEFAULT 0,  -- User can mark later
    
    -- Output Statistics
    total_lines_processed INTEGER,
    stdout_lines INTEGER,
    stderr_lines INTEGER,
    bytes_processed INTEGER,
    
    -- User Feedback (optional, set later)
    user_rating INTEGER,  -- 1-5: was this a good early exit decision?
    user_feedback TEXT,
    should_have_exited INTEGER,  -- NULL/0/1
    optimal_delay_suggestion REAL,
    
    -- ML Features
    project_type TEXT,  -- Detected: 'nodejs', 'python', 'rust', 'terraform', etc.
    command_category TEXT,  -- 'test', 'build', 'deploy', 'unknown'
    
    -- Privacy
    anonymized INTEGER DEFAULT 0
);

CREATE INDEX idx_command_hash ON executions(command_hash);
CREATE INDEX idx_timestamp ON executions(timestamp);
CREATE INDEX idx_exit_reason ON executions(exit_reason);
CREATE INDEX idx_project_type ON executions(project_type);
```

### 2. Match Events Table

```sql
CREATE TABLE match_events (
    event_id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    match_number INTEGER,
    timestamp_offset REAL,  -- Seconds from start of execution
    
    stream_source TEXT,  -- 'stdout', 'stderr', 'fd3', etc.
    line_number INTEGER,
    line_content TEXT,  -- Anonymized if needed
    matched_substring TEXT,
    match_position_start INTEGER,
    match_position_end INTEGER,
    
    context_before TEXT,  -- 3 lines before
    context_after TEXT,   -- 3 lines after
    
    FOREIGN KEY (execution_id) REFERENCES executions(execution_id)
);

CREATE INDEX idx_execution_id ON match_events(execution_id);
```

### 3. Output Samples Table

```sql
CREATE TABLE output_samples (
    sample_id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    
    sample_type TEXT,  -- 'match_context', 'false_positive_candidate', 'missed_error'
    stream_source TEXT,
    timestamp_offset REAL,
    
    content TEXT,  -- Anonymized log segment
    content_hash TEXT,
    
    is_error INTEGER,  -- ML label: was this actually an error?
    confidence REAL,   -- ML confidence score
    
    FOREIGN KEY (execution_id) REFERENCES executions(execution_id)
);
```

### 4. Performance Metrics Table

```sql
CREATE TABLE performance_metrics (
    metric_id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    
    metric_name TEXT,  -- 'cpu_usage_peak', 'memory_mb_peak', 'io_wait_seconds'
    metric_value REAL,
    timestamp_offset REAL,
    
    FOREIGN KEY (execution_id) REFERENCES executions(execution_id)
);
```

### 5. Pattern Effectiveness Summary (Materialized View)

```sql
CREATE TABLE pattern_effectiveness (
    pattern_hash TEXT PRIMARY KEY,
    pattern TEXT,
    
    total_uses INTEGER DEFAULT 0,
    successful_exits INTEGER DEFAULT 0,
    false_positives INTEGER DEFAULT 0,
    missed_errors INTEGER DEFAULT 0,
    
    avg_time_to_match REAL,
    avg_total_runtime REAL,
    
    user_rating_avg REAL,
    effectiveness_score REAL,  -- Calculated metric
    
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Data to Capture

### Critical Features for ML Training

1. **Command Context**:
   - Command string (anonymized if sensitive)
   - Command type/category (test/build/deploy)
   - Project language/framework
   - Working directory structure (anonymized paths)
   - Relevant environment variables (CI=true, NODE_ENV, etc.)

2. **Pattern Effectiveness**:
   - Pattern used
   - Number of matches
   - Time to first match
   - False positive indicators
   - Missed error indicators (from user feedback)

3. **Timing Characteristics**:
   - Time to first output (startup detection)
   - Idle period distribution
   - Time from match to exit (delay effectiveness)
   - Total runtime vs expected runtime

4. **Output Characteristics**:
   - Output volume (lines, bytes)
   - Output rate (lines/second)
   - Error density (errors per line)
   - Stream distribution (stdout vs stderr ratio)

5. **Exit Conditions**:
   - Why did it exit? (match/timeout/hang)
   - Was it the right decision? (user feedback)
   - Optimal delay (actual vs configured)

6. **User Feedback** (key for reinforcement learning):
   - Was early exit correct?
   - Should have waited longer/exited earlier?
   - False positive/negative reports
   - Rating (1-5 stars)

## Privacy & Anonymization

### PII Scrubbing

Automatically detect and anonymize:
- Passwords, tokens, API keys (regex patterns)
- Email addresses
- IP addresses
- File paths (replace with generic `/project/src/file.js`)
- User names
- Hostnames

### Opt-in Levels

```bash
# Disable all telemetry
earlyexit --no-telemetry 'pattern' cmd

# Anonymous telemetry only (default)
earlyexit --telemetry=anonymous 'pattern' cmd

# Full telemetry with PII scrubbing
earlyexit --telemetry=full 'pattern' cmd
```

## ML Use Cases

### 1. Pattern Recommendation Engine

Given: command type, language, past executions
Suggest: optimal error patterns

```python
# Example: earlyexit learns that for Node.js tests, 
# pattern 'FAIL|Error' works better than just 'Error'
recommended_pattern = ml_model.suggest_pattern(
    command="npm test",
    project_type="nodejs"
)
```

### 2. Optimal Delay Tuning

Given: command type, past match-to-exit times
Suggest: optimal `--delay-exit` value

```python
# Learn that Python tests need 15s delay (stack traces),
# but shell scripts only need 2s
optimal_delay = ml_model.suggest_delay(
    command="pytest",
    project_type="python"
)
```

### 3. Anomaly Detection

Detect unusual behavior:
- Command taking much longer than usual
- Unexpected error patterns
- Unusual output characteristics

### 4. False Positive Reduction

Learn which matches are false positives:
- "Error" in log messages that aren't actual errors
- Stack traces that are warnings, not failures

## Storage Backends

See **[TELEMETRY_BACKENDS.md](TELEMETRY_BACKENDS.md)** for complete backend options:

### SQLite (Default)
- ✅ **Performance**: 0.57ms overhead (0.0057% for 10s command)
- ✅ Local storage, complete privacy
- ✅ Works offline
- ⚠️ Lost on ephemeral systems

### HTTP Remote
- ✅ Works on CI/CD, containers
- ✅ Centralized team analytics
- ⚠️ Network dependency
- ⚠️ Requires infrastructure

### Hybrid
- ✅ Best of both: local + remote
- ✅ No data loss, async sync

## Implementation Phases

### Phase 1: Basic Telemetry (MVP)
- ✅ Capture execution metadata
- ✅ Record match events
- ✅ Store in SQLite locally
- ✅ CLI to view/export data
- ✅ **Performance validated**: <1ms overhead ✅

### Phase 2: User Feedback
- Interactive feedback prompts (opt-in)
- `earlyexit report <execution_id>` command
- Feedback API for external tools

### Phase 3: Local Analysis
- Pattern effectiveness reports
- Timing analysis dashboards
- Recommendations CLI

### Phase 4: ML Training Pipeline
- Feature engineering
- Model training (optional cloud sync)
- Inference for real-time suggestions

### Phase 5: Federated Learning (Future)
- Privacy-preserving model updates
- Community pattern library
- Opt-in model sharing

## Command-Line Interface

```bash
# View recent executions
earlyexit stats

# View pattern effectiveness
earlyexit analyze patterns

# Get recommendations
earlyexit suggest 'npm test'

# Provide feedback on last run
earlyexit feedback --rating 5 --comment "Perfect timing"

# Export data for analysis
earlyexit export --format json > data.json

# Clear telemetry data
earlyexit clear-data --older-than 30d
```

## Data Retention

- Default: Keep 90 days of data
- Automatic cleanup of old records
- Configurable: `~/.earlyexit/config.yaml`

```yaml
telemetry:
  enabled: true
  level: anonymous  # anonymous, full, none
  retention_days: 90
  max_db_size_mb: 100
  anonymize_paths: true
  anonymize_commands: true
```

## Research References

Based on ML best practices:
- **Error-driven learning**: Adjust parameters based on outcome feedback
- **Reinforcement learning**: Reward successful early exits, penalize false positives
- **Anomaly detection**: Detect deviations from normal execution patterns
- **Concept drift**: Adapt as projects/patterns evolve over time
- **Active learning**: Request user feedback on uncertain cases

## Benefits

1. **For Users**:
   - Automatic optimization of timeouts/delays
   - Better pattern suggestions
   - Reduced false positives over time
   - Project-specific tuning

2. **For AI Agents**:
   - Learn optimal parameters for different project types
   - Reduce trial-and-error iterations
   - Build confidence in autonomous decisions

3. **For Community**:
   - Share effective patterns (opt-in)
   - Collective intelligence
   - Faster improvement

## Example: Self-Improving Pattern

```bash
# First run: User tries a pattern
earlyexit 'Error' npm test
# Exit code 0, took 45s, delay was too long

# User provides feedback
earlyexit feedback --delay-should-be 10

# System learns and suggests next time
earlyexit suggest 'npm test'
# Suggests: earlyexit --delay-exit 10 'Error|FAIL' npm test

# Over time, learns project-specific patterns
# and automatically applies them
```

This creates a **virtuous cycle** of improvement!

