# Infrastructure / IaC Profiles

Profiles for infrastructure provisioning and Infrastructure-as-Code tools.

---

## Available Profiles

### mist-aws-provision.json

**Tool:** [Mist](https://github.com/mist-cloud/mist) - Database provisioning  
**Cloud:** AWS (RDS, Aurora, DynamoDB)  
**F1 Score:** 0.89 (10 runs)  
**Recommendation:** RECOMMENDED

**Install:**
```bash
earlyexit-profile install https://raw.githubusercontent.com/rsleedbx/earlyexit/master/community-patterns/infrastructure/mist-aws-provision.json
```

**Use:**
```bash
earlyexit --profile mist-aws mist create --cloud aws --db postgres
```

**What it catches:**
- AWS credential errors
- VPC configuration issues
- Security group problems
- IAM permission errors
- Invalid parameters
- Resource not found errors

**Time savings:** 15-20 minutes per failed provision

**Tutorial:** See [TECHNICAL_TUTORIAL_MIST.md](../../docs/TECHNICAL_TUTORIAL_MIST.md) for complete workflow

---

## Contributing Infrastructure Profiles

We need profiles for:

- ☐ **Terraform** (apply, plan, destroy)
- ☐ **Pulumi** (up, preview, destroy)
- ☐ **CloudFormation** (create-stack, update-stack)
- ☐ **Ansible** (playbook runs)
- ☐ **Chef** (cookbook runs)
- ☐ **Kubernetes** (kubectl apply, helm install)
- ☐ **AWS CDK** (deploy, synth)
- ☐ **Azure Resource Manager** (deployment operations)
- ☐ **GCP Deployment Manager**
- ☐ **Mist** (GCP, Azure providers)

### Contribution Guidelines

1. Test on at least 10 runs
2. Calculate validation metrics (TP/TN/FP/FN)
3. Document time savings
4. Note any false positives
5. Include example commands

See [TECHNICAL_TUTORIAL_MIST.md](../../docs/TECHNICAL_TUTORIAL_MIST.md) for step-by-step guide.

---

## Profile Characteristics

Infrastructure provisioning has unique needs:

### Long Runtimes
- Typical: 10-30 minutes
- Timeouts: 1800-3600 seconds

### Slow APIs
- Idle timeouts: 120-300 seconds
- First output: 30-60 seconds

### Rich Error Messages
- Delay exit: 15-30 seconds
- Capture lines: 150-300

### Common Patterns
```
Error:|Failed to|Invalid|PermissionDenied|ResourceNotFound
```

---

## Real-World Impact

**Mist project example:**
- 40 failed provisions over 2 weeks
- Average provision time: 18 minutes
- Average error detection: 2.5 minutes
- **Time saved: 11 hours (660 minutes)**

Your infrastructure tool could benefit similarly!

---

## Questions?

Open an issue or discussion on GitHub.

