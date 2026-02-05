# Testing Guide

## Setup
```bash
cd backend
source venv/bin/activate
pip install pytest reportlab
```

## Run Tests

### All Tests
```bash
pytest test_core_logic.py test_integration.py -v
```

### Unit Tests Only
```bash
pytest test_core_logic.py -v
```

### Integration Tests Only
```bash
pytest test_integration.py -v
```

## What Gets Tested

**Unit Tests (test_core_logic.py):**
- PDF extraction and validation
- Question parsing (all formats)
- Document loading
- File size and page limits
- Special characters and unicode
- Edge cases

**Integration Tests (test_integration.py):**
- API endpoint behavior
- File uploads
- Error handling
- Response structure
- Concurrent requests

## Notes

- **No backend needed** - tests run independently
- **No API costs** - LLM calls are mocked
- Tests use data from `test_data/` folder
- All tests should pass 
