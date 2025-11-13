---
name: Data Submission
about: Share your earlyexit usage data to help validate the early exit hypothesis
title: '[DATA] My earlyexit results for [tool/project type]'
labels: ['data-submission', 'community']
assignees: ''
---

## Thank You for Contributing! 🙏

Your data helps validate whether ML early exit principles actually apply to command-line tools. This is community-driven research!

---

## 1. Export Your Data

Run this command to export your anonymized data:

```bash
earlyexit-export --mask-sensitive > my-earlyexit-data.json
```

**Privacy Note:** This export automatically masks all sensitive data (patterns, commands, paths). Only metrics and project types are included.

---

## 2. Context About Your Usage

**What tools did you test earlyexit with?**
<!-- e.g., npm test, pytest, cargo build, terraform apply, etc. -->

**What project type(s)?**
<!-- e.g., Node.js, Python, Rust, Infrastructure/IaC -->

**How many runs/days of data?**
<!-- e.g., "~50 runs over 2 weeks", "3 days of CI/CD builds" -->

**What was your use case?**
<!-- e.g., "Testing during development", "CI/CD pipeline", "Database provisioning" -->

---

## 3. Your Observations

**Did earlyexit work as expected?**
<!-- Yes/No and explain -->

**Estimated time saved:**
<!-- e.g., "~5 minutes per failed build", "10 hours over 2 weeks" -->

**False positives encountered?**
<!-- Did it exit early when it shouldn't have? How often? -->

**False negatives encountered?**
<!-- Did it miss errors it should have caught? -->

**Would you recommend it to others?**
<!-- Yes/No and why -->

---

## 4. The Data (JSON Export)

Paste your exported JSON below or attach as a file:

```json
{
  "version": "1.0",
  "export_timestamp": 1234567890,
  "total_settings": 1,
  "masked_sensitive": true,
  "settings": [
    // Paste your export here
  ]
}
```

**Or attach the file:**
Drag and drop `my-earlyexit-data.json` here

---

## 5. Technical Details (Optional)

**Operating System:**
<!-- e.g., Ubuntu 22.04, macOS 14, Windows 11 -->

**Python Version:**
<!-- e.g., 3.11.5 -->

**earlyexit Version:**
<!-- Run: pip show earlyexit -->

**Any performance issues?**
<!-- e.g., high CPU usage, slow pattern matching, database locks -->

---

## 6. Permission to Use Data

- [ ] I confirm this data is anonymized and safe to share publicly
- [ ] You may include this data in aggregated statistics and research papers
- [ ] You may share this data with other researchers (still anonymized)

---

## What Happens Next?

1. I'll analyze your data along with others' submissions
2. Weekly summaries of aggregated results will be posted
3. Your contribution will be credited (if you want) in any research publications
4. I'll respond with findings specific to your use case

**Thank you for helping validate this hypothesis!** 🚀

