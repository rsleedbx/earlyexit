# Telemetry Backend Options

## Performance Results

✅ **SQLite overhead is negligible**: 
- Mean: 0.57 ms per execution
- P95: 0.67 ms
- **0.0057% overhead** for a 10-second command

## Backend Options

### 1. SQLite (Default - Local Storage)

**Best for**: Development, personal use, persistent systems

```yaml
# ~/.earlyexit/config.yaml
telemetry:
  backend: sqlite
  sqlite:
    path: ~/.earlyexit/telemetry.db
    wal_mode: true  # Write-Ahead Logging for better concurrency
    retention_days: 90
```

**Pros**:
- ✅ No network dependency
- ✅ Fast (sub-millisecond writes)
- ✅ Complete privacy (local-only)
- ✅ Simple setup (no infrastructure)
- ✅ Works offline

**Cons**:
- ❌ Lost on ephemeral systems (Docker, CI/CD runners)
- ❌ No centralized analysis across machines
- ❌ Manual data export needed

---

### 2. HTTP Endpoint (Remote Storage)

**Best for**: CI/CD, ephemeral containers, team analytics

```yaml
# ~/.earlyexit/config.yaml
telemetry:
  backend: http
  http:
    endpoint: https://telemetry.yourcompany.com/api/v1/events
    api_key: ${EARLYEXIT_API_KEY}  # From environment
    batch_size: 10
    flush_interval: 5  # seconds
    timeout: 2  # seconds
    retry_attempts: 3
    async: true  # Don't block on network
```

**Pros**:
- ✅ Works on ephemeral systems
- ✅ Centralized analytics across team/fleet
- ✅ No data loss on container destruction
- ✅ Can aggregate across many machines

**Cons**:
- ❌ Network dependency
- ❌ Requires infrastructure (API endpoint)
- ❌ Privacy concerns (data leaves machine)
- ❌ Potential latency/failures

---

### 3. Hybrid (SQLite + HTTP)

**Best for**: Maximum flexibility

```yaml
telemetry:
  backend: hybrid
  hybrid:
    local: true   # Store in SQLite first
    remote: true  # Also send to HTTP (async)
    local_primary: true  # Local is source of truth
```

**Behavior**:
1. Write to local SQLite immediately (fast, reliable)
2. Asynchronously batch and send to remote (best effort)
3. If remote fails, data still captured locally
4. Periodic sync retries failed sends

---

### 4. File-Based (Simple Export)

**Best for**: Minimal setup, manual analysis

```yaml
telemetry:
  backend: file
  file:
    path: ~/.earlyexit/telemetry.jsonl  # JSON Lines format
    rotate_size_mb: 100
    compression: gzip
```

**Pros**:
- ✅ Simple, no database
- ✅ Easy to process with standard tools (jq, grep)
- ✅ Easy to share/export

**Cons**:
- ❌ No efficient querying
- ❌ Manual analysis required

---

## Configuration Examples

### Example 1: CI/CD Runner (Ephemeral)

```yaml
# Send to remote, don't persist locally
telemetry:
  enabled: true
  backend: http
  http:
    endpoint: https://analytics.ci.company.com/earlyexit
    api_key_env: CI_TELEMETRY_TOKEN
    async: true
    fire_and_forget: true  # Don't wait for response
  anonymize: true
  scrub_pii: true
```

### Example 2: Developer Laptop (Persistent)

```yaml
# Store locally, optionally sync to team analytics
telemetry:
  enabled: true
  backend: hybrid
  sqlite:
    path: ~/.earlyexit/telemetry.db
    wal_mode: true
  http:
    endpoint: https://team-analytics.company.com/earlyexit
    api_key_env: EARLYEXIT_TEAM_KEY
    opt_in: true  # User must explicitly enable remote
```

### Example 3: Testing/Development

```yaml
# Local only, verbose logging
telemetry:
  enabled: true
  backend: sqlite
  sqlite:
    path: ~/.earlyexit/dev_telemetry.db
  debug: true
```

---

## CLI Options

```bash
# Explicit backend selection
earlyexit --telemetry-backend sqlite 'Error' cmd
earlyexit --telemetry-backend http 'Error' cmd
earlyexit --telemetry-backend none 'Error' cmd  # Disable

# Environment variables
export EARLYEXIT_TELEMETRY_BACKEND=http
export EARLYEXIT_TELEMETRY_ENDPOINT=https://...
export EARLYEXIT_TELEMETRY_API_KEY=...

# One-off remote send (even if configured for local)
earlyexit --telemetry-remote 'Error' cmd
```

---

## HTTP Endpoint Specification

### POST /api/v1/events

**Request**:
```json
{
  "api_version": "1.0",
  "events": [
    {
      "type": "execution",
      "data": {
        "execution_id": "uuid",
        "timestamp": "2025-01-15T10:30:00Z",
        "command_hash": "sha256...",
        "pattern": "Error",
        "exit_code": 0,
        "total_runtime": 45.3,
        "match_count": 1,
        "project_type": "nodejs",
        ...
      }
    },
    {
      "type": "match_event",
      "data": {
        "execution_id": "uuid",
        "match_number": 1,
        "timestamp_offset": 12.5,
        "stream_source": "stderr",
        ...
      }
    }
  ],
  "client": {
    "version": "0.0.1",
    "platform": "darwin",
    "anonymized": true
  }
}
```

**Response**:
```json
{
  "status": "ok",
  "received": 2,
  "warnings": []
}
```

**Authentication**:
- Bearer token in `Authorization` header
- Or API key in `X-API-Key` header

---

## Open Source Backend Implementations

### Option 1: Simple Python Flask API

```python
# Simple receiver that writes to PostgreSQL
from flask import Flask, request, jsonify
import psycopg2

app = Flask(__name__)

@app.route('/api/v1/events', methods=['POST'])
def receive_events():
    data = request.json
    # Validate API key
    # Insert to database
    # Return success
    return jsonify({"status": "ok", "received": len(data['events'])})
```

### Option 2: ClickHouse (High Performance)

ClickHouse is perfect for telemetry data:
- Extremely fast inserts (millions per second)
- Column-oriented (efficient for analytics)
- Built-in compression (10-100x)
- SQL interface

```sql
CREATE TABLE earlyexit_executions (
    execution_id String,
    timestamp DateTime,
    command_hash String,
    pattern String,
    exit_code UInt8,
    total_runtime Float32,
    ...
) ENGINE = MergeTree()
ORDER BY (timestamp, command_hash);
```

### Option 3: OpenTelemetry Collector

Leverage existing observability infrastructure:
```yaml
# Send as OTLP traces
earlyexit --telemetry-backend otlp 'Error' cmd
```

---

## Privacy & Security

### Data Minimization

**Remote backends should only send**:
- ✅ Command hash (not full command)
- ✅ Pattern (already public)
- ✅ Timing metrics
- ✅ Exit codes
- ❌ NO actual command arguments
- ❌ NO file paths
- ❌ NO output content (unless explicitly opted in)

### Anonymization Levels

1. **Minimal** (default for remote):
   ```json
   {
     "command_hash": "sha256...",  // One-way hash
     "pattern": "Error",
     "exit_code": 0,
     "runtime": 45.3
   }
   ```

2. **Full** (opt-in):
   ```json
   {
     "command": "npm test",  // Actual command
     "working_directory": "/project",
     "match_content": "Error: test failed",
     ...
   }
   ```

### Opt-In Flow

```bash
# First time using remote telemetry
$ earlyexit --telemetry-backend http 'Error' npm test

⚠️  Remote telemetry not yet configured.

Remote telemetry sends execution data to a server.
This is useful for CI/CD and team analytics but requires
sending data outside your machine.

Data sent:
  ✓ Command hash (anonymized)
  ✓ Pattern and exit code
  ✓ Timing metrics
  ✗ NO actual commands or output

Configure remote endpoint:
  export EARLYEXIT_TELEMETRY_ENDPOINT=https://...
  export EARLYEXIT_TELEMETRY_API_KEY=...

Or use local-only telemetry:
  earlyexit --telemetry-backend sqlite 'Error' npm test

Continue without telemetry? [y/N]
```

---

## Recommended Architectures

### Architecture 1: Simple Team Setup

```
Developer Laptops (SQLite)
         │
         │ (manual export)
         ↓
    Shared Storage (S3/GCS)
         │
         ↓
    Analysis Scripts
```

### Architecture 2: Production CI/CD

```
CI Runners (ephemeral)
         │
         │ (async HTTP)
         ↓
    API Gateway
         │
         ↓
    ClickHouse DB
         │
         ↓
    Grafana Dashboard
```

### Architecture 3: Hybrid Enterprise

```
Developers (SQLite) ─┐
                     ├──→ Optional HTTP ──→ Team Analytics
CI/CD (HTTP only) ───┘
```

---

## Implementation Phases

### Phase 1: SQLite Only ✅
- Local storage
- No network dependency
- Tested and benchmarked

### Phase 2: File Backend (Simple)
- JSON Lines format
- Easy export/import
- No DB required

### Phase 3: HTTP Backend
- Async posting
- Batching
- Retry logic
- API specification

### Phase 4: Hybrid Mode
- Local + Remote
- Best effort remote sync
- Fallback to local

### Phase 5: Advanced
- OpenTelemetry integration
- ClickHouse native protocol
- Real-time streaming

---

## Performance Comparison

| Backend | Write Latency | Reliability | Setup Complexity |
|---------|--------------|-------------|------------------|
| SQLite | 0.57ms (P50) | ✅ Excellent | ✅ Zero config |
| File | 0.1-1ms | ✅ Excellent | ✅ Minimal |
| HTTP (async) | 0.1ms* | ⚠️ Network-dependent | ⚠️ Requires endpoint |
| HTTP (sync) | 50-200ms | ⚠️ Network-dependent | ⚠️ Requires endpoint |
| Hybrid | 0.6ms | ✅ Best of both | ⚠️ More complex |

*Async: Non-blocking, queued in background

---

## Default Recommendation

**For v1.0 release**:
- ✅ SQLite by default (enabled)
- ✅ HTTP as opt-in (--telemetry-backend http)
- ✅ Easy to disable (--no-telemetry)
- ✅ Clear documentation on privacy

**For CI/CD users**:
- ✅ Detect CI environment variables (CI=true)
- ✅ Suggest HTTP backend
- ✅ Provide example endpoints

```bash
# Auto-detect CI
if [ "$CI" = "true" ]; then
  echo "📊 Detected CI environment"
  echo "Consider: export EARLYEXIT_TELEMETRY_BACKEND=http"
fi
```

---

## Testing the Remote Endpoint

```bash
# Test connectivity
earlyexit telemetry test-http \
  --endpoint https://telemetry.example.com \
  --api-key $KEY

# Dry run (show what would be sent)
earlyexit --telemetry-backend http \
  --telemetry-dry-run \
  'Error' npm test

# Force send a test event
earlyexit telemetry send-test \
  --endpoint https://... \
  --api-key $KEY
```

---

## Summary

✅ **SQLite is fast enough** (0.57ms, negligible overhead)  
✅ **HTTP solves ephemeral systems** (CI/CD, containers)  
✅ **Hybrid gives best of both worlds**  
✅ **Privacy-first with anonymization**  
✅ **Opt-in for remote telemetry**

**Recommendation for testing**: Start with SQLite, add HTTP when needed for CI/CD.

