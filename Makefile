# GitHub AI Contributions - Makefile
# Common commands for development and deployment

.PHONY: help terraform-init terraform-apply terraform-destroy airflow-up airflow-down dbt-run dbt-test test validate clean

# Default target
help: ## Show this help message
	@echo "GitHub AI Contributions - Available Commands"
	@echo ""
	@echo "Usage: make [command]"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

# Terraform
terraform-init: ## Initialize Terraform
	cd terraform && terraform init

terraform-plan: ## Run Terraform plan
	cd terraform && terraform plan -var="project_id=$(PROJECT_ID)"

terraform-apply: ## Apply Terraform configuration
	cd terraform && terraform apply -var="project_id=$(PROJECT_ID)"

terraform-destroy: ## Destroy Terraform resources (WARNING: deletes everything)
	cd terraform && terraform destroy -var="project_id=$(PROJECT_ID)"

terraform-output: ## Show Terraform outputs
	cd terraform && terraform output

# Airflow
airflow-up: ## Start Airflow stack
	docker compose up -d
	@echo "Airflow UI: http://localhost:8080 (admin/admin)"

airflow-down: ## Stop Airflow stack
	docker compose down

airflow-logs: ## Show Airflow logs
	docker compose logs -f

airflow-init: ## Initialize Airflow database
	docker compose up airflow-init

airflow-restart: ## Restart Airflow stack
	docker compose down && docker compose up -d

# dbt
dbt-deps: ## Install dbt dependencies
	cd dbt && dbt deps

dbt-run: ## Run dbt models
	cd dbt && dbt run

dbt-test: ## Run dbt tests
	cd dbt && dbt test

dbt-build: ## Run dbt deps, run, and test
	cd dbt && dbt deps && dbt run && dbt test

dbt-docs: ## Generate and serve dbt documentation
	cd dbt && dbt docs generate && dbt docs serve

# Testing
test: ## Run all tests
	pytest tests/ -v

test-airflow: ## Run Airflow tests only
	pytest tests/test_airflow_dag.py -v

test-terraform: ## Run Terraform tests only
	pytest tests/test_terraform.py -v

test-dbt: ## Run dbt tests only
	pytest tests/test_dbt_models.py -v

# Validation
validate: ## Run all validation scripts
	bash scripts/run_all_validations.sh

validate-terraform: ## Validate Terraform configuration
	bash scripts/validate_terraform.sh

validate-airflow: ## Validate Airflow DAG
	bash scripts/validate_airflow.sh

validate-dbt: ## Validate dbt models
	bash scripts/validate_dbt.sh

# Development
clean: ## Clean temporary files and artifacts
	rm -rf airflow/logs/*
	rm -rf dbt/target/
	rm -rf terraform/.terraform/
	rm -rf terraform/*.tfstate*
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -name "*.pyc" -delete
	@echo "Cleaned temporary files"

install: ## Install Python dependencies
	pip install -r requirements.txt

lint: ## Run linting (if configured)
	@echo "Linting not configured yet"

# Deployment
deploy: validate terraform-apply airflow-up dbt-build ## Full deployment pipeline
	@echo "✅ Deployment complete!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Open Airflow UI: http://localhost:8080"
	@echo "2. Enable the DAG: github_activity_batch_pipeline"
	@echo "3. Create Looker Studio dashboard using looker/dashboard_config.md"

# Quick start for new users
quickstart: terraform-init install airflow-up
	@echo ""
	@echo "🚀 Quick start complete!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Edit .env with your GCP credentials"
	@echo "2. Run: make terraform-apply PROJECT_ID=your-project"
	@echo "3. Run: make dbt-build"
	@echo "4. Open Airflow: http://localhost:8080"
