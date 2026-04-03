# Deployment Checklist

Use this checklist to ensure all components are properly configured before going live.

## Pre-Deployment

### Environment Setup
- [ ] GCP project created and billing enabled
- [ ] Service account created with required roles:
  - [ ] Storage Admin
  - [ ] BigQuery Admin
  - [ ] Airflow Worker (if using Cloud Composer)
- [ ] Service account key downloaded
- [ ] `.env` file created from `.env.example`
- [ ] `GOOGLE_APPLICATION_CREDENTIALS` path updated in `.env`
- [ ] `GOOGLE_CLOUD_PROJECT` set in `.env`

### Terraform
- [ ] Terraform >= 1.0 installed
- [ ] `terraform init` completed successfully
- [ ] `terraform plan` shows expected resources
- [ ] Variables reviewed (region, retention, etc.)
- [ ] `terraform apply` completed without errors
- [ ] Outputs noted (bucket_name, bq_table_id)
- [ ] State file stored securely (remote backend recommended)

### Docker/Airflow
- [ ] Docker >= 20.10 installed
- [ ] Docker Compose >= 2.0 installed
- [ ] `airflow/logs` directory created with write permissions
- [ ] `airflow/dags` directory exists
- [ ] `airflow/plugins` directory exists
- [ ] `docker compose up airflow-init` completed
- [ ] `docker compose up -d` started all services
- [ ] All containers healthy (`docker compose ps`)
- [ ] Airflow UI accessible (http://localhost:8080)
- [ ] Default credentials changed (admin/admin)

### Airflow Configuration
- [ ] Variable `project_id` created in Airflow UI
- [ ] DAG file visible in Airflow UI
- [ ] DAG parse successful (no errors)
- [ ] DAG toggled to Active
- [ ] Schedule verified (@daily)
- [ ] Catchup setting confirmed (True for backfill)

### dbt
- [ ] Python >= 3.9 installed
- [ ] dbt-bigquery installed (`pip install dbt-bigquery`)
- [ ] `profiles.yml` created in `~/.dbt/`
- [ ] BigQuery connection tested
- [ ] `dbt deps` completed
- [ ] `dbt run` completed successfully
- [ ] `dbt test` passed all tests
- [ ] Models visible in BigQuery UI

### Data Validation
- [ ] BigQuery table exists: `github_activity.github_events`
- [ ] Table is partitioned by `event_date`
- [ ] Table is clustered by `repo_name`, `actor_login`, `event_type`
- [ ] Sample data loaded (run DAG for test date)
- [ ] Partition pruning working (query cost check)
- [ ] dbt models materialized successfully
- [ ] `daily_stats` table populated
- [ ] `repo_health` table populated

### Looker Studio
- [ ] Looker Studio account accessible
- [ ] BigQuery connector authorized
- [ ] Data source created (github_activity dataset)
- [ ] Tile 1: Categorical analysis created
  - [ ] Event type pie chart
  - [ ] Top repos bar chart
  - [ ] Contributors table
- [ ] Tile 2: Temporal analysis created
  - [ ] Daily trend line chart
  - [ ] Hourly heatmap
  - [ ] Weekday/weekend scorecards
  - [ ] Health trend area chart
- [ ] Filters configured (date, event type, repo owner)
- [ ] Dashboard sharing settings configured

### Testing
- [ ] `make test` passes all pytest tests
- [ ] `make validate` passes all validation scripts
- [ ] Manual DAG run successful
- [ ] Data freshness verified
- [ ] Query performance acceptable (<5s for dashboard)

### Security
- [ ] Default Airflow credentials changed
- [ ] Service account key not committed to git
- [ ] `.env` file in `.gitignore`
- [ ] GCS bucket not publicly accessible
- [ ] BigQuery dataset access restricted
- [ ] Network access to Airflow restricted (if public)
- [ ] Audit logging enabled in GCP

### Documentation
- [ ] README.md reviewed and updated
- [ ] Architecture diagram accurate
- [ ] Team trained on dashboard usage
- [ ] Runbook created for common issues
- [ ] On-call rotation configured (if applicable)

### Monitoring & Alerts
- [ ] Airflow email alerts configured
- [ ] DAG failure notifications working
- [ ] BigQuery cost alerts set up
- [ ] Data freshness monitoring configured
- [ ] Dashboard access logging enabled

## Post-Deployment

### Day 1
- [ ] First automated DAG run successful
- [ ] Data visible in BigQuery
- [ ] Dashboard showing correct data
- [ ] No errors in Airflow logs
- [ ] Team notified of availability

### Week 1
- [ ] All daily DAG runs successful
- [ ] Data quality trends stable
- [ ] Query costs within budget
- [ ] User feedback collected
- [ ] Issues addressed

### Month 1
- [ ] 30-day retention working correctly
- [ ] Cost review completed
- [ ] Performance baseline established
- [ ] Documentation updated with lessons learned
- [ ] Backup/recovery tested

## Rollback Plan

If deployment fails:

1. **Stop Airflow**: `docker compose down`
2. **Destroy Terraform**: `cd terraform && terraform destroy`
3. **Delete BigQuery dataset**: `bq rm -r -f project_id:github_activity`
4. **Delete GCS bucket**: `gsutil rm -r gs://bucket-name`
5. **Fix issues** and restart from Pre-Deployment

## Support Contacts

- **Technical Lead**: [Name/Email]
- **Data Engineering**: [Team/Slack Channel]
- **Infrastructure**: [Team/Slack Channel]
- **Security**: [Email]

## Success Criteria

Deployment is successful when:

- ✅ All 5 Airflow tasks complete without errors
- ✅ Data loads to BigQuery daily
- ✅ dbt tests pass 100%
- ✅ Looker dashboard displays accurate data
- ✅ Query response time <5 seconds
- ✅ No security vulnerabilities
- ✅ Team can access and use dashboard

---

**Last Updated**: 2024-04-03  
**Version**: 1.0.0
