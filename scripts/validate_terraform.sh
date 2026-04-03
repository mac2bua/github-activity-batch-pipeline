#!/bin/bash
# Validate Terraform configuration
set -e

echo "🔍 Validating Terraform configuration..."

cd "$(dirname "$0")/../terraform"

# Check if terraform is installed
if ! command -v terraform &> /dev/null; then
    echo "❌ Terraform not found. Install: https://developer.hashicorp.com/terraform/install"
    exit 1
fi

# Initialize (if not already)
if [ ! -d ".terraform" ]; then
    echo "📦 Initializing Terraform..."
    terraform init
fi

# Validate syntax
echo "✅ Validating syntax..."
terraform validate

# Format check
echo "📝 Checking formatting..."
terraform fmt -check -recursive || {
    echo "⚠️  Files need formatting. Run: terraform fmt -recursive"
}

# Security scan (if tfsec available)
if command -v tfsec &> /dev/null; then
    echo "🔒 Running security scan..."
    tfsec .
else
    echo "ℹ️  Install tfsec for security scanning: brew install tfsec"
fi

# Plan (dry-run)
echo "📊 Generating plan (dry-run)..."
terraform plan -out=tfplan -no-color > /dev/null 2>&1 && {
    echo "✅ Plan generated successfully"
    rm -f tfplan
} || {
    echo "⚠️  Plan failed. Set variables with: terraform plan -var=\"project_id=your-project\""
}

echo "✅ Terraform validation complete!"
