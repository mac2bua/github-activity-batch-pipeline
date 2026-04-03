# GHE Archive Data Availability Notes

## Known Patterns

### Hourly Availability Varies by Date

GHE Archive does not have complete 24-hour coverage for all dates. Availability patterns observed:

| Date | Available Hours | Notes |
|------|----------------|-------|
| 2026-03-01 | 11-23 (13 hours) | Hours 00-10 return 404 |
| 2024-01-01 | Partial | Some hours available |
| 2024-06-15 | Most hours | Good coverage for testing |
| 2023-01-01 | Most hours | Good coverage for testing |
| 2011-02-20 | All 24 hours | Historical data complete |

### Why This Happens

1. **Data Lag**: Recent dates may not have all hours processed yet
2. **Archival Gaps**: Some periods have incomplete archival
3. **Timezone Issues**: Hours may be in UTC, causing apparent gaps
4. **Source Availability**: GitHub's API may have had outages

## Recommended Test Dates

For testing the pipeline, use dates with known good coverage:

```bash
# Good dates for testing (most hours available)
2024-06-15
2023-01-01
2011-02-20

# Partial dates (some hours available, good for testing partial download handling)
2026-03-01  # Hours 11-23 only
2024-01-01  # Some hours

# Avoid: Very recent dates (may have no data yet)
```

## How to Check Data Availability

Before running the pipeline for a specific date, check availability:

```bash
# Test a few hours to see if data exists
curl -I https://data.gharchive.org/2024-06-15-00.json.gz
curl -I https://data.gharchive.org/2024-06-15-12.json.gz
curl -I https://data.gharchive.org/2024-06-15-23.json.gz

# Or use this script to check all 24 hours
for h in $(seq -w 0 23); do
  status=$(curl -s -o /dev/null -w "%{http_code}" \
    "https://data.gharchive.org/2024-06-15-${h}.json.gz")
  echo "Hour $h: $status"
done
```

## Pipeline Behavior

The pipeline handles partial data gracefully:

1. **Download task**: Succeeds with any number of files (even 1)
   - Logs which hours were successful
   - Warns if >50% failed
   - Pushes file list to XCom

2. **Upload task**: Uploads whatever was downloaded
   - Warns if no files to upload
   - Still succeeds (validate task catches empty data)

3. **Validate task**: Checks if files exist in GCS
   - Returns `valid: False` if no files found
   - Downstream tasks can handle this

4. **Load task**: Loads available files to BigQuery
   - Works with any number of files
   - Empty load is still valid (just no new data)

## Configuration

The DAG has `catchup: False` to avoid backfilling dates with missing data:

```python
DAG_CONFIG = {
    'catchup': False,  # Don't backfill missing historical data
    ...
}
```

If you want to backfill specific dates, trigger them manually with known good dates.

## Troubleshooting

### "Download complete: 0/24 files succeeded"

**Cause**: The date has no available data.

**Fix**: Try a different date:
- Use recommended test dates above
- Check availability with curl first

### "More than half of files failed to download"

**Cause**: Partial data availability (normal for some dates).

**Action**: 
- Check which hours succeeded (logged)
- If you need complete data, try a different date
- If partial data is acceptable, proceed

### BigQuery has less data than expected

**Cause**: Only available hours were loaded.

**Action**: This is expected behavior. The pipeline loads what's available.

## Data Quality Notes

- **Minimum viable**: Even 1 hour of data is useful for testing
- **Recommended**: 12+ hours for meaningful analysis
- **Ideal**: 24 hours for complete daily picture

For production use, consider:
- Running weekly instead of daily (more complete data)
- Adding a waiting period (e.g., process T-2 days)
- Monitoring data availability patterns
