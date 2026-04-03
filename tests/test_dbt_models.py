"""
Test dbt models
Run: pytest tests/test_dbt_models.py
"""

import pytest
from pathlib import Path
import re


class TestDbtStructure:
    """Test dbt project structure"""
    
    @pytest.fixture
    def dbt_dir(self):
        return Path(__file__).parent.parent / 'dbt'
    
    def test_dbt_project_yml_exists(self, dbt_dir):
        """Test dbt_project.yml exists"""
        assert (dbt_dir / 'dbt_project.yml').exists()
    
    def test_models_dir_exists(self, dbt_dir):
        """Test models directory exists"""
        assert (dbt_dir / 'models').exists()
    
    def test_staging_dir_exists(self, dbt_dir):
        """Test staging directory exists"""
        assert (dbt_dir / 'models' / 'staging').exists()
    
    def test_marts_dir_exists(self, dbt_dir):
        """Test marts directory exists"""
        assert (dbt_dir / 'models' / 'marts').exists()


class TestStagingModel:
    """Test staging model"""
    
    @pytest.fixture
    def stg_content(self):
        dbt_dir = Path(__file__).parent.parent / 'dbt'
        return (dbt_dir / 'models' / 'staging' / 'stg_github_events.sql').read_text()
    
    def test_staging_file_exists(self):
        """Test staging model file exists"""
        dbt_dir = Path(__file__).parent.parent / 'dbt'
        assert (dbt_dir / 'models' / 'staging' / 'stg_github_events.sql').exists()
    
    def test_has_config(self, stg_content):
        """Test model has dbt config"""
        assert '{{' in stg_content
        assert 'config(' in stg_content
    
    def test_materialized_as_view(self, stg_content):
        """Test staging model is materialized as view"""
        assert "materialized='view'" in stg_content
    
    def test_has_cte(self, stg_content):
        """Test model uses CTEs"""
        assert 'with' in stg_content.lower()
    
    def test_selects_from_source(self, stg_content):
        """Test model selects from source"""
        assert 'source(' in stg_content or 'ref(' in stg_content
    
    def test_has_data_quality_checks(self, stg_content):
        """Test model has data quality flags"""
        assert 'is_valid' in stg_content.lower()


class TestDailyStatsMart:
    """Test daily_stats mart"""
    
    @pytest.fixture
    def daily_stats_content(self):
        dbt_dir = Path(__file__).parent.parent / 'dbt'
        return (dbt_dir / 'models' / 'marts' / 'daily_stats.sql').read_text()
    
    def test_daily_stats_exists(self):
        """Test daily_stats file exists"""
        dbt_dir = Path(__file__).parent.parent / 'dbt'
        assert (dbt_dir / 'models' / 'marts' / 'daily_stats.sql').exists()
    
    def test_materialized_as_table(self, daily_stats_content):
        """Test mart is materialized as table"""
        assert "materialized='table'" in daily_stats_content
    
    def test_has_partitioning(self, daily_stats_content):
        """Test mart has partitioning config"""
        assert 'partition_by' in daily_stats_content
    
    def test_has_clustering(self, daily_stats_content):
        """Test mart has clustering config"""
        assert 'cluster_by' in daily_stats_content
    
    def test_has_aggregations(self, daily_stats_content):
        """Test mart has aggregations"""
        assert 'count(' in daily_stats_content.lower()
        assert 'sum(' in daily_stats_content.lower()
    
    def test_references_staging(self, daily_stats_content):
        """Test mart references staging model"""
        assert "ref('stg_github_events')" in daily_stats_content


class TestRepoHealthMart:
    """Test repo_health mart"""
    
    @pytest.fixture
    def repo_health_content(self):
        dbt_dir = Path(__file__).parent.parent / 'dbt'
        return (dbt_dir / 'models' / 'marts' / 'repo_health.sql').read_text()
    
    def test_repo_health_exists(self):
        """Test repo_health file exists"""
        dbt_dir = Path(__file__).parent.parent / 'dbt'
        assert (dbt_dir / 'models' / 'marts' / 'repo_health.sql').exists()
    
    def test_has_health_score(self, repo_health_content):
        """Test mart calculates health score"""
        assert 'health_score' in repo_health_content.lower()
    
    def test_has_activity_metrics(self, repo_health_content):
        """Test mart has activity metrics"""
        assert 'push_events' in repo_health_content
        assert 'pr_events' in repo_health_content
    
    def test_has_classification(self, repo_health_content):
        """Test mart has health classification"""
        assert 'health_status' in repo_health_content
        assert 'Healthy' in repo_health_content


class TestSchemaYml:
    """Test schema.yml documentation"""
    
    @pytest.fixture
    def schema_content(self):
        dbt_dir = Path(__file__).parent.parent / 'dbt'
        return (dbt_dir / 'models' / 'schema.yml').read_text()
    
    def test_schema_file_exists(self):
        """Test schema.yml exists"""
        dbt_dir = Path(__file__).parent.parent / 'dbt'
        assert (dbt_dir / 'models' / 'schema.yml').exists()
    
    def test_has_version(self, schema_content):
        """Test schema has version"""
        assert 'version: 2' in schema_content
    
    def test_has_model_tests(self, schema_content):
        """Test schema has model tests"""
        assert 'tests:' in schema_content
    
    def test_has_descriptions(self, schema_content):
        """Test schema has column descriptions"""
        assert 'description:' in schema_content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
