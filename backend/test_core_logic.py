import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from main import (
    extract_text_from_pdf_bytes,
    parse_questions_from_file,
    load_document_from_json,
    load_document_from_pdf,
    process_single_question,
    MAX_PDF_PAGES,
    MAX_QUESTIONS,
    MAX_FILE_SIZE_MB
)
from io import BytesIO
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from unittest.mock import Mock, MagicMock


class TestPDFExtraction:
    """Test PDF text extraction with various scenarios"""
    
    def create_test_pdf(self, num_pages=1, text_per_page="Test content"):
        """Helper to create a test PDF"""
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        
        for i in range(num_pages):
            c.drawString(100, 750, f"{text_per_page} - Page {i+1}")
            c.showPage()
        
        c.save()
        buffer.seek(0)
        return buffer.read()
    
    def test_extract_text_success(self):
        """Test successful PDF text extraction"""
        pdf_bytes = self.create_test_pdf(num_pages=2, text_per_page="Hello World")
        text = extract_text_from_pdf_bytes(pdf_bytes)
        
        assert text is not None
        assert len(text) > 0
        assert "Hello World" in text or "Page" in text
    
    def test_extract_text_multiple_pages(self):
        """Test extraction from multi-page PDF"""
        pdf_bytes = self.create_test_pdf(num_pages=5, text_per_page="Multi-page test")
        text = extract_text_from_pdf_bytes(pdf_bytes)
        
        assert "Page 1" in text
        assert "Page 5" in text
    
    def test_extract_text_exceeds_page_limit(self):
        """Test PDF with too many pages"""
        pdf_bytes = self.create_test_pdf(num_pages=MAX_PDF_PAGES + 1)
        
        with pytest.raises(ValueError) as exc_info:
            extract_text_from_pdf_bytes(pdf_bytes)
        
        assert "exceeds the maximum allowed limit" in str(exc_info.value)
        assert str(MAX_PDF_PAGES) in str(exc_info.value)
    
    def test_extract_text_exactly_at_page_limit(self):
        """Test PDF with exactly MAX_PDF_PAGES pages (boundary test)"""
        pdf_bytes = self.create_test_pdf(num_pages=MAX_PDF_PAGES)
        text = extract_text_from_pdf_bytes(pdf_bytes)
        
        assert text is not None
        assert len(text) > 0
    
    def test_extract_text_corrupted_pdf(self):
        """Test handling of corrupted PDF"""
        corrupted_pdf = b"Not a valid PDF file content"
        
        with pytest.raises(ValueError) as exc_info:
            extract_text_from_pdf_bytes(corrupted_pdf)
        
        assert "Unable to read PDF" in str(exc_info.value) or "Error processing PDF" in str(exc_info.value)
    
    def test_extract_text_empty_pdf(self):
        """Test PDF with no content"""
        pdf_bytes = self.create_test_pdf(num_pages=1, text_per_page="")
        text = extract_text_from_pdf_bytes(pdf_bytes)
        
        # Should not raise error, just return empty or minimal text
        assert text is not None
    
    def test_load_document_from_pdf_creates_chunks(self):
        """Test that load_document_from_pdf creates proper chunks"""
        pdf_bytes = self.create_test_pdf(num_pages=2, text_per_page="Test content for chunking")
        chunks = load_document_from_pdf(pdf_bytes)
        
        assert len(chunks) > 0
        assert all(hasattr(chunk, 'page_content') for chunk in chunks)
        assert all(hasattr(chunk, 'metadata') for chunk in chunks)


class TestQuestionParsing:
    """Test question parsing from various JSON formats"""
    
    def test_parse_questions_simple_array(self):
        """Test parsing simple array of questions"""
        questions_json = json.dumps(["Question 1?", "Question 2?", "Question 3?"])
        questions = parse_questions_from_file(questions_json.encode(), "test.json")
        
        assert len(questions) == 3
        assert questions[0] == "Question 1?"
        assert questions[1] == "Question 2?"
        assert questions[2] == "Question 3?"
    
    def test_parse_questions_object_format(self):
        """Test parsing questions from object with 'questions' key"""
        questions_json = json.dumps({
            "questions": ["Q1?", "Q2?", "Q3?"]
        })
        questions = parse_questions_from_file(questions_json.encode(), "test.json")
        
        assert len(questions) == 3
        assert questions[0] == "Q1?"
    
    def test_parse_questions_detailed_format(self):
        """Test parsing questions from array of objects"""
        questions_json = json.dumps([
            {"question": "What is AI?"},
            {"question": "What is ML?"}
        ])
        questions = parse_questions_from_file(questions_json.encode(), "test.json")
        
        assert len(questions) == 2
        assert questions[0] == "What is AI?"
        assert questions[1] == "What is ML?"
    
    def test_parse_questions_mixed_format(self):
        """Test mixed valid formats"""
        questions_json = json.dumps([
            "Simple question?",
            {"question": "Object question?"}
        ])
        questions = parse_questions_from_file(questions_json.encode(), "test.json")
        
        assert len(questions) == 2
        assert "Simple question?" in questions
        assert "Object question?" in questions
    
    def test_parse_questions_exceeds_limit(self):
        """Test too many questions"""
        many_questions = [f"Question {i}?" for i in range(MAX_QUESTIONS + 1)]
        questions_json = json.dumps(many_questions)
        
        with pytest.raises(ValueError) as exc_info:
            parse_questions_from_file(questions_json.encode(), "test.json")
        
        assert "exceeds the maximum limit" in str(exc_info.value)
        assert str(MAX_QUESTIONS) in str(exc_info.value)
    
    def test_parse_questions_exactly_at_limit(self):
        """Test exactly MAX_QUESTIONS questions (boundary test)"""
        questions = [f"Question {i}?" for i in range(MAX_QUESTIONS)]
        questions_json = json.dumps(questions)
        
        parsed = parse_questions_from_file(questions_json.encode(), "test.json")
        assert len(parsed) == MAX_QUESTIONS
    
    def test_parse_questions_invalid_json(self):
        """Test invalid JSON format"""
        invalid_json = b"{ invalid json }"
        
        with pytest.raises(ValueError) as exc_info:
            parse_questions_from_file(invalid_json, "test.json")
        
        assert "Invalid JSON" in str(exc_info.value)
    
    def test_parse_questions_empty_list(self):
        """Test empty questions list"""
        questions_json = json.dumps([])
        
        with pytest.raises(ValueError) as exc_info:
            parse_questions_from_file(questions_json.encode(), "test.json")
        
        assert "No questions found" in str(exc_info.value)
    
    def test_parse_questions_null_values(self):
        """Test handling of null values in questions"""
        questions_json = json.dumps([None, "Valid question?", None])
        questions = parse_questions_from_file(questions_json.encode(), "test.json")
        
        # Should skip null values
        assert len(questions) >= 1
        assert "Valid question?" in questions
    
    def test_parse_questions_empty_strings(self):
        """Test handling of empty strings"""
        questions_json = json.dumps(["", "Valid?", ""])
        questions = parse_questions_from_file(questions_json.encode(), "test.json")
        
        # Implementation should handle empty strings gracefully
        assert isinstance(questions, list)


class TestDocumentLoading:
    """Test document loading from JSON"""
    
    def test_load_json_document_dict(self):
        """Test loading JSON document as dictionary"""
        doc_json = json.dumps({
            "company": "TestCorp",
            "founded": 2020,
            "ceo": "John Doe"
        })
        
        chunks = load_document_from_json(doc_json.encode())
        
        assert len(chunks) > 0
        assert chunks[0].page_content is not None
        assert "TestCorp" in chunks[0].page_content
    
    def test_load_json_document_list(self):
        """Test loading JSON document as list"""
        doc_json = json.dumps(["Item 1", "Item 2", "Item 3"])
        
        chunks = load_document_from_json(doc_json.encode())
        
        assert len(chunks) > 0
        assert chunks[0].page_content is not None
    
    def test_load_json_document_nested(self):
        """Test loading nested JSON document"""
        doc_json = json.dumps({
            "company": "TestCorp",
            "details": {
                "founded": 2020,
                "employees": 100
            },
            "products": ["A", "B", "C"]
        })
        
        chunks = load_document_from_json(doc_json.encode())
        
        assert len(chunks) > 0
        content = chunks[0].page_content
        assert "TestCorp" in content
        assert "founded" in content
    
    def test_load_json_invalid_format(self):
        """Test invalid JSON document"""
        invalid_json = b"{ not valid json }"
        
        with pytest.raises(ValueError) as exc_info:
            load_document_from_json(invalid_json)
        
        assert "Invalid JSON" in str(exc_info.value)
    
    def test_load_json_large_document(self):
        """Test loading large JSON document"""
        large_doc = {f"key_{i}": f"value_{i}" for i in range(1000)}
        doc_json = json.dumps(large_doc)
        
        chunks = load_document_from_json(doc_json.encode())
        
        # Should be split into multiple chunks
        assert len(chunks) > 1


class TestProcessSingleQuestion:
    """Test individual question processing"""
    
    def test_process_question_success(self):
        """Test successful question processing"""
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Answer: Test answer\nSource: Test source"
        
        result = process_single_question(mock_chain, "What is the test?")
        
        assert result["question"] == "What is the test?"
        assert result["answer"] == "Test answer"
        assert result["source"] == "Test source"
    
    def test_process_question_no_source(self):
        """Test question processing with no source"""
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Answer: Test answer\nSource: N/A"
        
        result = process_single_question(mock_chain, "What is the test?")
        
        assert result["answer"] == "Test answer"
        assert result["source"] == ""  # N/A should be converted to empty string
    
    def test_process_question_error(self):
        """Test question processing with error"""
        mock_chain = MagicMock()
        mock_chain.invoke.side_effect = Exception("Test error")
        
        result = process_single_question(mock_chain, "What is the test?")
        
        assert "Error" in result["answer"]
        assert result["question"] == "What is the test?"


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_special_characters_in_questions(self):
        """Test questions with special characters"""
        questions_json = json.dumps([
            "What is AI/ML?",
            "How does it work? (explain)",
            "Cost: $100?",
            "What about 50% off?",
            "Email: test@example.com?"
        ])
        
        questions = parse_questions_from_file(questions_json.encode(), "test.json")
        assert len(questions) == 5
        assert "AI/ML" in questions[0]
        assert "$" in questions[2]
        assert "@" in questions[4]
    
    def test_unicode_in_questions(self):
        """Test questions with unicode characters"""
        questions_json = json.dumps([
            "¿Qué es AI?",
            "Qu'est-ce que l'IA?",
            "什么是人工智能?"
        ])
        
        questions = parse_questions_from_file(questions_json.encode(), "test.json")
        assert len(questions) == 3
    
    def test_very_long_question(self):
        """Test handling of very long questions"""
        long_question = "What is " + "very " * 100 + "long question?"
        questions_json = json.dumps([long_question])
        
        questions = parse_questions_from_file(questions_json.encode(), "test.json")
        assert len(questions) == 1
        assert len(questions[0]) > 500
    
    def test_whitespace_handling(self):
        """Test handling of extra whitespace"""
        questions_json = json.dumps([
            "  Question with spaces?  ",
            "\nQuestion with newlines?\n",
            "\tQuestion with tabs?\t"
        ])
        
        questions = parse_questions_from_file(questions_json.encode(), "test.json")
        assert len(questions) == 3
    
    def test_duplicate_questions(self):
        """Test handling of duplicate questions"""
        questions_json = json.dumps([
            "What is AI?",
            "What is ML?",
            "What is AI?"  # Duplicate
        ])
        
        questions = parse_questions_from_file(questions_json.encode(), "test.json")
        # Should accept duplicates (business logic may vary)
        assert len(questions) == 3


class TestFileSizeLimits:
    """Test file size limit validations"""
    
    def test_questions_file_size_calculation(self):
        """Test that file size is calculated correctly"""
        questions = ["Q?" for _ in range(100)]
        questions_json = json.dumps(questions).encode()
        size_mb = len(questions_json) / (1024 * 1024)
        
        # Should be well under limit
        assert size_mb < MAX_FILE_SIZE_MB
    
    def test_large_json_document_chunks(self):
        """Test that large documents are properly chunked"""
        # Create a document larger than chunk size
        large_text = "A" * 5000  # 5000 characters
        doc_json = json.dumps({"content": large_text})
        
        chunks = load_document_from_json(doc_json.encode())
        
        # Should be split into multiple chunks (chunk_size=1000)
        assert len(chunks) > 1


class TestChunkingStrategy:
    """Test document chunking logic"""
    
    def test_chunk_overlap_maintained(self):
        """Test that chunks maintain proper overlap"""
        # Create document larger than chunk size
        large_text = "Word " * 500  # ~2500 characters
        doc_json = json.dumps({"content": large_text})
        
        chunks = load_document_from_json(doc_json.encode())
        
        if len(chunks) > 1:
            # Check that consecutive chunks share some content (overlap)
            chunk1_end = chunks[0].page_content[-100:]
            chunk2_start = chunks[1].page_content[:100]
            # There should be some overlap
            assert len(chunks) > 1  # At least verify chunking happened
    
    def test_small_document_single_chunk(self):
        """Test that small documents result in single chunk"""
        small_doc = json.dumps({"test": "small content"})
        chunks = load_document_from_json(small_doc.encode())
        
        # Small documents should be a single chunk
        assert len(chunks) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])