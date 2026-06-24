# Pre-Production Security Hardening Checklist

## Network Security
- [ ] Elasticsearch not exposed to public internet (internal network only)
- [ ] Only ports 443 (HTTPS) and necessary admin ports exposed
- [ ] Firewall rules restrict access to ISRO internal network ranges
- [ ] VPN required for remote analyst access (if applicable)

## Application Security
- [ ] JWT_SECRET_KEY generated with `openssl rand -hex 32`, NOT default value
- [ ] All default passwords changed (admin123, analyst123, viewer123)
- [ ] ES_VERIFY_CERTS=true in production
- [ ] DEBUG=false confirmed in production .env
- [ ] CORS_ORIGINS restricted to actual production domain only
- [ ] Rate limiting verified active on all sensitive endpoints
- [ ] Run `python backend/scripts/security_audit.py` — all checks PASS

## Data Security
- [ ] Elasticsearch encryption at rest enabled
- [ ] TLS 1.2+ enforced for all connections
- [ ] Backup encryption verified
- [ ] Secrets stored via secrets_manager, never in plaintext .env in production

## Access Control
- [ ] RBAC roles tested: viewer cannot access admin endpoints
- [ ] Audit logging confirmed active for all admin actions
- [ ] Default admin account password changed immediately post-deploy

## Monitoring
- [ ] Prometheus + Grafana accessible only to admin team
- [ ] Platform alerting (PA-001 through PA-008) verified functional
- [ ] Disk space, memory alerts tested

## Compliance
- [ ] Data governance document reviewed by ISRO compliance officer
- [ ] Data retention periods confirmed appropriate
- [ ] Third-party license audit completed and approved

## Final Sign-off
- [ ] Full test suite passes (`make test-full`)
- [ ] Smoke test passes against staging environment
- [ ] Load test results reviewed and acceptable
- [ ] Security audit script shows no FAIL results
- [ ] Disaster recovery runbook tested (restore from backup, verify)
