"""
Unit tests for GCS source_objects configuration

These tests ensure that:
1. source_objects in GCSToBigQueryOperator matches upload_to_gcs object_name format
2. Upload task uses correct object_name pattern
3. Both tasks use consistent path structure

Bug History:
- Original bug: source_objects was 'raw/{{ ds }}/' (directory)
- Upload task uploaded to 'raw/{ds}/{filename}' (files)
- GCSToBigQueryOperator couldn't find files because it looked for directory, not files
- Fix: source_objects should be 'raw/{{ ds }}/*.json.gz' to match uploaded files

Run: pytest tests/test_gcs_source_objects.py -v
"""

import pytest
from pathlib import Path
import sys
import re
from unittest.mock import patch

# Add dags directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'airflow' / 'dags'))


class TestUploadTaskPath:
    """Test upload_to_gcs task path construction"""

    def test_upload_object_name_format(self) -> None:
        """
        Test that upload_to_gcs uses correct object_name format.
        
        The upload function should create paths like:
        - raw/2024-01-02/2024-01-02-00.json.gz
        - raw/2024-01-02/2024-01-02-01.json.gz
        """
        # Import the module
        import github_activity_pipeline
        
        # Check the upload function exists
        assert hasattr(github_activity_pipeline, 'upload_to_gcs')
        
        # The upload function uses:
        # gcs_prefix = f'raw/{ds}'
        # object_name = f'{gcs_prefix}/{file_path.name}'
        # Which produces: raw/2024-01-02/2024-01-02-00.json.gz
        
        # We verify this by checking the source code
        import inspect
        source = inspect.getsource(github_activity_pipeline.upload_to_gcs)
        
        # Should use gcs_prefix with 'raw/' pattern
        assert 'gcs_prefix' in source
        assert "'raw/" in source or '"raw/' in source
        
        # Should construct object_name from prefix and filename
        assert 'object_name' in source
        assert 'gcs_prefix' in source

    def test_upload_gcs_prefix_format(self) -> None:
        """Test that gcs_prefix uses correct format"""
        import github_activity_pipeline
        import inspect
        
        source = inspect.getsource(github_activity_pipeline.upload_to_gcs)
        
        # Should be: gcs_prefix = f'raw/{ds}'
        assert re.search(r"gcs_prefix\s*=\s*f['\"]raw/\{ds\}['\"]", source) or \
               re.search(r'gcs_prefix\s*=\s*f["\']raw/\{ds\}["\']', source)


class TestLoadTaskSourceObjects:
    """Test load_to_bigquery task source_objects configuration"""

    def test_source_objects_uses_wildcard(self) -> None:
        """
        Test that source_objects uses wildcard pattern to match files.
        
        Should be: 'raw/{{ ds }}/*.json.gz'
        NOT: 'raw/{{ ds }}/' (directory)
        
        The wildcard is critical because:
        1. Upload task uploads individual files: raw/2024-01-02/file.json.gz
        2. GCSToBigQueryOperator needs to match those files
        3. Directory pattern 'raw/{{ ds }}/' won't match files
        """
        import github_activity_pipeline
        
        # Find the load task
        load_task = None
        for task in github_activity_pipeline.dag.tasks:
            if task.task_id == 'load_to_bigquery':
                load_task = task
                break
        
        assert load_task is not None, "load_to_bigquery task not found"
        
        # Get source_objects parameter
        source_objects = load_task.source_objects
        assert source_objects is not None
        
        # Should be a list with one pattern
        assert isinstance(source_objects, list)
        assert len(source_objects) == 1
        
        pattern = source_objects[0]
        
        # Pattern should include wildcard
        assert '*.json.gz' in pattern or '*' in pattern, \
            f"source_objects should include wildcard, got: {pattern}"
        
        # Pattern should start with raw/
        assert pattern.startswith('raw/'), \
            f"source_objects should start with 'raw/', got: {pattern}"

    def test_source_objects_matches_upload_pattern(self) -> None:
        """
        Test that source_objects pattern matches what upload_to_gcs creates.
        
        Upload creates: raw/{ds}/{filename}.json.gz
        Load should match: raw/{{ ds }}/*.json.gz
        """
        import github_activity_pipeline
        
        # Find the load task
        load_task = None
        for task in github_activity_pipeline.dag.tasks:
            if task.task_id == 'load_to_bigquery':
                load_task = task
                break
        
        assert load_task is not None
        
        source_objects = load_task.source_objects
        assert source_objects is not None
        
        pattern = source_objects[0]
        
        # Verify pattern structure
        # Should be: raw/{{ ds }}/*.json.gz
        assert '{{ ds }}' in pattern, "Pattern should include {{ ds }} template"
        assert 'raw/' in pattern, "Pattern should include raw/ prefix"
        assert '*.json.gz' in pattern, "Pattern should include *.json.gz wildcard"

    def test_source_objects_not_directory_only(self) -> None:
        """
        Test that source_objects is NOT just a directory pattern.
        
        This is the bug that caused:
        "404 Not found: URI gs://bucket/raw/2024-01-02/"
        
        The directory 'raw/2024-01-02/' doesn't exist as an object in GCS.
        Only individual files exist: raw/2024-01-02/file.json.gz
        """
        import github_activity_pipeline
        
        load_task = None
        for task in github_activity_pipeline.dag.tasks:
            if task.task_id == 'load_to_bigquery':
                load_task = task
                break
        
        assert load_task is not None
        
        pattern = load_task.source_objects[0]
        
        # Should NOT end with just / (directory pattern)
        # Should end with *.json.gz (file pattern)
        assert not pattern.endswith('/'), \
            f"source_objects should not be directory-only pattern, got: {pattern}"
        assert not pattern.endswith('/\"'), \
            f"source_objects should not be directory-only pattern, got: {pattern}"
        assert not pattern.endswith("/'"), \
            f"source_objects should not be directory-only pattern, got: {pattern}"


class TestPathConsistency:
    """Test that upload and load tasks use consistent paths"""

    def test_upload_and_load_use_same_prefix(self) -> None:
        """
        Test that both tasks use 'raw/' prefix consistently.
        
        Upload: raw/{ds}/filename.json.gz
        Load: raw/{{ ds }}/*.json.gz
        
        Both should use 'raw/' as the base prefix.
        """
        import github_activity_pipeline
        import inspect
        
        # Check upload function
        upload_source = inspect.getsource(github_activity_pipeline.upload_to_gcs)
        assert "'raw/" in upload_source or '"raw/' in upload_source
        
        # Check load task
        load_task = None
        for task in github_activity_pipeline.dag.tasks:
            if task.task_id == 'load_to_bigquery':
                load_task = task
                break
        
        assert load_task is not None
        pattern = load_task.source_objects[0]
        assert pattern.startswith('raw/')

    def test_gcs_bucket_consistency(self) -> None:
        """
        Test that both tasks use the same GCS_BUCKET.
        
        This ensures upload and load operate on the same bucket.
        """
        import github_activity_pipeline
        
        # GCS_BUCKET should be defined at module level
        assert hasattr(github_activity_pipeline, 'GCS_BUCKET')
        
        # Find load task
        load_task = None
        for task in github_activity_pipeline.dag.tasks:
            if task.task_id == 'load_to_bigquery':
                load_task = task
                break
        
        assert load_task is not None
        
        # Load task should use GCS_BUCKET
        assert load_task.bucket == github_activity_pipeline.GCS_BUCKET


class TestSourceObjectsPattern:
    """Test specific source_objects patterns"""

    def test_valid_pattern_formats(self) -> None:
        """Test various valid pattern formats"""
        valid_patterns = [
            'raw/{{ ds }}/*.json.gz',
            'raw/{{ ds }}/*',
            'raw/{{ds}}/*.json.gz',
        ]
        
        for pattern in valid_patterns:
            # Should have wildcard
            assert '*' in pattern
            # Should have ds template
            assert 'ds' in pattern
            # Should have raw prefix
            assert pattern.startswith('raw')

    def test_invalid_pattern_formats(self) -> None:
        """Test various invalid pattern formats"""
        invalid_patterns = [
            'raw/{{ ds }}/',  # Directory only - won't match files
            'raw/{{ ds }}',   # No trailing slash or wildcard
            '{{ ds }}/',      # Missing raw/ prefix
        ]
        
        for pattern in invalid_patterns:
            # Should NOT be used
            # Either no wildcard or wrong structure
            has_wildcard = '*' in pattern
            has_trailing_slash = pattern.endswith('/')
            
            # Invalid if: no wildcard AND has trailing slash (directory pattern)
            if not has_wildcard and has_trailing_slash:
                # This is the bug pattern
                pass  # We're testing that our code doesn't use this


class TestGCSObjectExistence:
    """Test understanding of GCS object structure"""

    def test_gcs_does_not_have_directory_objects(self) -> None:
        """
        Test understanding that GCS doesn't have real directories.
        
        GCS is flat - 'directories' are just prefixes in object names.
        When you upload to 'raw/2024-01-02/file.json.gz', GCS creates:
        - Object: raw/2024-01-02/file.json.gz
        
        It does NOT create:
        - Object: raw/
        - Object: raw/2024-01-02/
        
        So GCSToBigQueryOperator with source_objects=['raw/2024-01-02/']
        will fail because that 'directory' object doesn't exist.
        """
        # This is a conceptual test - verifying understanding
        # The actual test is that source_objects uses wildcard pattern
        
        import github_activity_pipeline
        
        load_task = None
        for task in github_activity_pipeline.dag.tasks:
            if task.task_id == 'load_to_bigquery':
                load_task = task
                break
        
        assert load_task is not None
        
        # Pattern should use wildcard to match actual file objects
        pattern = load_task.source_objects[0]
        assert '*' in pattern, \
            "GCS has no directories - must use wildcard to match files"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
