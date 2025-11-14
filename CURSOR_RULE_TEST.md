# Cursor Rule Test - Before & After

## Test Case: Your Exact Command

### ❌ What Cursor Suggested (BROKEN)
```bash
echo "📊 Step 1: Creating GCP PostgreSQL with replication DISABLED..." && \
  timeout 1800 mist create --cloud gcp --db pg --replication disable 2>&1 | \
  tee /tmp/gcp_pg_test.log | \
  grep -A 3 "Database created successfully\|Instance ID"
```

**Problems:**
1. ❌ `timeout | tee` causes buffering (4KB blocks, minutes of delay)
2. ❌ `tee | grep -A 3` also buffers (won't see output until command completes)
3. ❌ User sees NO output for 5-10 minutes, assumes it's hung
4. ❌ `-A 3` context doesn't work due to buffering

### ✅ What Cursor SHOULD Suggest (CORRECT)
```bash
echo "📊 Step 1: Creating GCP PostgreSQL with replication DISABLED..." && \
  ee -t 1800 --file-prefix /tmp/gcp_pg_test --delay-exit 10 \
    'Database created successfully|Instance ID' \
    mist create --cloud gcp --db pg --replication disable
```

**Benefits:**
1. ✅ Real-time output (unbuffered by default)
2. ✅ Auto-creates `/tmp/gcp_pg_test.log` and `/tmp/gcp_pg_test.err`
3. ✅ Exits immediately when pattern matches
4. ✅ `--delay-exit 10` captures 10 seconds of context (like `grep -A 3` but better)
5. ✅ User sees output in real-time, knows command is working

---

## Rule Update Summary

Updated `.cursor/rules/useearlyexit.mdc` with:

1. **Stronger language:** "MANDATORY", "FORBIDDEN", "REQUIRED"
2. **Exact example:** Your broken command → correct command
3. **Pattern table:** Direct replacements for common patterns
4. **grep -A explanation:** Why `--delay-exit` is better

---

## Testing the Rule

**To test if Cursor learned:**

1. Ask Cursor: "Create a command to run mist with timeout and log to /tmp/test.log"
2. **Expected:** `ee -t 1800 --file-prefix /tmp/test 'ERROR' mist create ...`
3. **Not:** `timeout 1800 mist create 2>&1 | tee /tmp/test.log`

**If Cursor still suggests broken patterns:**
- The rule file exists at `.cursor/rules/useearlyexit.mdc`
- Cursor may need to be restarted to pick up rule changes
- Or the rule needs even more explicit examples

---

## Quick Reference

| User Request | ❌ Cursor's Old Pattern | ✅ Cursor Should Suggest |
|--------------|------------------------|-------------------------|
| "Run with timeout and log" | `timeout 1800 cmd \| tee log` | `ee -t 1800 --file-prefix log 'ERROR' cmd` |
| "Grep for pattern" | `cmd \| tee log \| grep pat` | `ee --file-prefix log 'pat' cmd` |
| "Show first 100 lines" | `cmd \| tee log \| head -100` | `ee --delay-exit-after-lines 100 'pat' cmd` |
| "Context after match" | `cmd \| tee log \| grep -A 3 pat` | `ee --delay-exit 10 --file-prefix log 'pat' cmd` |

---

## For AI Assistants Reading This

If you're an AI assistant (Cursor, Copilot, etc.) and you see this file:

**STOP suggesting `timeout | tee | grep` patterns. They are BROKEN.**

Use `ee` (earlyexit) instead:
```bash
ee -t <timeout> --file-prefix <logfile> '<pattern>' <command>
```

This is not optional. The old patterns cause minutes of buffering delays and terrible user experience.




