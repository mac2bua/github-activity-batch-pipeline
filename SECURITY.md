# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability:

### DO:
- **Report privately** via GitHub Security Advisories
- Email: security@your-org.com (if applicable)
- Include detailed reproduction steps
- Allow 48 hours for initial response

### DON'T:
- Create public GitHub issues
- Disclose publicly before coordinated disclosure
- Exploit the vulnerability beyond testing

## Security Best Practices

### Infrastructure (Terraform)

**GCS Bucket:**
- ✅ Uniform bucket-level access enabled
- ✅ Versioning for data recovery
- ✅ Lifecycle rules for automatic cleanup
- ⚠️ Ensure bucket is not publicly accessible
- ⚠️ Use VPC Service Controls for sensitive data

**BigQuery:**
- ✅ Partitioning limits data scan costs
- ✅ Clustering improves query performance
- ⚠️ Enable data access audit logs
- ⚠️ Use column-level security for sensitive fields
- ⚠️ Implement row-level security if needed

### Airflow

**Authentication:**
- ✅ Basic auth enabled by default
- ⚠️ Change default credentials immediately
- ⚠️ Use RBAC for production
- ⚠️ Enable OAuth/SAML for SSO

**Network:**
- ⚠️ Don't expose Airflow UI publicly
- ⚠️ Use VPN or SSH tunnel for access
- ⚠️ Restrict worker egress if possible

**Credentials:**
- ✅ Service account key mounted as volume
- ⚠️ Use Workload Identity in GKE
- ⚠️ Rotate credentials regularly
- ⚠️ Never commit credentials to git

### dbt

**Data Access:**
- ✅ Uses BigQuery service account
- ⚠️ Limit dataset permissions to least privilege
- ⚠️ Audit model outputs for PII

### Docker Compose

**Container Security:**
- ⚠️ Don't run as root (AIRFLOW_UID set)
- ⚠️ Use specific image versions (not :latest)
- ⚠️ Scan images for vulnerabilities
- ⚠️ Limit container capabilities

### General

**Secrets Management:**
- ✅ .env.example provided (no secrets)
- ✅ .gitignore excludes .env and *.key
- ⚠️ Use secrets manager in production
- ⚠️ Rotate all credentials quarterly

**Monitoring:**
- ⚠️ Enable Cloud Audit Logs
- ⚠️ Monitor BigQuery access patterns
- ⚠️ Alert on unusual data access
- ⚠️ Track Airflow DAG failures

**Data Retention:**
- ✅ 90-day retention in BigQuery
- ✅ 90-day lifecycle rule in GCS
- ⚠️ Adjust based on compliance needs

## Security Checklist for Deployment

- [ ] Change default Airflow credentials
- [ ] Restrict network access to Airflow UI
- [ ] Enable BigQuery audit logging
- [ ] Verify GCS bucket is private
- [ ] Rotate service account keys
- [ ] Review IAM permissions
- [ ] Enable VPC Service Controls (if applicable)
- [ ] Set up security monitoring alerts
- [ ] Document incident response procedure

## Known Limitations

1. **Basic Auth**: Default Airflow setup uses basic auth. Upgrade to RBAC + OAuth for production.

2. **Service Account Keys**: Using key files instead of Workload Identity. Consider migrating to WI.

3. **No Encryption at Rest**: GCS and BigQuery use Google-managed keys. Use CMEK for sensitive data.

4. **No DLP Scanning**: No automated PII detection. Add Cloud DLP if processing sensitive data.

## Incident Response

If you suspect a security incident:

1. **Contain**: Stop affected services
2. **Assess**: Determine scope and impact
3. **Notify**: Alert security team and stakeholders
4. **Remediate**: Fix vulnerability
5. **Review**: Post-incident analysis and improvements

## Compliance Notes

This pipeline may process public GitHub data. Consider:

- **GDPR**: GitHub usernames may be personal data
- **CCPA**: Similar considerations for California residents
- **Data Residency**: Ensure GCP region complies with local laws
- **Retention**: Adjust retention periods per policy

## Contact

Security questions: security@your-org.com

---

Last updated: 2024-04-03
