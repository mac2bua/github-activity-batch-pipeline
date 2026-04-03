.PHONY: help terraform-init terraform-apply airflow-up dbt-run

help:
	@echo "GitHub Activity Pipeline - Commands:"
	@echo "  make terraform-init   - Initialize Terraform"
	@echo "  make terraform-apply  - Apply infrastructure"
	@echo "  make airflow-up       - Start Airflow"
	@echo "  make airflow-down     - Stop Airflow"
	@echo "  make dbt-run          - Run dbt models"

terraform-init:
	cd terraform && terraform init

terraform-apply:
	cd terraform && terraform apply -var="project_id=$(GCP_PROJECT_ID)" -var="environment=dev"

airflow-up:
	cd airflow && docker-compose up -d

airflow-down:
	cd airflow && docker-compose down

dbt-run:
	cd dbt && dbt run
