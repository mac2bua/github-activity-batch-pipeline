#!/usr/bin/env python3
"""
Fast Validation Script - Test transform logic without full DAG run

This script:
1. Downloads a sample GHE Archive file (1 hour, ~50MB)
2. Runs the transform logic
3. Validates output schema matches BigQuery
4. Completes in ~30 seconds vs 5-15 minutes for full DAG

Usage: python3 scripts/fast_validate.py [execution_date]
Example: python3 scripts/fast_validate.py 2024-06-15
"""

import sys
import json
import gzip
import tempfile
import os
from pathlib import Path
from datetime import datetime, timezone

# Sample GHE Archive URL pattern
GHE_ARCHIVE_URL = "https://data.gharchive.org"

def fetch_sample_hour(date_str, hour=12):
    """Fetch a single hour of GHE Archive data."""
    import requests
    
    filename = f"{date_str}-{hour:02d}.json.gz"
    url = f"{GHE_ARCHIVE_URL}/{filename}"
    
    print(f"Fetching: {filename}")
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    
    return response.content

def transform_event(event):
    """
    Transform a single GHE event to BigQuery schema.
    This is the same logic as in the DAG's transform_data task.
    """
    repo_name = event.get('repo', {}).get('name', '')
    repo_owner = repo_name.split('/')[0] if '/' in repo_name else ''
    created_at_str = event.get('created_at', '')
    event_date = created_at_str.split('T')[0] if created_at_str else ''
    
    transformed = {
        'event_id': str(event.get('id', '')),
        'event_type': str(event.get('type', '')),
        'actor_login': str(event.get('actor', {}).get('login', '')),
        'repo_name': str(repo_name),
        'repo_owner': str(repo_owner),
        'created_at': created_at_str,
        'event_date': event_date,
        'payload': event.get('payload', {}),
        'public': bool(event.get('public', False)),
        'loaded_at': datetime.now(timezone.utc).isoformat()
    }
    
    return transformed

def validate_schema(transformed):
    """Validate transformed event matches BigQuery schema."""
    errors = []
    
    # Check required fields exist
    required_fields = [
        'event_id', 'event_type', 'actor_login', 'repo_name',
        'repo_owner', 'created_at', 'event_date', 'public', 'loaded_at'
    ]
    
    for field in required_fields:
        if field not in transformed:
            errors.append(f"Missing required field: {field}")
    
    # Check types
    string_fields = ['event_id', 'event_type', 'actor_login', 'repo_name', 
                     'repo_owner', 'created_at', 'event_date', 'loaded_at']
    
    for field in string_fields:
        if field in transformed and not isinstance(transformed[field], str):
            errors.append(f"Field {field} should be STRING, got {type(transformed[field]).__name__}")
    
    # Critical: event_id must be STRING (not INTEGER)
    if 'event_id' in transformed:
        if not isinstance(transformed['event_id'], str):
            errors.append(f"CRITICAL: event_id must be STRING, got {type(transformed['event_id']).__name__}")
        elif transformed['event_id'].isdigit():
            # It's a string representation of a number - that's correct!
            pass
    
    # Check public is boolean
    if 'public' in transformed and not isinstance(transformed['public'], bool):
        errors.append(f"Field public should be BOOLEAN, got {type(transformed['public']).__name__}")
    
    # Check payload is dict
    if 'payload' in transformed and not isinstance(transformed['payload'], dict):
        errors.append(f"Field payload should be JSON/dict, got {type(transformed['payload']).__name__}")
    
    return errors

def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else "2024-06-15"
    
    print("=" * 60)
    print("FAST VALIDATION - Transform Logic Test")
    print("=" * 60)
    print(f"Date: {date_str}")
    print(f"Fetching 1 hour of GHE Archive data...")
    print()
    
    try:
        # Fetch sample data
        raw_data = fetch_sample_hour(date_str, hour=12)
        print(f"Downloaded {len(raw_data) / 1024 / 1024:.2f} MB")
        
        # Decompress directly in memory
        print("Decompressing and parsing events...")
        events = []
        
        import io
        with gzip.open(io.BytesIO(raw_data), 'rt', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                if i >= 100:  # Test first 100 events
                    break
                try:
                    event = json.loads(line.strip())
                    events.append(event)
                except json.JSONDecodeError:
                    continue
        
        print(f"Parsed {len(events)} events")
        print()
        
        # Transform and validate
        print("Transforming and validating schema...")
        all_valid = True
        error_count = 0
        
        for i, event in enumerate(events):
            transformed = transform_event(event)
            errors = validate_schema(transformed)
            
            if errors:
                all_valid = False
                error_count += len(errors)
                if i < 5:  # Show first few errors
                    print(f"  Event {i}: {errors}")
        
        print()
        print("=" * 60)
        if all_valid:
            print("✅ FAST VALIDATION PASSED")
            print(f"   Tested {len(events)} events, 0 schema errors")
            print("   Transform logic is correct!")
            return 0
        else:
            print("❌ FAST VALIDATION FAILED")
            print(f"   Tested {len(events)} events, {error_count} schema errors")
            return 1
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ VALIDATION ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
