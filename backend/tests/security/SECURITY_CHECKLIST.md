# SOC Platform Security Checklist (OWASP Top 10)

This document outlines the implementation and testing status of OWASP Top 10 security constraints within the SOC Platform architecture.

## Automated Coverage

The `test_owasp.py` module automatically asserts the following protection mechanisms using `pytest` and `httpx`:

### 1. Broken Access Control (A01:2021)
- **Covered**: Endpoints are bound via JWT extraction ensuring missing/expired tokens throw strict `401 Unauthorized` errors.
- **Covered**: RBAC logic ensuring basic Viewer/Analyst tokens are blocked (`403 Forbidden`) from hitting Admin-only administrative routes like Model Reloads and Training Kickoffs.

### 2. Cryptographic Failures (A02:2021)
- **Covered**: Health endpoints dynamically strip exact JSON responses ensuring `.env` variables (e.g. `ES_PASSWORD`) are never dumped natively into browser space.

### 3. Injection (A03:2021)
- **Covered**: URL Param sanitization—FastAPI strict-typing correctly 422s malformed payload strings mapping SQLi attempts (e.g., `status=' OR 1=1--`).
- **Covered**: Prompt Injection bounds on the `/api/slm/chat` endpoint testing against `<|system|>` override attacks.
- **Covered**: Path Traversal natively caught via FastAPI strict URI validation (`404` or `422` against `../../etc/passwd`).

### 4. Insecure Design (A04:2021)
- **Covered**: Hard-limited rate-limiting assertions checking brute-force login limits (10/min) and heavy AI inference limits (20/min).

### 5. Security Misconfiguration (A05:2021)
- **Covered**: Explicit `500 Internal Server Error` checks asserting raw Python `Traceback` stack-traces are masked and replaced with generic handler errors.
- **Covered**: Ensuring `/api/slm/status` obfuscates actual Docker volume paths and local filesystem mappings.

---

## Manual Testing & Penetration Steps

The following items should be validated natively by human QA or external penetration teams before production:

### 1. XSS Execution (A03:2021 / A07:2017)
While `test_owasp.py` proves the backend natively *stores* XSS payloads safely (e.g., `<script>alert(1)</script>` in feedback notes), QA must test the React Frontend (`AlertDetail.jsx`) to ensure data is safely mounted via standard `react-dom` text bindings and not forcibly injected via `dangerouslySetInnerHTML`.

### 2. Vulnerable and Outdated Components (A06:2021)
- **Action**: Run `pip-audit` locally on the backend environment.
- **Action**: Run `npm audit` on the frontend environment.

### 3. Identification and Authentication Failures (A07:2021)
- **Action**: Verify Password Complexity and MFA setups inside the external IDP (e.g., Okta/Keycloak) supplying the JWT tokens, as the SOC platform natively trusts the upstream signature.

### 4. Software and Data Integrity Failures (A08:2021)
- **Action**: Validate Docker supply chain bounds—ensure the ML model weights (`isolation_forest.pkl`, `autoencoder.pt`) are securely signed and tracked via MLFlow rather than pulled dynamically over plaintext HTTP.

### 5. Server-Side Request Forgery (SSRF) (A10:2021)
- **Action**: Currently, the platform does not natively accept dynamic URLs to pull from external web resources. If Webhooks or OSINT integrations are added, they must be validated to drop internal `.svc.cluster.local` loops.

## How to Run Security Tests
```bash
pytest backend/tests/security/ -v --tb=short
```
