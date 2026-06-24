# ISRO SOC Platform — Operational Runbook

This runbook dictates the immediate operational steps required to restore the ISRO SOC AI Platform during a critical outage. It acts as the primary reference for the Platform Engineering and Infrastructure teams.

---

## Severity Definitions
- **SEV1**: Platform completely down, no alert visibility. Core Elasticsearch node crashed or backend API routing failed.
- **SEV2**: Degraded. Core alerting functions, but some AI functionality unavailable (e.g., SLM down, RAG timeout).
- **SEV3**: Minor issue. UI glitch, delayed stats update, or a workaround is available.

---

## Runbook: Elasticsearch Down

**Symptoms:** 
- `GET /health/ready` returns `503 Service Unavailable`.
- The React dashboard shows a "Failed to fetch" red banner, and stats show `0`.

**Diagnosis:**
1. Check if the ES container is active:
   ```bash
   docker compose ps elasticsearch
   ```
2. Check local HTTP availability bypassing the API:
   ```bash
   curl -u elastic:$ES_PASSWORD http://localhost:9200
   ```
3. Read the exact crash reason from the container logs:
   ```bash
   docker compose logs elasticsearch --tail 100
   ```

**Resolution:**
1. **Crashed Container**: Often due to a host memory spike.
   ```bash
   docker compose restart elasticsearch
   ```
2. **Disk Full Exception (Watermark Block)**: Elasticsearch locks indices into "Read-Only" mode if disk space exceeds 85%.
   - Check space: `df -h`
   - Run the hard cleanup script: `make clean`
3. **Data Corruption**: If the shards are irreparably corrupted, trigger the backup restoration (see *Disaster Recovery* below).

**Escalation:** 
If not resolved in **15 minutes**, escalate to the Tier 3 Infrastructure Team.

---

## Runbook: SLM Not Responding

**Symptoms:** 
- The Investigation Chat UI shows "Model not loaded".
- `GET /api/slm/status` returns `{"loaded": false}`.

**Diagnosis:**
1. Check the server RAM usage via the metrics endpoint:
   ```bash
   curl http://localhost:8000/health/metrics
   ```
   *Look for `memory_percent > 90%`.*
2. Check the FastAPI backend logs for PyTorch `CUDA OutOfMemoryError` or OS `SIGKILL` flags.

**Resolution:**
1. **OOM Mitigation**: Restart the backend. If it crashes again, edit `.env.development` and set `SLM_LOAD_IN_4BIT=true` to drastically reduce VRAM usage, then restart.
2. **Corrupt Weights**: If the model files on disk are corrupted, force a reload of the base HuggingFace weights:
   ```bash
   curl -X POST http://localhost:8000/api/slm/reload-model \
     -H "Content-Type: application/json" \
     -d '{"model": "base"}'
   ```
3. **Fallback**: If the hardware cannot support the model, disable it. Threat scores and deterministic rule-based explanations will continue to function normally.

---

## Runbook: Ingestion Pipeline Stalled

**Symptoms:** 
- A platform self-monitoring alert (`PA-001`) has fired.
- `GET /api/ingestion/status` shows an aggressively outdated `last_run` timestamp.

**Diagnosis:**
1. Check the FastAPI backend logs for APScheduler crashes.
   ```bash
   docker compose logs backend | grep APScheduler
   ```
2. Verify that Elasticsearch is still responding to the backend.

**Resolution:**
1. Restart the backend container to reboot the scheduler daemon.
2. Force a manual ingestion catch-up spanning the missed hours:
   ```bash
   curl -X POST http://localhost:8000/api/ingestion/run \
     -H "Content-Type: application/json" \
     -d '{"force_full": true}'
   ```
3. **Verify Upstream**: Check if Logstash/Filebeat actually stopped sending logs to `logs-system-*` in the first place.

---

## Runbook: Disk Space Critical

**Symptoms:** 
- Platform alert `PA-006` fires.
- Server disk capacity exceeds `85%`.

**Resolution:**
1. Execute the comprehensive cleanup script forcefully:
   ```bash
   cd backend && python scripts/cleanup.py --execute
   ```
2. Identify the bloated index using the ES Cat API:
   ```bash
   curl -u elastic:$ES_PASSWORD http://localhost:9200/_cat/indices?v&s=store.size:desc
   ```
3. If `soc-score-history` is massive, consider reducing its retention mapping from the default 30 days down to 7 days.
4. Purge orphaned Docker volumes and dangling images:
   ```bash
   docker system prune -a --volumes
   ```

---

## Runbook: Suspected Security Incident on the Platform Itself

*(Meta-incident: An attacker is actively targeting the SOC platform)*

**Symptoms:** 
- Unrecognized admin sessions or suspicious modifications to ML model thresholds.

**Immediate Actions:**
1. Check the internal audit log for anomalous configuration changes:
   ```bash
   curl http://localhost:8000/api/admin/audit-log
   ```
2. Search the proxy logs (Nginx) for massive bursts of `401 Unauthorized` requests targeting `/api/auth/login` (brute-force attack).
3. **Critical Rotation**: If a compromise is suspected, immediately rotate the `JWT_SECRET_KEY` in the `.env` file and restart the backend. This instantly invalidates all active analyst sessions globally.
4. Implement strict IP blocking at the perimeter firewall for the offending attacker IPs identified in the rate-limit logs.

---

## Disaster Recovery — Full Platform Restore

**Scenario:** Complete, irrecoverable server loss (e.g., hardware fire, catastrophic host ransomware). Rebuilding from cold backups.

1. **Provision Infrastructure**: Spin up the new Linux host and install Docker.
2. **Clone Source Code**:
   ```bash
   git clone <repo-url> Project-SOC && cd Project-SOC
   ```
3. **Restore Secrets**: Pull the `.env.development` and `.env.production` files from your secure internal Password Vault (e.g., HashiCorp Vault). *These are NEVER stored in Git.*
4. **Boot Database**:
   ```bash
   docker compose up -d elasticsearch
   ```
5. **Restore ES Snapshot**: Utilize the Kibana Snapshot Restore API or the built-in admin route to pull the latest nightly backup from the S3/NFS mount:
   ```bash
   curl -X POST http://localhost:8000/api/admin/backups/latest/restore
   ```
6. **Restore ML Models**: Copy the `.pkl` and `.pt` weights from your network backup drive into `backend/models/saved/`.
7. **Boot Stack**:
   ```bash
   docker compose up -d
   ```
8. **Verify Integrity**: Run the internal smoke tests against the restored cluster:
   ```bash
   make smoke-test
   ```
9. **Visual Check**: Log into the React dashboard and ensure historical alerts and baselines populate correctly.

---

## Contact Escalation Chain

*(Please fill this with internal ISRO contact details)*

1. **L1 (SOC Analyst)**: Identifies the platform outage and attempts basic UI refreshes.
2. **L2 (Platform Admin)**: Executes this Runbook (restarting containers, running cleanup scripts).
   - **Name**: [Placeholder]
   - **Phone**: [Placeholder]
3. **L3 (Infrastructure Team)**: Handles hardware failures, disk expansions, and bare-metal DR restores.
   - **Name**: [Placeholder]
   - **Phone**: [Placeholder]

---

## Maintenance Windows

**Recommended Window**: Sundays 02:00 - 04:00 IST.

*Why?* This coincides exactly with the automated `weekly_cleanup_job` and the Unsupervised ML Retraining pipeline (`APScheduler`). If the platform needs to be brought down for patching, performing it during this window ensures no mid-week baseline metrics are severed.
