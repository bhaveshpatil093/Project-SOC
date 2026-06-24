# Production Go-Live Checklist

## T-7 Days
- [ ] Staging validation report: APPROVED (`python backend/scripts/staging_validation.py`)
- [ ] Security hardening checklist: 100% complete
- [ ] Load test results reviewed and accepted
- [ ] Disaster recovery runbook tested end-to-end
- [ ] Analyst training sessions scheduled

## T-3 Days
- [ ] Production environment provisioned
- [ ] SSL certificates installed and verified
- [ ] Production `.env` configured (all secrets rotated from staging)
- [ ] DNS configured for production domain (`soc.istrac.isro.gov.in`)
- [ ] Backup schedule confirmed active

## T-1 Day
- [ ] Final smoke test against production environment
- [ ] Rollback plan documented and understood by team
- [ ] On-call rotation confirmed for go-live window

## Go-Live Day
- [ ] Deploy during approved maintenance window
- [ ] Run `smoke_test.py` immediately post-deploy
- [ ] Monitor dashboards for first 2 hours actively
- [ ] Verify first real ingestion cycle completes successfully
- [ ] Verify first real alert generates correctly

## T+1 Day
- [ ] Review overnight logs for any errors
- [ ] Confirm scheduled jobs ran correctly (retraining, backups, reports)
- [ ] Gather initial analyst feedback

## T+7 Days
- [ ] Review first week metrics: alert volume, FP rate, SLM usage
- [ ] Conduct retrospective with SOC team
- [ ] Document any issues and resolutions in `RUNBOOK.md`
