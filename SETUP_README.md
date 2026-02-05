# Quick Setup & Run Guide

## Video Link
https://drive.google.com/file/d/1ihlmQHWJFujRP3A9jR886Bh6dJzaNuSZ/view?usp=sharing

## Backend Setup

### 1. Install Dependencies
```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 2. Run Backend
```bash
python3 main.py
```

Backend runs at: `http://localhost:3000`

---

## Frontend Setup

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Run Frontend
```bash
npm run dev
```

Frontend runs at: `http://localhost:5173`

---

## Usage

1. Open browser to `http://localhost:5173`
2. Upload questions file (JSON)
3. Upload document file (PDF or JSON)
4. Click "Get Answers"
5. View results with citations

---

## Test Files

Use sample files from `backend/test_data/`:

**Questions:**
- `questions_simple.json` - 5 questions
- `questions_object.json` - 4 questions

**Documents:**
- `document_company.json` - Company info
- `document_sample.pdf` - PDF sample

**Example:**
```
Questions: test_data/questions_simple.json
Document: test_data/document_company.json
```

---

## Troubleshooting

**Backend won't start:**
- Check Python version: `python3 --version` (need 3.12)
- Reinstall: `pip install -r requirements.txt`

**Frontend won't start:**
- Delete node_modules: `rm -rf node_modules`
- Reinstall: `npm install`

**CORS errors:**
- Make sure backend is running first
- Check backend URL in `App.jsx` (should be `http://localhost:3000`)

**"Connection refused":**
- Backend must be running: `python3 main.py`
- Check correct port (backend: 3000, frontend: 5173)
