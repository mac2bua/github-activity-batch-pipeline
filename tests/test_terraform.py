"""
Test Terraform configuration
Run: pytest tests/test_terraform.py
"""

import pytest
import re
from pathlib import Path


class TestTerraformFiles:
    """Test Terraform file structure"""
    
    @pytest.fixture
    def terraform_dir(self):
        return Path(__file__).parent.parent / 'terraform'
    
    def test_main_tf_exists(self, terraform_dir):
        """Test main.tf exists"""
        assert (terraform_dir / 'main.tf').exists()
    
    def test_variables_tf_exists(self, terraform_dir):
        """Test variables.tf exists"""
        assert (terraform_dir / 'variables.tf').exists()
    
    def test_outputs_tf_exists(self, terraform_dir):
        """Test outputs.tf exists"""
        assert (terraform_dir / 'outputs.tf').exists()


class TestGCSBucket:
    """Test GCS bucket configuration"""
    
    @pytest.fixture
    def main_tf_content(self):
        terraform_dir = Path(__file__).parent.parent / 'terraform'
        return (terraform_dir / 'main.tf').read_text()
    
    def test_bucket_resource_exists(self, main_tf_content):
        """Test GCS bucket resource is defined"""
        assert 'google_storage_bucket' in main_tf_content
    
    def test_bucket_versioning(self, main_tf_content):
        """Test bucket versioning is enabled"""
        assert 'versioning' in main_tf_content
        assert 'enabled = true' in main_tf_content
    
    def test_bucket_lifecycle_rule(self, main_tf_content):
        """Test bucket has lifecycle rules"""
        assert 'lifecycle_rule' in main_tf_content
    
    def test_bucket_location(self, main_tf_content):
        """Test bucket has location defined"""
        assert 'location' in main_tf_content


class TestBigQueryTable:
    """Test BigQuery table configuration"""
    
    @pytest.fixture
    def main_tf_content(self):
        terraform_dir = Path(__file__).parent.parent / 'terraform'
        return (terraform_dir / 'main.tf').read_text()
    
    def test_table_resource_exists(self, main_tf_content):
        """Test BigQuery table resource is defined"""
        assert 'google_bigquery_table' in main_tf_content
    
    def test_time_partitioning(self, main_tf_content):
        """Test table has time partitioning"""
        assert 'time_partitioning' in main_tf_content
        assert 'type' in main_tf_content
        assert 'DAY' in main_tf_content
    
    def test_clustering(self, main_tf_content):
        """Test table has clustering configured"""
        assert 'clustering' in main_tf_content
    
    def test_partition_field(self, main_tf_content):
        """Test partition field is event_date"""
        assert 'event_date' in main_tf_content
    
    def test_schema_defined(self, main_tf_content):
        """Test table schema is defined"""
        assert 'schema' in main_tf_content
        assert 'event_id' in main_tf_content
        assert 'event_type' in main_tf_content


class TestOutputs:
    """Test Terraform outputs"""
    
    @pytest.fixture
    def outputs_content(self):
        terraform_dir = Path(__file__).parent.parent / 'terraform'
        return (terraform_dir / 'outputs.tf').read_text()
    
    def test_bucket_name_output(self, outputs_content):
        """Test bucket_name output exists"""
        assert 'bucket_name' in outputs_content
    
    def test_bq_table_id_output(self, outputs_content):
        """Test bq_table_id output exists"""
        assert 'bq_table_id' in outputs_content
    
    def test_project_id_output(self, outputs_content):
        """Test project_id output exists"""
        assert 'project_id' in outputs_content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
