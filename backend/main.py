from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import os
from openai import OpenAI
import PyPDF2
from io import BytesIO
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import hashlib
from typing import List

# LangChain imports
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import tempfile

app = FastAPI()

# Configuration limits
MAX_FILE_SIZE_MB = 10  # 10 MB limit
MAX_PDF_PAGES = 50  # Maximum 50 pages
MAX_QUESTIONS = 20  # Maximum 20 questions per request
OPENAI_TIMEOUT_SECONDS = 60  # 60 second timeout for OpenAI API
TOKENS = 200000

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize LangChain components
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, timeout=OPENAI_TIMEOUT_SECONDS)
embeddings = OpenAIEmbeddings()

def extract_text_from_pdf_bytes(pdf_bytes):
    """Extract text from PDF bytes with page limit check"""
    try:
        pdf_file = BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        num_pages = len(pdf_reader.pages)
        
        if num_pages > MAX_PDF_PAGES:
            raise ValueError(
                f"PDF has {num_pages} pages, which exceeds the maximum allowed limit of {MAX_PDF_PAGES} pages. "
                f"Please upload a smaller PDF or split it into multiple files."
            )
        
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        
        if len(text) > TOKENS:
            raise ValueError(
                f"Extracted text is too large ({len(text)} characters). "
                f"Please upload a smaller PDF with less content."
            )
        
        return text
    except PyPDF2.errors.PdfReadError:
        raise ValueError("Unable to read PDF file. The file may be corrupted or encrypted.")
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Error processing PDF: {str(e)}")

def load_document_from_pdf(pdf_bytes):
    """Load and process PDF document using LangChain"""
    text = extract_text_from_pdf_bytes(pdf_bytes)
    
    # Create a Document object
    doc = Document(page_content=text, metadata={"source": "uploaded_pdf"})
    
    # Split text into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_documents([doc])
    
    return chunks

def load_document_from_json(json_bytes):
    """Load JSON document and convert to LangChain format"""
    try:
        json_data = json.loads(json_bytes)
        
        # Convert JSON to text
        if isinstance(json_data, dict):
            text = json.dumps(json_data, indent=2)
        elif isinstance(json_data, list):
            text = json.dumps(json_data, indent=2)
        else:
            text = str(json_data)
        
        # Create Document
        doc = Document(page_content=text, metadata={"source": "uploaded_json"})
        
        # Split if needed
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = text_splitter.split_documents([doc])
        
        return chunks
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format in document file.")

def parse_questions_from_file(questions_bytes, filename):
    """Parse questions from JSON file"""
    try:
        questions_data = json.loads(questions_bytes)
        
        questions = []
        
        # Handle different JSON formats
        if isinstance(questions_data, list):
            for item in questions_data:
                if isinstance(item, str):
                    questions.append(item)
                elif isinstance(item, dict) and 'question' in item:
                    questions.append(item['question'])
        elif isinstance(questions_data, dict):
            if 'questions' in questions_data:
                for q in questions_data['questions']:
                    if isinstance(q, str):
                        questions.append(q)
                    elif isinstance(q, dict) and 'question' in q:
                        questions.append(q['question'])
        
        if not questions:
            raise ValueError("No questions found in the questions file. Please ensure your JSON contains questions.")
        
        if len(questions) > MAX_QUESTIONS:
            raise ValueError(
                f"You submitted {len(questions)} questions, which exceeds the maximum limit of {MAX_QUESTIONS}. "
                f"Please reduce the number of questions."
            )
        
        return questions
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format in questions file.")

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List

def answer_questions_with_langchain(questions, document_chunks):
    """Use LangChain RAG to answer questions based on document with concurrent execution"""
    try:
        # Create vector store from document chunks (one-time operation)
        vectorstore = FAISS.from_documents(document_chunks, embeddings)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        
        # Create prompt template using ChatPromptTemplate
        template = """Use the following pieces of context to answer the question at the end. 
If you cannot find the answer in the context, respond with "Answer not found in document".
Always include a relevant quote from the context as your source if the answer is found.

Context: {context}

Question: {question}

Provide your answer in the following format:
Answer: [Your answer here]
Source: [Relevant quote from the document]

If the answer is not in the document, respond with:
Answer: Answer not found in document
Source: N/A
"""
        
        prompt = ChatPromptTemplate.from_template(template)
        
        # Create the chain using LCEL
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)
        
        chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )
        
        # Process questions in batches for efficiency
        BATCH_SIZE = 5  # Process 5 questions at a time
        qa_pairs = []
        
        # Use ThreadPoolExecutor for concurrent LLM calls
        with ThreadPoolExecutor(max_workers=3) as executor:
            for i in range(0, len(questions), BATCH_SIZE):
                batch = questions[i:i + BATCH_SIZE]
                
                # Submit all questions in batch concurrently
                future_to_question = {
                    executor.submit(process_single_question, chain, q): q 
                    for q in batch
                }
                
                # Collect results as they complete
                for future in future_to_question:
                    question = future_to_question[future]
                    try:
                        result = future.result()
                        qa_pairs.append(result)
                    except Exception as e:
                        qa_pairs.append({
                            "question": question,
                            "answer": f"Error processing question: {str(e)}",
                            "source": ""
                        })
        
        return qa_pairs
        
    except Exception as e:
        raise ValueError(f"Error during question answering: {str(e)}")


def process_single_question(chain, question: str) -> dict:
    """Process a single question through the chain"""
    try:
        result = chain.invoke(question)
        
        # Parse answer and source from response
        answer = result
        source = ""
        
        if "Answer:" in result and "Source:" in result:
            parts = result.split("Source:")
            answer = parts[0].replace("Answer:", "").strip()
            source = parts[1].strip() if len(parts) > 1 else ""
        
        return {
            "question": question,
            "answer": answer,
            "source": source if source and source != "N/A" else ""
        }
    except Exception as e:
        return {
            "question": question,
            "answer": f"Error: {str(e)}",
            "source": ""
        }

# Cache for vector stores to avoid recomputation
from functools import lru_cache
import hashlib

@lru_cache(maxsize=10)
def get_cached_vectorstore(document_hash: str, document_chunks_tuple):
    """Cache vector store creation to avoid recomputing embeddings"""
    # Convert tuple back to list for processing
    chunks = list(document_chunks_tuple)
    return FAISS.from_documents(chunks, embeddings)


@app.post("/answer")
async def answer(questions_file: UploadFile = File(...), document_file: UploadFile = File(...)):
    """
    Main endpoint that accepts:
    - questions_file: JSON file with list of questions
    - document_file: PDF or JSON file containing the document to query
    
    Uses async/await for non-blocking I/O and concurrent question processing
    """
    try:
        # Read files asynchronously and concurrently
        questions_bytes, document_bytes = await asyncio.gather(
            questions_file.read(),
            document_file.read()
        )
        
        # Check file sizes
        questions_size_mb = len(questions_bytes) / (1024 * 1024)
        document_size_mb = len(document_bytes) / (1024 * 1024)
        
        if questions_size_mb > MAX_FILE_SIZE_MB:
            return {"error": f"Questions file size ({questions_size_mb:.2f} MB) exceeds maximum of {MAX_FILE_SIZE_MB} MB"}
        
        if document_size_mb > MAX_FILE_SIZE_MB:
            return {"error": f"Document file size ({document_size_mb:.2f} MB) exceeds maximum of {MAX_FILE_SIZE_MB} MB"}
        
        print(f"Processing questions file: {questions_file.filename}")
        print(f"Processing document file: {document_file.filename}")
        
        # Parse questions
        try:
            questions = parse_questions_from_file(questions_bytes, questions_file.filename)
            print(f"Found {len(questions)} questions")
        except ValueError as e:
            return {"error": str(e)}
        
        # Load document based on file type (run in thread pool to avoid blocking)
        try:
            loop = asyncio.get_event_loop()
            
            if document_file.filename.endswith('.pdf') or document_file.content_type == 'application/pdf':
                print("Loading PDF document...")
                document_chunks = await loop.run_in_executor(
                    None, 
                    load_document_from_pdf, 
                    document_bytes
                )
            else:
                print("Loading JSON document...")
                document_chunks = await loop.run_in_executor(
                    None,
                    load_document_from_json,
                    document_bytes
                )
            
            print(f"Document split into {len(document_chunks)} chunks")
        except ValueError as e:
            return {"error": str(e)}
        
        # Answer questions using LangChain RAG (run in thread pool)
        try:
            qa_pairs = await loop.run_in_executor(
                None,
                answer_questions_with_langchain,
                questions,
                document_chunks
            )
            print(f"Generated {len(qa_pairs)} Q&A pairs")
            return {"qa_pairs": qa_pairs}
        except ValueError as e:
            return {"error": str(e)}
        
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)