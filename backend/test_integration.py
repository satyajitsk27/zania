import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import json
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from main import app, MAX_QUESTIONS, MAX_PDF_PAGES


@pytest.fixture
def client():
    """Create test client for FastAPI"""
    return TestClient(app)


@pytest.fixture
def sample_questions_simple():
    """Create simple questions JSON"""
    questions = ["What is the company?", "Who is the CEO?", "When was it founded?"]
    return BytesIO(json.dumps(questions).encode())


@pytest.fixture
def sample_questions_object():
    """Create questions in object format"""
    questions = {"questions": ["What is AI?", "What is ML?"]}
    return BytesIO(json.dumps(questions).encode())


@pytest.fixture
def sample_document_json():
    """Create sample JSON document"""
    document = {
        "company": "TestCorp Solutions",
        "ceo": "Jane Smith",
        "founded": 2020,
        "revenue": "$10M",
        "services": ["Cloud", "AI", "Security"]
    }
    return BytesIO(json.dumps(document).encode())


@pytest.fixture
def sample_pdf():
    """Create sample PDF document"""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(100, 750, "Company: TestCorp Solutions")
    c.drawString(100, 730, "CEO: Jane Smith")
    c.drawString(100, 710, "Founded: 2020")
    c.drawString(100, 690, "Revenue: $10M")
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


class TestSuccessfulRequests:
    """Test successful API requests with mocked LLM"""
    
    @patch('main.answer_questions_with_langchain')
    def test_json_document_success(self, mock_qa, client, sample_questions_simple, sample_document_json):
        """Test successful request with JSON document"""
        # Mock the Q&A function
        mock_qa.return_value = [
            {"question": "What is the company?", "answer": "TestCorp Solutions", "source": "company: TestCorp Solutions"},
            {"question": "Who is the CEO?", "answer": "Jane Smith", "source": "ceo: Jane Smith"},
            {"question": "When was it founded?", "answer": "2020", "source": "founded: 2020"}
        ]
        
        response = client.post(
            "/answer",
            files={
                "questions_file": ("questions.json", sample_questions_simple, "application/json"),
                "document_file": ("document.json", sample_document_json, "application/json")
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "qa_pairs" in data
        assert len(data["qa_pairs"]) == 3
        assert data["qa_pairs"][0]["question"] == "What is the company?"
        assert data["qa_pairs"][0]["answer"] == "TestCorp Solutions"
    
    @patch('main.answer_questions_with_langchain')
    def test_pdf_document_success(self, mock_qa, client, sample_questions_simple, sample_pdf):
        """Test successful request with PDF document"""
        mock_qa.return_value = [
            {"question": "What is the company?", "answer": "TestCorp Solutions", "source": "Company: TestCorp Solutions"},
            {"question": "Who is the CEO?", "answer": "Jane Smith", "source": "CEO: Jane Smith"},
            {"question": "When was it founded?", "answer": "2020", "source": "Founded: 2020"}
        ]
        
        response = client.post(
            "/answer",
            files={
                "questions_file": ("questions.json", sample_questions_simple, "application/json"),
                "document_file": ("document.pdf", sample_pdf, "application/pdf")
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "qa_pairs" in data
        assert len(data["qa_pairs"]) == 3
    
    @patch('main.answer_questions_with_langchain')
    def test_object_format_questions(self, mock_qa, client, sample_questions_object, sample_document_json):
        """Test with questions in object format"""
        mock_qa.return_value = [
            {"question": "What is AI?", "answer": "Artificial Intelligence", "source": ""},
            {"question": "What is ML?", "answer": "Machine Learning", "source": ""}
        ]
        
        response = client.post(
            "/answer",
            files={
                "questions_file": ("questions.json", sample_questions_object, "application/json"),
                "document_file": ("document.json", sample_document_json, "application/json")
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "qa_pairs" in data
        assert len(data["qa_pairs"]) == 2


class TestValidationErrors:
    """Test validation error handling"""
    
    def test_file_size_limit_questions(self, client, sample_document_json):
        """Test questions file exceeds size limit"""
        # Create a large file (>10MB)
        large_content = json.dumps(["Q?" for _ in range(1000000)])  # Very large
        large_file = BytesIO(large_content.encode())
        
        response = client.post(
            "/answer",
            files={
                "questions_file": ("questions.json", large_file, "application/json"),
                "document_file": ("document.json", sample_document_json, "application/json")
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "exceeds" in data["error"].lower()
    
    def test_file_size_limit_document(self, client, sample_questions_simple):
        """Test document file exceeds size limit"""
        # Create a large document
        large_doc = json.dumps({"data": "x" * (11 * 1024 * 1024)})  # >10MB
        large_file = BytesIO(large_doc.encode())
        
        response = client.post(
            "/answer",
            files={
                "questions_file": ("questions.json", sample_questions_simple, "application/json"),
                "document_file": ("document.json", large_file, "application/json")
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "exceeds" in data["error"].lower()
    
    def test_too_many_questions(self, client, sample_document_json):
        """Test exceeding question limit"""
        many_questions = [f"Question {i}?" for i in range(MAX_QUESTIONS + 5)]
        questions_file = BytesIO(json.dumps(many_questions).encode())
        
        response = client.post(
            "/answer",
            files={
                "questions_file": ("questions.json", questions_file, "application/json"),
                "document_file": ("document.json", sample_document_json, "application/json")
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "exceeds the maximum limit" in data["error"]
        assert str(MAX_QUESTIONS) in data["error"]
    
    def test_empty_questions(self, client, sample_document_json):
        """Test empty questions array"""
        empty_questions = BytesIO(json.dumps([]).encode())
        
        response = client.post(
            "/answer",
            files={
                "questions_file": ("questions.json", empty_questions, "application/json"),
                "document_file": ("document.json", sample_document_json, "application/json")
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "No questions found" in data["error"]
    
    def test_invalid_json_questions(self, client, sample_document_json):
        """Test invalid JSON in questions file"""
        invalid_json = BytesIO(b"{ invalid json syntax }")
        
        response = client.post(
            "/answer",
            files={
                "questions_file": ("questions.json", invalid_json, "application/json"),
                "document_file": ("document.json", sample_document_json, "application/json")
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "Invalid JSON" in data["error"]
    
    def test_invalid_json_document(self, client, sample_questions_simple):
        """Test invalid JSON in document file"""
        invalid_json = BytesIO(b"{ not valid json }")
        
        response = client.post(
            "/answer",
            files={
                "questions_file": ("questions.json", sample_questions_simple, "application/json"),
                "document_file": ("document.json", invalid_json, "application/json")
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data


class TestPDFHandling:
    """Test PDF-specific handling"""
    
    def test_corrupted_pdf(self, client, sample_questions_simple):
        """Test corrupted PDF file"""
        corrupted_pdf = BytesIO(b"This is not a PDF file")
        
        response = client.post(
            "/answer",
            files={
                "questions_file": ("questions.json", sample_questions_simple, "application/json"),
                "document_file": ("document.pdf", corrupted_pdf, "application/pdf")
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
    
    def test_large_pdf(self, client, sample_questions_simple):
        """Test PDF exceeding page limit"""
        # Create PDF with more than MAX_PDF_PAGES
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        for i in range(MAX_PDF_PAGES + 1):
            c.drawString(100, 750, f"Page {i+1}")
            c.showPage()
        c.save()
        buffer.seek(0)
        
        response = client.post(
            "/answer",
            files={
                "questions_file": ("questions.json", sample_questions_simple, "application/json"),
                "document_file": ("document.pdf", buffer, "application/pdf")
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "exceeds the maximum allowed limit" in data["error"]


class TestMissingParameters:
    """Test missing required parameters"""
    
    def test_missing_questions_file(self, client, sample_document_json):
        """Test missing questions file"""
        response = client.post(
            "/answer",
            files={
                "document_file": ("document.json", sample_document_json, "application/json")
            }
        )
        
        # Should return 422 for missing required field
        assert response.status_code == 422
    
    def test_missing_document_file(self, client, sample_questions_simple):
        """Test missing document file"""
        response = client.post(
            "/answer",
            files={
                "questions_file": ("questions.json", sample_questions_simple, "application/json")
            }
        )
        
        # Should return 422 for missing required field
        assert response.status_code == 422
    
    def test_missing_both_files(self, client):
        """Test missing both files"""
        response = client.post("/answer")
        
        # Should return 422 for missing required fields
        assert response.status_code == 422


class TestResponseStructure:
    """Test response structure and format"""
    
    @patch('main.answer_questions_with_langchain')
    def test_response_has_correct_structure(self, mock_qa, client, sample_questions_simple, sample_document_json):
        """Test that successful response has correct structure"""
        mock_qa.return_value = [
            {"question": "Q1?", "answer": "A1", "source": "S1"}
        ]
        
        response = client.post(
            "/answer",
            files={
                "questions_file": ("questions.json", sample_questions_simple, "application/json"),
                "document_file": ("document.json", sample_document_json, "application/json")
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "qa_pairs" in data
        assert isinstance(data["qa_pairs"], list)
        
        if len(data["qa_pairs"]) > 0:
            qa = data["qa_pairs"][0]
            assert "question" in qa
            assert "answer" in qa
            assert "source" in qa
    
    @patch('main.answer_questions_with_langchain')
    def test_response_with_empty_source(self, mock_qa, client, sample_questions_simple, sample_document_json):
        """Test response when source is empty"""
        mock_qa.return_value = [
            {"question": "Q1?", "answer": "A1", "source": ""}
        ]
        
        response = client.post(
            "/answer",
            files={
                "questions_file": ("questions.json", sample_questions_simple, "application/json"),
                "document_file": ("document.json", sample_document_json, "application/json")
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["qa_pairs"][0]["source"] == ""


class TestConcurrentRequests:
    """Test handling of concurrent requests (async behavior)"""
    
    @patch('main.answer_questions_with_langchain')
    def test_multiple_concurrent_requests(self, mock_qa, client, sample_questions_simple, sample_document_json):
        """Test that multiple requests can be handled"""
        mock_qa.return_value = [
            {"question": "Q?", "answer": "A", "source": "S"}
        ]
        
        # Make multiple requests (TestClient handles them sequentially but tests async endpoint)
        responses = []
        for i in range(3):
            sample_questions_simple.seek(0)
            sample_document_json.seek(0)
            
            response = client.post(
                "/answer",
                files={
                    "questions_file": ("questions.json", sample_questions_simple, "application/json"),
                    "document_file": ("document.json", sample_document_json, "application/json")
                }
            )
            responses.append(response)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
            assert "qa_pairs" in response.json()


class TestEdgeCases:
    """Test edge cases in integration"""
    
    @patch('main.answer_questions_with_langchain')
    def test_special_characters_in_files(self, mock_qa, client, sample_document_json):
        """Test handling of special characters"""
        questions = ["What is $price?", "Who handles support@example.com?", "Is 50% discount available?"]
        questions_file = BytesIO(json.dumps(questions).encode())
        
        mock_qa.return_value = [
            {"question": q, "answer": "Answer", "source": ""} for q in questions
        ]
        
        response = client.post(
            "/answer",
            files={
                "questions_file": ("questions.json", questions_file, "application/json"),
                "document_file": ("document.json", sample_document_json, "application/json")
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["qa_pairs"]) == 3
    
    @patch('main.answer_questions_with_langchain')
    def test_unicode_in_files(self, mock_qa, client, sample_document_json):
        """Test handling of unicode characters"""
        questions = ["¿Qué es esto?", "什么是这个?"]
        questions_file = BytesIO(json.dumps(questions, ensure_ascii=False).encode('utf-8'))
        
        mock_qa.return_value = [
            {"question": q, "answer": "Answer", "source": ""} for q in questions
        ]
        
        response = client.post(
            "/answer",
            files={
                "questions_file": ("questions.json", questions_file, "application/json"),
                "document_file": ("document.json", sample_document_json, "application/json")
            }
        )
        
        assert response.status_code == 200


class TestErrorRecovery:
    """Test error recovery and graceful failure"""
    
    @patch('main.answer_questions_with_langchain')
    def test_partial_failure_in_qa(self, mock_qa, client, sample_questions_simple, sample_document_json):
        """Test that partial failures in Q&A are handled"""
        # Mock some questions succeeding and some failing
        mock_qa.return_value = [
            {"question": "Q1?", "answer": "Success", "source": ""},
            {"question": "Q2?", "answer": "Error processing question", "source": ""},
            {"question": "Q3?", "answer": "Success", "source": ""}
        ]
        
        response = client.post(
            "/answer",
            files={
                "questions_file": ("questions.json", sample_questions_simple, "application/json"),
                "document_file": ("document.json", sample_document_json, "application/json")
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        # All questions should have responses (even errors)
        assert len(data["qa_pairs"]) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
