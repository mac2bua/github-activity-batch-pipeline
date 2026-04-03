"""
Unit tests for GitHub Activity Batch Pipeline tasks.

Tests each task function independently to catch bugs before DAG execution.
"""

import pytest
import json
import gzip
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

# Mock airflow before importing task functions
import sys
from unittest.mock import MagicMock

# Create mock airflow modules
sys.modules['airflow'] = MagicMock()
sys.modules['airflow.models'] = MagicMock()
sys.modules['airflow.operators'] = MagicMock()
sys.modules['airflow.operators.python'] = MagicMock()
sys.modules['airflow.operators.bash'] = MagicMock()
sys.modules['airflow.providers'] = MagicMock()
sys.modules['airflow.providers.google'] = MagicMock()
sys.modules['airflow.providers.google.cloud'] = MagicMock()
sys.modules['airflow.providers.google.cloud.hooks'] = MagicMock()
sys.modules['airflow.providers.google.cloud.hooks.gcs'] = MagicMock()
sys.modules['airflow.providers.google.cloud.transfers'] = MagicMock()
sys.modules['airflow.providers.google.cloud.transfers.gcs_to_bigquery'] = MagicMock()

# Import task functions
sys.path.insert(0, str(Path(__file__).parent.parent / 'airflow' / 'dags'))

# Now import the module and extract just the functions we need
import importlib.util
spec = importlib.util.spec_from_file_location(
    "pipeline_funcs",
    Path(__file__).parent.parent / 'airflow' / 'dags' / 'github_activity_pipeline.py'
)
pipeline_module = importlib.util.module_from_spec(spec)

# Mock the constants
pipeline_module.GCS_BUCKET = 'test-bucket'
pipeline_module.DATA_DIR = Path('/tmp/test_github_archive')
pipeline_module.BQ_DATASET = 'test_dataset'
pipeline_module.BQ_TABLE = 'test_table'
pipeline_module.PROJECT_ID = 'test-project'

# Mock GCSHook
mock_gcs_hook = MagicMock()
pipeline_module.GCSHook = MagicMock(return_value=mock_gcs_hook)

# Now we can import the functions
from github_activity_pipeline import (
    download_github_archive,
    upload_to_gcs,
    validate_data_quality,
    transform_ghe_to_schema,
)


class TestDownloadGithubArchive:
    """Tests for download_github_archive task."""
    
    @patch('github_activity_pipeline.requests.get')
    def test_download_success(self, mock_get):
        """Test successful download of multiple files."""
        # Mock successful response
        mock_response = Mock()
        mock_response.content = b'\x1f\x8b\x08\x00'  # gzip header
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Create mock context
        context = {
            'execution_date': datetime(2024, 1, 2),
            'ti': Mock()
        }
        
        # Ensure DATA_DIR exists
        pipeline_module.DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        result = download_github_archive(**context)
        
        assert 'Downloaded' in result
        assert context['ti'].xcom_push.called
        
    @patch('github_activity_pipeline.requests.get')
    def test_download_partial_404(self, mock_get):
        """Test download when some files return 404 (expected behavior)."""
        # Mock 404 for some hours
        def side_effect(url):
            if '10.json.gz' in url or '11.json.gz' in url:
                mock_404 = Mock()
                mock_404.raise_for_status.side_effect = Exception("404")
                mock_404.status_code = 404
                raise Exception("404")
            mock_response = Mock()
            mock_response.content = b'\x1f\x8b\x08\x00'
            mock_response.raise_for_status = Mock()
            return mock_response
        
        mock_get.side_effect = side_effect
        
        context = {
            'execution_date': datetime(2024, 1, 2),
            'ti': Mock()
        }
        
        pipeline_module.DATA_DIR.mkdir(parents=True, exist_ok=True)
        result = download_github_archive(**context)
        
        # Should still succeed with partial data
        assert 'Downloaded' in result


class TestUploadToGcs:
    """Tests for upload_to_gcs task."""
    
    @patch('github_activity_pipeline.GCSHook')
    @patch('github_activity_pipeline.glob.glob')
    def test_upload_success(self, mock_glob, mock_hook_class):
        """Test successful upload of files."""
        # Mock files exist
        mock_glob.return_value = ['/tmp/github_archive/2024-01-02-00.json.gz']
        
        # Mock hook
        mock_hook = Mock()
        mock_hook_class.return_value = mock_hook
        
        result = upload_to_gcs()
        
        assert 'Uploaded' in result
        mock_hook.upload.assert_called_once()
        
    @patch('github_activity_pipeline.GCSHook')
    @patch('github_activity_pipeline.glob.glob')
    def test_upload_no_files(self, mock_glob, mock_hook_class):
        """Test upload when no files exist."""
        mock_glob.return_value = []
        
        result = upload_to_gcs()
        
        assert 'No files to upload' in result


class TestValidateDataQuality:
    """Tests for validate_data_quality task."""
    
    @patch('github_activity_pipeline.GCSHook')
    def test_validation_success(self, mock_hook_class):
        """Test successful validation with files present."""
        mock_hook = Mock()
        mock_hook.list.return_value = ['data/file1.json.gz', 'data/file2.json.gz']
        
        # Mock get_blob to return blob with size
        mock_blob1 = Mock()
        mock_blob1.size = 1024
        mock_blob2 = Mock()
        mock_blob2.size = 2048
        mock_hook.get_blob.side_effect = [mock_blob1, mock_blob2]
        
        mock_hook_class.return_value = mock_hook
        
        result = validate_data_quality()
        
        assert result['valid'] is True
        assert result['file_count'] == 2
        assert result['total_size_bytes'] == 3072
        
    @patch('github_activity_pipeline.GCSHook')
    def test_validation_no_files(self, mock_hook_class):
        """Test validation fails when no files exist."""
        mock_hook = Mock()
        mock_hook.list.return_value = []
        mock_hook_class.return_value = mock_hook
        
        result = validate_data_quality()
        
        assert result['valid'] is False
        assert result['reason'] == 'No files found'


class TestTransformGheToSchema:
    """Tests for transform_ghe_to_schema task."""
    
    @patch('github_activity_pipeline.GCSHook')
    @patch('github_activity_pipeline.os.unlink')
    def test_transform_success(self, mock_unlink, mock_hook_class):
        """Test successful transformation of GHE data."""
        mock_hook = Mock()
        mock_hook.list.return_value = ['data/2024-01-02-00.json.gz']
        
        # Create sample GHE Archive data
        sample_event = {
            'id': '39324579438',
            'type': 'CreateEvent',
            'actor': {'id': 101632126, 'login': 'testuser', 'display_login': 'testuser'},
            'repo': {'id': 815527809, 'name': 'testuser/testrepo', 'url': 'https://...'},
            'payload': {'ref': None, 'ref_type': 'repository'},
            'public': True,
            'created_at': '2024-01-02T00:00:00Z'
        }
        
        # Mock download to return gzipped JSON
        with tempfile.NamedTemporaryFile(suffix='.json.gz', delete=False) as tmp:
            with gzip.open(tmp.name, 'wt') as f:
                f.write(json.dumps(sample_event) + '\n')
            with open(tmp.name, 'rb') as f:
                mock_hook.download.return_value = f.read()
            os.unlink(tmp.name)
        
        mock_hook_class.return_value = mock_hook
        
        result = transform_ghe_to_schema()
        
        assert 'Transformed' in result
        assert mock_hook.upload.called
        
        # Verify transformed data structure
        call_args = mock_hook.upload.call_args
        assert call_args[1]['object_name'] == 'transformed/2024-01-02-00.json.gz'
        
    @patch('github_activity_pipeline.GCSHook')
    def test_transform_no_source_files(self, mock_hook_class):
        """Test transform when no source files exist."""
        mock_hook = Mock()
        mock_hook.list.return_value = []
        mock_hook_class.return_value = mock_hook
        
        result = transform_ghe_to_schema()
        
        assert 'No files to transform' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
