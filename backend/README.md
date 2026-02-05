# Test Data Files

This directory contains various test data files for manual and automated testing.

## Questions Files

### Valid Questions
- **questions_simple.json** - Simple array format with 5 questions about company
- **questions_object.json** - Object format with "questions" key (4 questions)
- **questions_detailed.json** - Array of objects with "question" key (3 questions)
- **questions_special_chars.json** - Questions with special characters ($, /, &, etc.)

### Edge Cases
- **questions_empty.json** - Empty array (should trigger validation error)
- **questions_invalid.json** - Invalid JSON syntax (should trigger parse error)
- **questions_too_many.json** - 25 questions (exceeds MAX_QUESTIONS=20, should trigger limit error)

## Document Files

### Valid Documents
- **document_company.json** - Comprehensive company information (TechCorp Solutions)
  - Company details, services, team structure, awards, products
  - Best paired with: questions_simple.json, questions_object.json

- **document_technical.json** - Technical product specification (CloudPro Platform)
  - System requirements, features, API details, pricing
  - Best paired with: questions_special_chars.json

- **document_sample.pdf** - PDF version of company overview
  - Single page with key company information
  - Best paired with: questions_simple.json

### Edge Cases
- **document_large.pdf** - 60-page PDF (exceeds MAX_PDF_PAGES=50, should trigger limit error)

## Usage Examples

### Valid Request (Success)
```bash
curl -X POST http://localhost:3000/answer \
  -F "questions_file=@test_data/questions_simple.json" \
  -F "document_file=@test_data/document_company.json"
```

### Too Many Questions (Validation Error)
```bash
curl -X POST http://localhost:3000/answer \
  -F "questions_file=@test_data/questions_too_many.json" \
  -F "document_file=@test_data/document_company.json"
```

### Large PDF (Validation Error)
```bash
curl -X POST http://localhost:3000/answer \
  -F "questions_file=@test_data/questions_simple.json" \
  -F "document_file=@test_data/document_large.pdf"
```

### Invalid JSON (Parse Error)
```bash
curl -X POST http://localhost:3000/answer \
  -F "questions_file=@test_data/questions_invalid.json" \
  -F "document_file=@test_data/document_company.json"
```

### Empty Questions (Validation Error)
```bash
curl -X POST http://localhost:3000/answer \
  -F "questions_file=@test_data/questions_empty.json" \
  -F "document_file=@test_data/document_company.json"
```

## Using in Frontend

Upload these files through the web interface at http://localhost:5173:

1. **Success Test**: 
   - Questions: questions_simple.json
   - Document: document_company.json
   - Expected: 5 Q&A pairs with answers grounded in document

2. **Different Format Test**:
   - Questions: questions_object.json
   - Document: document_company.json
   - Expected: 4 Q&A pairs

3. **PDF Test**:
   - Questions: questions_simple.json
   - Document: document_sample.pdf
   - Expected: 5 Q&A pairs extracted from PDF

4. **Error Test - Too Many Questions**:
   - Questions: questions_too_many.json
   - Document: document_company.json
   - Expected: Error message about exceeding limit

5. **Error Test - Large PDF**:
   - Questions: questions_simple.json
   - Document: document_large.pdf
   - Expected: Error message about exceeding page limit

## File Sizes
- All JSON files: < 5 KB
- document_sample.pdf: ~10 KB
- document_large.pdf: ~50 KB (60 pages)

## Expected Behavior Summary

| Test Case | Expected Result |
|-----------|----------------|
| questions_simple.json + document_company.json | ✅ 5 Q&A pairs |
| questions_object.json + document_company.json | ✅ 4 Q&A pairs |
| questions_detailed.json + document_company.json | ✅ 3 Q&A pairs |
| questions_special_chars.json + document_technical.json | ✅ 4 Q&A pairs |
| questions_simple.json + document_sample.pdf | ✅ 5 Q&A pairs |
| questions_too_many.json + any document | ❌ Error: Exceeds 20 question limit |
| questions_empty.json + any document | ❌ Error: No questions found |
| questions_invalid.json + any document | ❌ Error: Invalid JSON |
| any questions + document_large.pdf | ❌ Error: Exceeds 50 page limit |
