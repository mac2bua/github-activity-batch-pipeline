"""
Unit tests for GCS source_objects configuration

These tests ensure that:
1. source_objects in GCSToBigQueryOperator matches upload_to_gcs object_name format
2. Upload task uses correct object_name pattern
3. Both tasks use consistent path structure
4. GHE Archive URL format is correct

Bug History:
- Original bug: source_objects was 'raw/{{ ds }}/' (directory)
- Upload task uploaded to 'data/{filename}' (files)
- GCSToBigQueryOperator couldn't find files because it looked for directory, not files
- Fix: source_objects should be 'data/*.json.gz' to match uploaded files

Run: pytest tests/test_gcs_source_objects.py -v
"""

import pytest
from pathlib import Path
import sys
import re

# Add dags directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'airflow' / 'dags'))


class TestUploadTaskPath:
    """Test upload_to_gcs task path construction"""

    def test_upload_object_name_format(self) -> None:
        """
        Test that upload_to_gcs uses correct object_name format.
        
        The upload function should create paths like:
        - data/2024-01-02-00.json.gz
        - data/2024-01-02-01.json.gz
        
        NOT:
        - raw/2024-01-02/2024-01-02-00.json.gz (old format)
        """
        import github_activity_pipeline
        import inspect
        
        source = inspect.getsource(github_activity_pipeline.upload_to_gcs)
        
        # Should use 'data/' prefix, not 'raw/'
        assert "'data/" in source or '"data/' in source, \
            "upload_to_gcs should use 'data/' prefix"
        
        # Should NOT use old 'raw/{ds}/' format
        assert "'raw/" not in source and '"raw/' not in source, \
            "upload_to_gcs should NOT use old 'raw/' prefix"
        
        # Should construct object_name from basename
        assert 'os.path.basename' in source, \
            "upload_to_gcs should use os.path.basename for filename"

    def test_upload_uses_data_prefix(self) -> None:
        """Test that upload uses 'data/' prefix consistently"""
        import github_activity_pipeline
        import inspect
        
        source = inspect.getsource(github_activity_pipeline.upload_to_gcs)
        
        # Object name should be: f'data/{filename}'
        assert re.search(r"object_name\s*=\s*f?['\"]data/", source), \
            "object_name should start with 'data/'"


class TestLoadTaskSourceObjects:
    """Test load_to_bigquery task source_objects configuration"""

    def test_source_objects_uses_wildcard(self) -> None:
        """
        Test that source_objects uses wildcard pattern to match files.
        
        Should be: 'data/*.json.gz'
        NOT: 'data/' (directory)
        
        The wildcard is critical because:
        1. Upload task uploads individual files: data/file.json.gz
        2. GCSToBigQueryOperator needs to match those files
        3. Directory pattern 'data/' won't match files
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
        
        # Pattern should start with data/
        assert pattern.startswith('data/'), \
            f"source_objects should start with 'data/', got: {pattern}"

    def test_source_objects_matches_upload_pattern(self) -> None:
        """
        Test that source_objects pattern matches what upload_to_gcs creates.
        
        Upload creates: data/filename.json.gz
        Load should match: data/*.json.gz
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
        assert 'data/' in pattern, "Pattern should include data/ prefix"
        assert '*.json.gz' in pattern, "Pattern should include *.json.gz wildcard"

    def test_source_objects_not_directory_only(self) -> None:
        """
        Test that source_objects is NOT just a directory pattern.
        
        This is the bug that caused:
        "404 Not found: URI gs://bucket/data/"
        
        The directory 'data/' doesn't exist as an object in GCS.
        Only individual files exist: data/file.json.gz
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


class TestPathConsistency:
    """Test that upload and load tasks use consistent paths"""

    def test_upload_and_load_use_same_prefix(self) -> None:
        """
        Test that both tasks use 'data/' prefix consistently.
        
        Upload: data/filename.json.gz
        Load: data/*.json.gz
        
        Both should use 'data/' as the base prefix.
        """
        import github_activity_pipeline
        import inspect
        
        # Check upload function
        upload_source = inspect.getsource(github_activity_pipeline.upload_to_gcs)
        assert "'data/" in upload_source or '"data/' in upload_source
        
        # Check load task
        load_task = None
        for task in github_activity_pipeline.dag.tasks:
            if task.task_id == 'load_to_bigquery':
                load_task = task
                break
        
        assert load_task is not None
        pattern = load_task.source_objects[0]
        assert pattern.startswith('data/')

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


class TestGHEArchiveURL:
    """Test GHE Archive URL configuration"""

    def test_url_format(self) -> None:
        """
        Test that GHE Archive URL uses correct format.
        
        Should be: https://data.gharchive.org
        NOT: https://gharchive.org/data/
        
        Files are at: https://data.gharchive.org/YYYY-MM-DD-HH.json.gz
        """
        import github_activity_pipeline
        
        # URL should be data.gharchive.org
        assert github_activity_pipeline.GHE_ARCHIVE_URL == 'https://data.gharchive.org', \
            f"GHE_ARCHIVE_URL should be 'https://data.gharchive.org', got: {github_activity_pipeline.GHE_ARCHIVE_URL}"

    def test_url_constructs_correct_path(self) -> None:
        """Test that URL constructs correct file path"""
        import github_activity_pipeline
        
        # Example: 2024-01-02-00.json.gz
        date_str = "2024-01-02"
        hour_str = "00"
        filename = f"{date_str}-{hour_str}.json.gz"
        url = f"{github_activity_pipeline.GHE_ARCHIVE_URL}/{filename}"
        
        expected = "https://data.gharchive.org/2024-01-02-00.json.gz"
        assert url == expected, f"URL should be {expected}, got: {url}"


class TestGCSObjectExistence:
    """Test understanding of GCS object structure"""

    def test_gcs_does_not_have_directory_objects(self) -> None:
        """
        Test understanding that GCS doesn't have real directories.
        
        GCS is flat - 'directories' are just prefixes in object names.
        When you upload to 'data/file.json.gz', GCS creates:
        - Object: data/file.json.gz
        
        It does NOT create:
        - Object: data/
        
        So GCSToBigQueryOperator with source_objects=['data/']
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
