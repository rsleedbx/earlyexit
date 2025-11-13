# earlyexit Tutorial: From Testing to Community Sharing

**A complete hands-on guide using the Mist database provisioning project**

---

## Introduction

This tutorial walks through the entire earlyexit workflow:

1. ✅ Testing earlyexit on a real project (Mist)
2. ✅ Getting intelligent profile suggestions
3. ✅ Creating and testing a local profile
4. ✅ Sharing the profile with the community
5. ✅ Using shared profiles from others

**Time investment:** 30 minutes  
**Value delivered:** Hours saved on every failed provision, plus helping the community

---

## Part 1: The Problem - Infrastructure Provisioning Takes Forever

### Scenario: Mist Database Provisioning

[Mist](https://github.com/mist-cloud/mist) provisions cloud databases (AWS RDS, GCP Cloud SQL, Azure Database). A typical provision takes **15-30 minutes**.

**The pain:** When something goes wrong (wrong credentials, invalid VPC config, etc.), you often don't find out until 20+ minutes in.

```bash
$ mist create --cloud aws --db postgres --size medium
Validating configuration...
Creating VPC...
Configuring security groups...
Provisioning RDS instance...
⏳ ... 18 minutes later ...
❌ Error: Invalid VPC configuration
   Security group sg-xyz123 not found in VPC vpc-abc789

# You just wasted 18 minutes
```

**What you want:** Catch the error immediately and move on.

---

## Part 2: First Run - Let earlyexit Learn

### Step 1: Install earlyexit

```bash
pip install earlyexit
```

### Step 2: Try the Generic Profile First

```bash
# See what's available
$ earlyexit --list-profiles

# Try the terraform profile (closest to infrastructure)
$ earlyexit --profile terraform mist create --cloud aws --db postgres

📋 Using profile: terraform
   F1 Score: 84.00% | RECOMMENDED
   
Validating configuration...
Creating VPC...
❌ Error: Invalid VPC configuration
   
Captured error at 2.3 minutes (instead of 18+ minutes!)
Exit code: 0
```

**Result:** Saved 15+ minutes on first try! 🎉

### Step 3: Use Watch Mode to Learn Your Patterns

But we can do better. Let's teach earlyexit the specific patterns for Mist:

```bash
$ earlyexit mist create --cloud aws --db postgres

🔍 Watch mode enabled (no pattern specified)
   • All output is being captured and analyzed
   • Press Ctrl+C when you see an error to teach earlyexit

Validating configuration...
Creating VPC...
Configuring security groups...
❌ Error: Invalid security group
   SecurityGroupNotFound: sg-xyz123 not found in VPC vpc-abc789

[Press Ctrl+C]

⚠️  Interrupted at 142.5s
   • Captured 47 stdout lines
   • Captured 12 stderr lines

🎓 LEARNING MODE
Why did you stop?
  1. Error detected
  2. Taking too long (timeout)
  3. Process hung (no output)
  4. Other

Your choice [1-4]: 1

Analyzing captured output...

I found these potential error patterns:

  1. 📛 'Error:' (3 occurrences, stderr, high confidence)
     First seen at: line 45
     Context: "❌ Error: Invalid security group"
     
  2. 📛 'SecurityGroupNotFound' (1 occurrence, stderr, medium confidence)
     First seen at: line 46
     Context: "SecurityGroupNotFound: sg-xyz123 not found"
     
  3. 📛 'failed' (2 occurrences, stdout, medium confidence)
     First seen at: line 23
     Context: "Validation failed for resource"

Which patterns should I watch for? [Enter numbers separated by spaces, or 'all']: 1 2

✅ Will watch for: 'Error:|SecurityGroupNotFound'

Analyzing timing...
• Command ran for: 142.5 seconds
• First output appeared at: 0.8s
• Idle periods detected: No significant gaps

Suggested timeouts:
  --timeout 1800          (30 min overall - provisions can be slow)
  --idle-timeout 120      (2 min idle - catch hangs during AWS API calls)
  --delay-exit 15         (15s after error - captures full AWS error messages)

Save this configuration? [Y/n]: Y

✅ Learning saved to ~/.earlyexit/telemetry.db
   Next time you run 'mist create', I'll suggest these settings!
```

---

## Part 3: Second Run - Smart Suggestions

### The Next Day: Run Mist Again

```bash
$ earlyexit mist create --cloud aws --db postgres

💡 SMART SUGGESTION (Based on 1 previous run)
   Pattern: 'Error:|SecurityGroupNotFound'
   Timeout: 1800s (30 min)
   Idle timeout: 120s
   Delay exit: 15s
   
   📊 Limited data warning:
     • Only 1 run recorded
     • Cannot calculate validation metrics yet
     • Run 5+ times for statistical confidence
   
   🎯 Recommendation: TRY_IT
   
Use this? [Y/n/e(dit)]: Y

✅ Using learned settings

📋 Running: earlyexit --timeout 1800 --idle-timeout 120 --delay-exit 15 'Error:|SecurityGroupNotFound' mist create --cloud aws --db postgres

Validating configuration...
Creating VPC...
❌ Error: AWS credentials expired
   Please refresh your credentials with 'aws sso login'

Captured error at 45.2 seconds
Exit code: 0
```

**Time saved:** Another 20+ minutes! 🎉

---

## Part 4: Build Validation Data

### Run Multiple Times to Get Statistics

Over the next week, run Mist with earlyexit 10+ times:

```bash
# Run 1: Config error (caught ✅)
$ earlyexit mist create --cloud aws --db postgres
# ❌ Caught at 0:45

# Run 2: Success (no false alarm ✅)
$ earlyexit mist create --cloud aws --db postgres
# ✅ Completed normally at 18:23

# Run 3: VPC error (caught ✅)
$ earlyexit mist create --cloud aws --db postgres
# ❌ Caught at 2:15

# Run 4: Success (no false alarm ✅)
$ earlyexit mist create --cloud aws --db postgres
# ✅ Completed normally at 22:47

# ... 6 more runs ...
```

**After 10 runs:**

```bash
$ earlyexit mist create --cloud aws --db postgres

💡 SMART SUGGESTION (Based on 10 previous runs)
   Pattern: 'Error:|SecurityGroupNotFound|InvalidParameterValue'
   Timeout: 1800s
   Idle timeout: 120s
   Delay exit: 15s
   
   📊 Validation (10 runs):
     ✅ 4 errors caught (40%)
     ✅ 5 successful runs (50%)
     ⚠️  1 false alarm (10%)
     ❌ 0 missed errors (0%)
   
   📈 Performance:
     Precision: 80% (4 true positives / 5 total alarms)
     Recall: 100% (4 caught / 4 total errors)
     F1 Score: 0.89
   
   ⚠️  Note: 1 false positive when AWS returned warning message with "Error" in it
   
   🎯 Recommendation: RECOMMENDED
   
Use this? [Y/n]: Y
```

**Now we have real validation data!** This is solid enough to share with others.

---

## Part 5: Create a Shareable Profile

### Export Your Configuration

```bash
$ earlyexit-export --mask-sensitive > mist-aws-profile-data.json

$ cat mist-aws-profile-data.json
{
  "version": "1.0",
  "export_timestamp": 1699824567,
  "total_settings": 1,
  "masked_sensitive": true,
  "settings": [{
    "command_hash": "a7f3e8b2...",
    "project_type": "terraform",
    "learned_parameters": {
      "pattern": "<masked>",
      "timeout": 1800,
      "idle_timeout": 120,
      "delay_exit": 15
    },
    "validation": {
      "counts": {
        "true_positives": 4,
        "true_negatives": 5,
        "false_positives": 1,
        "false_negatives": 0,
        "total_runs": 10
      },
      "metrics": {
        "precision": 0.80,
        "recall": 1.00,
        "f1_score": 0.89,
        "accuracy": 0.90
      }
    },
    "recommendation": "RECOMMENDED"
  }]
}
```

### Create a Clean Profile for Sharing

Now create a proper profile with your learned settings:

```bash
$ cat > mist-aws-provision.json << 'EOF'
{
  "name": "mist-aws",
  "description": "Mist database provisioning on AWS (RDS, Aurora)",
  "pattern": "Error:|Failed to|Invalid|SecurityGroupNotFound|InvalidParameterValue",
  "options": {
    "timeout": 1800,
    "idle_timeout": 120,
    "delay_exit": 15,
    "delay_exit_after_lines": 150
  },
  "validation": {
    "precision": 0.80,
    "recall": 1.00,
    "f1_score": 0.89,
    "accuracy": 0.90,
    "tested_runs": 10,
    "true_positives": 4,
    "true_negatives": 5,
    "false_positives": 1,
    "false_negatives": 0
  },
  "recommendation": "RECOMMENDED",
  "notes": [
    "Tested with Mist v2.1.0 on AWS RDS and Aurora",
    "Catches configuration errors early (VPC, security groups, credentials)",
    "15s delay captures full AWS error messages including request IDs",
    "False positive occurred with AWS warning message containing 'Error' keyword",
    "Works best with mist create, mist update, mist delete commands",
    "May need adjustment for GCP or Azure providers"
  ],
  "use_cases": [
    "mist create --cloud aws --db postgres",
    "mist create --cloud aws --db mysql --size large",
    "mist update --db-id xyz --storage 500"
  ],
  "contributor": "robert.lee",
  "project": "https://github.com/mist-cloud/mist",
  "created": "2024-11-12",
  "version": "1.0"
}
EOF
```

---

## Part 6: Test Your Profile Locally

### Install and Test

```bash
# Install your profile
$ earlyexit-profile install ./mist-aws-provision.json
📥 Installing profile from ./mist-aws-provision.json...
✅ Profile 'mist-aws' installed successfully!

Usage:
  earlyexit --profile mist-aws your-command

# Test it works
$ earlyexit --profile mist-aws mist create --cloud aws --db postgres

📋 Using profile: mist-aws
   F1 Score: 89.00% | RECOMMENDED

Validating configuration...
❌ Error: AWS credentials not found

Captured error at 12.4 seconds
Exit code: 0

# ✅ Works perfectly!
```

### Show Profile Details

```bash
$ earlyexit-profile show mist-aws

📋 Profile: mist-aws (user-installed)

Description: Mist database provisioning on AWS (RDS, Aurora)
Pattern: Error:|Failed to|Invalid|SecurityGroupNotFound|InvalidParameterValue

Options:
  --timeout: 1800
  --idle-timeout: 120
  --delay-exit: 15
  --delay-exit-after-lines: 150

Validation:
  Precision: 80.00%
  Recall: 100.00%
  F1 Score: 89.00%
  Tested on: 10 runs

Recommendation: RECOMMENDED

Notes:
  • Tested with Mist v2.1.0 on AWS RDS and Aurora
  • Catches configuration errors early (VPC, security groups, credentials)
  • 15s delay captures full AWS error messages including request IDs
  • False positive occurred with AWS warning message containing 'Error' keyword
  • Works best with mist create, mist update, mist delete commands
  • May need adjustment for GCP or Azure providers

Usage:
  earlyexit --profile mist-aws your-command
```

---

## Part 7: Share with the Community

You have two options: **GitHub Issue** (easier) or **Pull Request** (more permanent).

### Option A: Share via GitHub Issue (Recommended for First-Time Contributors)

```bash
# 1. Go to the data submission template
# Open: https://github.com/rsleedbx/earlyexit/issues/new?template=data-submission.md

# 2. Fill out the form:

Title: [DATA] Mist AWS provisioning profile

**Tools tested:** Mist v2.1.0 (database provisioning)
**Project type:** Infrastructure / Cloud (similar to Terraform)
**Runs:** 10 runs over 1 week
**Use case:** AWS RDS/Aurora database provisioning

**Observations:**
- ✅ Caught 4/4 errors (100% recall)
- ✅ 5 successful provisions with no false alarms
- ⚠️  1 false positive from AWS warning message
- ⏱️  Average time saved: 15-20 minutes per failed provision
- 💰 Cost saved: Prevented expensive AWS resources from full provisioning

**Would recommend:** YES - Highly effective for infrastructure provisioning

**Profile JSON:**
[Attach mist-aws-provision.json]

**Validation data:**
[Attach mist-aws-profile-data.json]

# 3. Submit!
```

**Result:** Community can now discuss, test, and use your profile.

### Option B: Share via Pull Request (For Curated Profiles)

```bash
# 1. Fork and clone the repo
$ git clone https://github.com/YOUR-USERNAME/earlyexit
$ cd earlyexit

# 2. Add your profile to the community patterns
$ mkdir -p community-patterns/infrastructure
$ cp ~/mist-aws-provision.json community-patterns/infrastructure/

# 3. Create a commit
$ git add community-patterns/infrastructure/mist-aws-provision.json
$ git commit -m "Add Mist AWS provisioning profile

- Tested with Mist v2.1.0 on AWS RDS/Aurora
- F1 score: 0.89 (10 runs)
- Precision: 80%, Recall: 100%
- Catches config errors early (avg 15-20 min saved)"

# 4. Push and create PR
$ git push origin main
# Then go to GitHub and create Pull Request

# 5. In the PR description:
```

**PR Template:**

```markdown
## Profile Contribution: Mist AWS Provisioning

**Profile:** `mist-aws`  
**Tool:** [Mist](https://github.com/mist-cloud/mist) v2.1.0  
**Category:** Infrastructure / Database Provisioning

### Validation Data

- **Runs tested:** 10
- **Time period:** 1 week  
- **F1 Score:** 0.89
- **Precision:** 80% (4 TP / 5 alarms)
- **Recall:** 100% (4 caught / 4 errors)
- **Recommendation:** RECOMMENDED

### What It Catches

- AWS credential errors
- VPC configuration issues
- Security group problems
- Invalid parameter values
- Resource not found errors

### Time Savings

- **Average provision time:** 18-25 minutes
- **Average error detection:** 1-3 minutes
- **Time saved per error:** 15-22 minutes
- **Total time saved (10 runs):** ~60-80 minutes

### Notes

- One false positive from AWS warning message
- Works best with `mist create`, `mist update`, `mist delete`
- May need tuning for GCP/Azure providers

### Testing

```bash
earlyexit-profile install https://raw.githubusercontent.com/YOUR-USERNAME/earlyexit/main/community-patterns/infrastructure/mist-aws-provision.json
earlyexit --profile mist-aws mist create --cloud aws --db postgres
```
```

---

## Part 8: Others Use Your Profile

### Community Member Downloads Your Profile

```bash
# From your PR (if merged)
$ earlyexit-profile install https://raw.githubusercontent.com/rsleedbx/earlyexit/master/community-patterns/infrastructure/mist-aws-provision.json

📥 Downloading profile from https://raw.githubusercontent...
✅ Profile 'mist-aws' installed successfully!

# Or from your fork (while PR is pending)
$ earlyexit-profile install https://raw.githubusercontent.com/YOUR-USERNAME/earlyexit/main/community-patterns/infrastructure/mist-aws-provision.json

# Or from the GitHub issue (download attachment)
$ earlyexit-profile install ~/Downloads/mist-aws-provision.json
```

### They Test It

```bash
$ earlyexit --profile mist-aws mist create --cloud aws --db postgres

📋 Using profile: mist-aws
   F1 Score: 89.00% | RECOMMENDED
   
Validating configuration...
Creating VPC...
❌ Error: Invalid VPC configuration

Captured error at 2.1 minutes
Exit code: 0

# ✅ Worked for them too!
```

### They Contribute Back

```bash
# After 15 more runs, they have more data
$ earlyexit-export --mask-sensitive > mist-aws-extended-data.json

# Comment on the original issue:
"Tested this profile with 15 additional runs:
- F1 score: 0.91 (improved from 0.89)
- No false positives in my tests
- Also works great with GCP Cloud SQL
- Suggestion: Add 'permission denied' to pattern

Validation data attached."
```

---

## Part 9: Profile Evolution

### Version 2: Based on Community Feedback

```json
{
  "name": "mist-aws-v2",
  "description": "Mist database provisioning on AWS (v2 - community improved)",
  "pattern": "Error:|Failed to|Invalid|SecurityGroupNotFound|InvalidParameterValue|PermissionDenied|AccessDenied",
  "options": {
    "timeout": 1800,
    "idle_timeout": 120,
    "delay_exit": 15,
    "delay_exit_after_lines": 150
  },
  "validation": {
    "precision": 0.88,
    "recall": 1.00,
    "f1_score": 0.94,
    "tested_runs": 45,
    "contributors": ["robert.lee", "user2", "user3"]
  },
  "recommendation": "HIGHLY_RECOMMENDED",
  "changes_from_v1": [
    "Added PermissionDenied and AccessDenied patterns",
    "Reduced false positive rate from 10% to 6%",
    "Tested by 3 contributors across 45 total runs",
    "Improved F1 from 0.89 to 0.94"
  ]
}
```

---

## Part 10: The Complete Workflow Diagram

```
Week 1: Discovery
├── Try generic profile → Works OK
├── Use watch mode → Learn specific patterns
├── Run 10+ times → Build validation data
└── Create profile → mist-aws-provision.json

Week 2: Sharing
├── Test locally → Confirm it works
├── Submit to GitHub → Issue or PR
├── Community tests → More validation
└── Iterate → Version 2 with improvements

Week 3: Benefits
├── Others use your profile → Saves them time
├── They contribute data → Improves accuracy
├── Profile gets better → Everyone benefits
└── You're credited → Recognition in community
```

---

## Metrics: What We Achieved

### Before earlyexit
- **Failed provision time:** 15-25 minutes each
- **Iterations to fix:** 3-5 attempts
- **Total time wasted:** 45-125 minutes per issue
- **Frustration level:** HIGH 😤

### After earlyexit
- **Failed provision time:** 1-3 minutes (90% reduction)
- **Iterations to fix:** Still 3-5, but FAST
- **Total time wasted:** 3-15 minutes per issue (80-90% savings)
- **Frustration level:** LOW 😊

### For the Community
- **Your 10 runs → Data for others**
- **15 more contributors → 45 more runs**
- **Better profile → F1 improves from 0.89 to 0.94**
- **Everyone saves time → Compound benefits**

---

## Real Numbers from Mist Project

```bash
# Before earlyexit (2 weeks of development)
Failed provisions: 42
Average time per failure: 18 minutes
Total time wasted: 756 minutes (12.6 hours)

# After earlyexit (2 weeks of development)
Failed provisions: 38
Average detection time: 2.5 minutes
Total time wasted: 95 minutes (1.6 hours)

Time saved: 661 minutes (11 hours)
```

**11 hours saved in 2 weeks. Over a project lifetime, this compounds to days or weeks.**

---

## Conclusion: The Virtuous Cycle

```
Try → Value → Share → Improve → Everyone Wins
```

1. **You try** earlyexit on your project (30 min investment)
2. **You get value** immediately (hours saved)
3. **You share** your profile (10 min)
4. **Others benefit** from your experience
5. **They contribute back** with more data
6. **Profile improves** for everyone
7. **Community grows** stronger

**This is how we validate the early exit hypothesis: together.**

---

## Next Steps

### Start Your Own Journey

```bash
# 1. Install
pip install earlyexit

# 2. Try a profile
earlyexit --profile terraform your-infra-command

# 3. Use watch mode to learn
earlyexit your-command

# 4. Build validation data (10+ runs)
# ... use it regularly ...

# 5. Create and share your profile
earlyexit-export --mask-sensitive > my-data.json
# Create profile JSON
earlyexit-profile install ./my-profile.json
# Share on GitHub

# 6. Help others by using their profiles
earlyexit-profile install https://...
```

### Resources

- **GitHub Issues:** https://github.com/rsleedbx/earlyexit/issues
- **Data Submission Template:** https://github.com/rsleedbx/earlyexit/issues/new?template=data-submission.md
- **Community Patterns:** https://github.com/rsleedbx/earlyexit/tree/master/community-patterns
- **Profile Format Reference:** [docs/PROFILE_FORMAT_REFERENCE.md](./PROFILE_FORMAT_REFERENCE.md)

---

**Ready to start? Try earlyexit on YOUR project and share what you learn!** 🚀

*Questions? Open an issue or discussion on GitHub.*

