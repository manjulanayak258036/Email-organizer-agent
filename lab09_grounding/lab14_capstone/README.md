# Lab 14: Capstone Integration

This lab wires the validated outputs from the earlier labs into a single deployed worklet:

- connector layer for source access
- runtime + audit + checkpoints
- node graph orchestration
- governance approval + rollback rules
- specialist output generation
- dashboard-ready summary for the faculty mailbox owner

The capstone intentionally integrates existing contracts instead of rewriting them. The deployment shell is intentionally thin and uses the same modules the earlier labs already proved.

## Run

```bash
python lab14_capstone/demo_lab14.py
streamlit run lab14_capstone/app.py
```

## Acceptance

The capstone is accepted when the mailbox owner can run one session, review the generated triaged inbox and drafts, and publish only approved work under the same guardrail as the live dashboard.
