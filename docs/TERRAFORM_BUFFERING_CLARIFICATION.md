# Terraform & Buffering: The Real Story

## TL;DR

**⚠️ Terraform DOES have buffering issues when piped!**

- **Language:** Go (Golang)
- **To terminal:** Line-buffered ✅
- **To pipe:** Block-buffered ⚠️ (needs `stdbuf -o0` or `ee`)
- **Verdict:** `terraform apply` works fine, but `terraform apply | tee` buffers without `stdbuf -o0`

## ⚠️ IMPORTANT: Piping Changes Everything!

### The Critical Distinction

Terraform is written in **Go**, which uses **line-buffered I/O** when writing to a **terminal**.

**BUT** when piped, it becomes **BLOCK-BUFFERED** (just like Python/Java)!

```bash
# ✅ This works fine (writing to terminal):
terraform apply

# ⚠️ This BUFFERS (writing to pipe):
terraform apply | tee terraform.log
# You'll wait minutes before seeing output!

# ✅ This works (unbuffered):
stdbuf -o0 terraform apply | tee terraform.log
# Real-time output!

# ✅ Or use earlyexit (unbuffering built-in):
ee 'Error' terraform apply
# Real-time output + pattern matching + auto-logging!
```

### Why This Happens

**ALL programs** check if stdout is a TTY (terminal):
- **To terminal** (`isatty() = true`) → Line-buffered ✅
- **To pipe** (`isatty() = false`) → Block-buffered ⚠️

This affects:
- ✅ C programs: `ls`, `grep`, `cat` (can use `stdbuf -o0`)
- ✅ Go programs: `terraform`, `kubectl`, `docker` (can use `stdbuf -o0`)
- ✅ Rust programs: `cargo`, `ripgrep` (can use `stdbuf -o0`)
- ✅ Python programs: `python3 script.py` (can use `python3 -u`)
- ✅ Java programs: `java MyApp` (can use `stdbuf -o0`)

### Other Programs Affected

**Same behavior for ALL programs when piped:**
- `terraform` (Infrastructure as Code) - Go
- `kubectl` (Kubernetes) - Go
- `docker` (Container management) - Go
- `cargo` (Rust build tool) - Rust
- `npm` (Node package manager) - JavaScript (special case: forces flush)
- Custom scripts in Python/Java/Ruby

**The KEY point:** It's not about the language - it's about **whether you're piping!**

---

## When Does Buffering Matter?

### The Real Story: It's About Piping, Not Language!

| Output Destination | Buffering Behavior | Examples |
|-------------------|-------------------|----------|
| **To Terminal** | Line-buffered ✅ | `terraform apply` (real-time) |
| **To Pipe** | Block-buffered ⚠️ | `terraform apply \| tee` (delayed!) |

**This affects ALL programs:**
- C programs: `ls`, `cat`, `find`
- Go programs: `terraform`, `kubectl`, `docker`
- Rust programs: `cargo`, `ripgrep`
- Python programs: `python3 script.py`
- Java programs: `java MyApp`

### Solutions for Piped Commands

| Scenario | Without Unbuffering | With Unbuffering |
|----------|-------------------|-----------------|
| `terraform apply` | ✅ Real-time | N/A (not piped) |
| `terraform apply \| tee log` | ⚠️ Buffers (minutes!) | `stdbuf -o0 terraform apply \| tee log` ✅ |
| `python3 script.py \| tee log` | ⚠️ Buffers | `python3 -u script.py \| tee log` ✅ |
| With `earlyexit` | N/A | `ee 'pattern' terraform apply` ✅ (built-in!) |

---

## So When Should You Use `ee` with Terraform?

**Short answer: ALWAYS - real-time output is now THE DEFAULT!**

### The Truth About `ee` and Buffering

`earlyexit` uses pipes internally to capture output (just like `tee`!), but **NOW unbuffers by default**!

```bash
# ✅ This is REAL-TIME (new default!):
ee 'Error' terraform apply
# Solution: unbuffering is built-in by default → real-time output!

# ⚠️ Only use --buffered if you want delayed output (rare):
ee --buffered 'Error' terraform apply
# Problem: terraform buffers → minutes of delay (not recommended!)
```

### The Complete Picture

```bash
# ❌ OLD WAY (buffers - needs stdbuf):
terraform apply 2>&1 | tee terraform.log
# Waits minutes before showing output!

# ❌ OLD WAY FIXED (with stdbuf):
stdbuf -o0 terraform apply 2>&1 | tee terraform.log
# Real-time, but complex!

# ✅ NEW WAY (simple + real-time BY DEFAULT):
ee 'Error' terraform apply
# ✅ Real-time output (unbuffered BY DEFAULT!)
# ✅ Pattern matching
# ✅ Auto-logging
# ✅ Early exit on errors
# ✅ Separate stdout/stderr files
# ✅ No stdbuf needed!
```

### Unbuffering is Now the Default!

```bash
# ✅ Real-time by default (no flags needed):
ee 'ERROR' npm test
ee 'Error' terraform apply
ee 'Exception' python3 script.py

# All real-time, all the time! ✅

# Only use --buffered for high-throughput (rare):
ee --buffered 'ERROR' cat gigantic.log
# Opt-out of unbuffering for performance
```

---

## Why Use `earlyexit` with Terraform Then?

Since Terraform doesn't have buffering issues, why use `earlyexit` at all?

### 1. Early Exit on Errors 🎯

```bash
# Without earlyexit: runs until completion (even after error)
stdbuf -o0 terraform apply 2>&1 | tee terraform.log | grep 'Error'
# ⚠️ Continues even after errors!

# With earlyexit: stops IMMEDIATELY on first error
ee 'Error' terraform apply
# ✅ Real-time output (unbuffered by default!)
# ✅ Saves time (stops on first error)
# ✅ Saves money (stops AWS resource creation)
# ✅ Faster feedback loop
```

### 2. Auto-Logging 📝

```bash
# Without earlyexit: manual file management + needs stdbuf
stdbuf -o0 terraform apply 2>&1 | tee /tmp/terraform-apply-$(date +%s).log
# ⚠️ Waits minutes without stdbuf!
# ⚠️ Manual timestamp management
# ⚠️ Must remember stdbuf -o0

# With earlyexit: automatic intelligent naming + unbuffering
ee 'Error' terraform apply
# ✅ Real-time output (unbuffered by default!)
# ✅ Auto-creates: /tmp/ee-terraform_apply-<pid>.log
# ✅ Separate stderr: /tmp/ee-terraform_apply-<pid>.errlog
# ✅ No stdbuf needed!
# ✅ No manual filename management
```

### 3. Timeout Detection ⏱️

```bash
# Terraform can hang on AWS API calls
ee -t 300 --idle-timeout 60 'Error' terraform apply

# ✅ Real-time output (unbuffered by default!)
# ✅ Max 300s total
# ✅ Kills if no output for 60s
# ✅ First output timeout available
```

### 4. Compression 🗜️

```bash
# Terraform logs can be HUGE
ee -z 'Error' terraform apply
# ✅ Real-time output (unbuffered by default!)
# ✅ Auto-compresses to .log.gz
# ✅ 70-90% space savings
# ✅ Read with: zcat /tmp/ee-terraform_apply-*.log.gz
```

### 5. Pattern-Based Exit 🔍

```bash
# Stop immediately on specific errors
ee 'AccessDenied|InvalidPermissions|LimitExceeded' terraform apply

# ✅ Real-time output (unbuffered by default!)
# ✅ Catches permission errors immediately
# ✅ Catches AWS limit errors immediately
# ✅ Saves time and money
```

---

## Real-World Terraform Example

### The Mist Project Use Case

```bash
# Old way (manual pipeline)
cd /Users/robert.lee/github/mist && \
  terraform apply \
  -var="cloud=aws" \
  -var="region=us-west-2" \
  2>&1 | tee /tmp/mist_terraform_apply_$(date +%s).log | \
  grep -E 'Error|Warning'

# Problems:
# ⚠️ Runs to completion even after errors
# ⚠️ Manual log file naming
# ⚠️ No timeout protection
# ⚠️ No compression
# ⚠️ Complex pipeline syntax
```

### With earlyexit:

```bash
# New way (simple + powerful + real-time BY DEFAULT!)
cd /Users/robert.lee/github/mist && \
  ee -z -t 600 --idle-timeout 120 'Error|AccessDenied' \
  terraform apply -var="cloud=aws" -var="region=us-west-2"

# Benefits:
# ✅ Real-time output (unbuffered by default!)
# ✅ Stops on first Error or AccessDenied (saves time & money)
# ✅ Auto-logging: /tmp/ee-terraform_apply-<pid>.log.gz
# ✅ 600s max timeout, 120s idle timeout
# ✅ 70-90% smaller logs (gzip)
# ✅ Simple, readable syntax
# ✅ Separate stdout/stderr logs
# ✅ No stdbuf needed!
```

---

## Summary

### For Terraform Users:

1. ⚠️ **Buffering IS an issue when piped** (ALL programs buffer when piped, including Go!)
2. 🎯 **Just use `ee`** - unbuffering is now THE DEFAULT!
3. 💡 **Use `ee` for:**
   - Real-time output (unbuffered by default!)
   - Early exit on errors (save time & money)
   - Auto-logging (intelligent filenames)
   - Timeout protection (idle, first-output, total)
   - Compression (save disk space)
   - Pattern matching (catch specific errors)

### The Key Insight:

**Piping changes buffering behavior for ALL programs:**
- `terraform apply` (to terminal) → Line-buffered ✅
- `terraform apply | tee log` → Block-buffered ⚠️ (needs `stdbuf -o0`)
- `ee 'pattern' terraform apply` → **Unbuffered by DEFAULT** ✅ (real-time!)
- `ee --buffered 'pattern' terraform apply` → Block-buffered ⚠️ (opt-out, rare)

### Quick Reference:

```bash
# Standard Terraform (unbuffered by default!)
ee 'Error' terraform apply                          # ✅ Real-time (default!)
ee -z 'Error' terraform plan                        # ✅ With compression
ee -t 300 'Error' terraform destroy                 # ✅ With timeout

# Python scripts (also unbuffered by default!)
ee 'Error' python3 terraform_wrapper.py             # ✅ Real-time (default!)

# Other Go tools (also unbuffered by default!)
ee 'error' kubectl apply -f deployment.yaml         # ✅ Real-time (default!)
ee 'ERRO' docker build -t myapp:latest .            # ✅ Real-time (default!)

# Opt-out only when needed (rare)
ee --buffered 'ERROR' cat gigantic.log              # For high-throughput
```

---

## Test It Yourself

```bash
# Create a slow Terraform-like Go program
cat > /tmp/test.go << 'EOF'
package main
import ("fmt"; "time")
func main() {
    for i := 0; i < 5; i++ {
        fmt.Printf("Line %d\n", i)
        time.Sleep(1 * time.Second)
    }
}
EOF

# Test 1: To terminal (line-buffered, real-time)
go run /tmp/test.go
# ✅ Output appears line-by-line in real-time!

# Test 2: Piped to tee (block-buffered, delayed!)
go run /tmp/test.go | tee /tmp/out.log
# ⚠️ All output appears at once after 5s!

# Test 3: With stdbuf (unbuffered, real-time!)
stdbuf -o0 go run /tmp/test.go | tee /tmp/out.log
# ✅ Output appears line-by-line in real-time!

# Test 4: With earlyexit (unbuffered BY DEFAULT, real-time!)
ee 'xxx' go run /tmp/test.go
# ✅ Output appears line-by-line in real-time!
# (Note: unbuffering is now the default, no -u needed!)
```

---

**Bottom line:** Even Go programs (like Terraform) buffer when piped! `earlyexit` unbuffers BY DEFAULT, so you get real-time output without any flags. No need to remember `stdbuf -o0` or `-u`! 🚀

