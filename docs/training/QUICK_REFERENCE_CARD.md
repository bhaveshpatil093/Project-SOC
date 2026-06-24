# SOC Platform Quick Reference

## Threat Score Guide
| Score | Severity | Required Action |
|-------|----------|-----------------|
| 🟢 **0-30** | Low | Monitor only. Often closed automatically. |
| 🟡 **30-60** | Medium | Review within 4 hours. |
| 🟠 **60-80** | High | Review within 30 minutes. |
| 🔴 **80-100** | Critical | Review within 15 minutes. Escalate if confirmed. |

---

## Workbench Shortcuts
*Use these keys to rapidly triage the Alert Queue without using your mouse.*

- `T` = Mark as **True Positive** (Real threat)
- `F` = Mark as **False Positive** (Authorized / Normal behavior)
- `B` = Mark as **Benign** (Abnormal but harmless, e.g. broken config)
- `I` = Open **Investigate** chat pane
- `E` = Open **Escalate** dialog
- `N` = Move to **Next** alert
- `P` = Move to **Previous** alert

---

## When to Escalate
You must hit the Escalate button and notify L2/Incident Response immediately if:
- A Critical alert is confirmed as a True Positive.
- You detect a **Multi-stage incident** (an attacker successfully chaining 3+ MITRE tactics).
- **Lateral movement** or **Data Exfiltration** is confirmed.
- A previously Watchlisted entity or VIP user triggers a new alert.

---

## Good SLM Questions
*The AI Assistant requires clear context. Use these prompts for the best results.*

- ✅ "Why was this alert flagged? Summarize the SHAP features."
- ✅ "Has this specific host had similar alerts in the past 30 days?"
- ✅ "What should I check first to verify if this PowerShell command is malicious?"
- ✅ "Summarize the timeline of this incident in bullet points."

*Avoid these behaviors:*
- ❌ Avoid simple yes/no questions ("Is this bad?").
- ❌ Do not ask the AI to make the final triage decision for you. It is an assistant, not an oracle.
- ❌ Do not assume the AI is perfectly accurate. Always verify its claims against the raw logs.
