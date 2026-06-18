Here's the feature engineering map — what you extract from each source and what ML patterns it feeds: Now here's the precise implementation plan broken down by your exact fields:

---

## Step 1 — Parsing & the `log_type` derived column

Your first code task. Map `data_stream.dataset` to a human-readable `log_type`:

```python
LOG_TYPE_MAP = {
    "system.syslog":                    "network",
    "endpoint.events.process":          "process",
    "windows.powershell_operational":   "security_alert"
}
doc["log_type"] = LOG_TYPE_MAP.get(doc["data_stream.dataset"], "unknown")
```

For syslog, you also need to regex-parse the `message` field immediately at ingestion:

```python
import re

SYSLOG_PATTERNS = {
    "src_ip":   r"SRC=([\d\.]+)",
    "dst_ip":   r"DST=([\d\.]+)",
    "protocol": r"PROTO=(\w+)",
    "src_port": r"SPT=(\d+)",
    "dst_port": r"DPT=(\d+)",
    "network_interface": r"IN=(\w*)"
}

def parse_syslog_message(msg: str) -> dict:
    return {k: (m.group(1) if (m := re.search(p, msg)) else None)
            for k, p in SYSLOG_PATTERNS.items()}
```

---

## Step 2 — Feature Engineering, field by field

### From `system.syslog` (network features)
These are all computed over a **5-minute sliding window per `host.ip`**:

| Raw field | Engineered feature | Why it matters |
|---|---|---|
| `src_ip`, `dst_ip` | `unique_dst_ip_count` | High = scanning or lateral movement |
| `dst_port` | `unique_dst_port_count` | High = port scan |
| `dst_port` | `is_rare_port` (flag) | Ports outside 80/443/22/3389 = suspicious |
| `protocol` | `rare_protocol_flag` | Non TCP/UDP in corporate env = anomalous |
| `@timestamp` | `conn_per_minute` | Spike = DoS or C2 beaconing |
| `src_ip` + `dst_ip` | `is_internal_to_external` | Internal src → external dst on odd ports = exfil signal |

### From `endpoint.events.process` (behavioral features)

| Raw field | Engineered feature | Why it matters |
|---|---|---|
| `process.command_line` | `cmd_suspicious_keywords` (TF-IDF or keyword list) | Detects `base64`, `invoke-expression`, `wget`, `curl`, `-enc` |
| `process.parent.name` → `process.name` | `parent_child_pair` (encoded) | `word.exe → powershell.exe` = classic LOLBin chain |
| `process.interactive` | Direct binary feature | `False` + shell spawn = headless execution = suspicious |
| `process.executable` | `is_rare_executable_path` | Path outside `C:\Windows\System32` = anomalous |
| `process.args_count` | Direct + rolling mean deviation | Unusually long arg lists = encoded payloads |
| `process.working_directory` | `is_temp_dir` flag | Execution from `%TEMP%` or `/tmp` = red flag |
| `event.action` | One-hot encoded | `process_started`, `file_created`, etc. |
| `process.exit_code` | Non-zero exit spike | Repeated failures = brute-forcing tools |

### From `windows.powershell_operational` (alert features)

| Raw field | Engineered feature | Why it matters |
|---|---|---|
| `winlog.event_id` | Direct + rolling frequency | Event 4688 (process creation), 4624/4625 (login success/fail) |
| `kibana.alert.risk_score` | Direct numeric feature | Already 0–100, feed straight in |
| `kibana.alert.rule.threat` → `tactic.name` | Label-encoded tactic | Maps to MITRE tactic (TA0001–TA0043) |
| `kibana.alert.rule.threat` → `technique.id` | Label-encoded technique | T1059 (Command Scripting), T1055 (Injection) etc. |
| `kibana.alert.workflow_status` | `open_alert_count` per host | Accumulating unresolved alerts = escalating incident |
| `kibana.alert.severity` | Ordinal encoded: low=1, medium=2, high=3, critical=4 | Weighted in threat score |

---

## Step 3 — Entity key & join strategy

The hardest part of your pipeline is joining these three heterogeneous sources. Use this composite key:

```python
entity_key = (host.id, user.name or "system", window_bucket)
# window_bucket = floor(@timestamp to nearest 5 minutes)
```

In pandas:
```python
df["window_bucket"] = df["@timestamp"].dt.floor("5min")
df["entity_key"] = df["host_id"].astype(str) + "|" + df["user_name"].fillna("system")
```

Group and aggregate each source separately into this 5-min window, then merge on `(entity_key, window_bucket)` with an outer join (a host might have syslog but no process events in that window — that's valid and itself a signal).

---

## Step 4 — Model assignment by log type

| Model | Input features | Detects |
|---|---|---|
| `IsolationForest` | Network feature vector | Port scans, beaconing, exfiltration |
| `Autoencoder` (PyTorch) | Process feature vector | Malicious cmd patterns, LOLBin chains |
| `LSTM` | Sequence of `event.action` per `user.name` over 30-min window | Unusual behavioral sequences (login → priv escalation → data access) |
| `Rule engine` (dict-based) | `technique.id` from alerts | Trigger on known-bad MITRE techniques directly |

The `IsolationForest` and `Autoencoder` are unsupervised — they learn the normal baseline first. The rule engine handles the alert source since `risk_score` and `technique.id` are already semi-structured ground truth.

---

## Step 5 — Key suspicious patterns your fields can detect

From the specific fields you have, these are the highest-value detectable patterns:

**Port scan:** `unique_dst_port_count > 50` in a 5-min window per `src_ip`

**Brute force:** `event_id == 4625` (login failure) count > 10 in 2-min window per `user.name`

**Living off the land (LOLBin):** `process.parent.name == "winword.exe"` AND `process.name in ["powershell.exe", "cmd.exe", "wscript.exe"]`

**Encoded payload:** `"-enc"` or `"base64"` in `process.command_line`

**C2 beaconing:** Regular `conn_per_minute` with low variance to same `dst_ip` over 1-hour window

**Privilege escalation:** `process.interactive == False` + `user.name == "SYSTEM"` + `event.action == "process_started"` from unusual parent

**Data exfiltration:** High `conn_per_minute` to `is_internal_to_external == True` + `rare_protocol_flag`

---

## Step 6 — The `log_type` column's role in the ML pipeline

Your derived `log_type` column becomes a routing key in the inference pipeline:

```python
def route_to_model(feature_row):
    if feature_row["log_type"] == "network":
        return isolation_forest.predict(feature_row[NETWORK_FEATURES])
    elif feature_row["log_type"] == "process":
        return autoencoder.reconstruct_error(feature_row[PROCESS_FEATURES])
    elif feature_row["log_type"] == "security_alert":
        return rule_engine.score(feature_row[ALERT_FEATURES])
```

The final **threat score** is a weighted average of the three model outputs, normalized to 0–100:

```python
threat_score = 0.35 * network_score + 0.45 * process_score + 0.20 * alert_score
```

Weight the process model heavier because `process.command_line` is the richest and most reliable signal you have. The alert score acts as a floor — if Kibana already flagged it with a high `risk_score`, it should never score low.
