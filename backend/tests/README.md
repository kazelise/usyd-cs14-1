# Tracking Module Tests

## Overview

Unit tests for the tracking module (calibration, gaze, click tracking).

## Test Files

| File | Description |
|------|-------------|
| `test_schemas_tracking.py` | Pydantic schema validation tests |
| `test_quality.py` | Calibration quality computation tests |
| `test_quality_advanced.py` | Advanced quality tests with fixtures |
| `test_schema_edge_cases.py` | Edge case and boundary value tests |
| `test_schema_types.py` | Type coercion and serialization tests |
| `test_batch_processing.py` | Batch data processing tests |
| `test_calibration_workflow.py` | Calibration workflow consistency tests |
| `test_tracking_fixtures.py` | Fixture-based gaze/click tests |
| `test_schema_interop.py` | Schema interoperability tests |

## Running Tests

```bash
cd backend
python -m pytest tests/ -v
```

## Test Output

Test results are saved in `output/test-results/` after each major update.
