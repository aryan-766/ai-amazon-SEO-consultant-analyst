# Amazon SEO Copilot 🚀

**Amazon SEO Copilot** is a complete, production-ready AI SaaS application built to help e-commerce brands analyze Amazon competitor keyword datasets, discover high-traffic opportunities, optimize listings dynamically, generate styled reports, and converse directly with their data using local RAG (Retrieval-Augmented Generation) intelligence.

---

## 🛠️ Tech Stack

### Frontend
- **Framework**: React / Next.js (App Router, TypeScript)
- **Styling**: Tailwind CSS (v4), Custom Glassmorphic Panels
- **State Management**: Zustand
- **Data Fetching**: TanStack React Query
- **Charts**: Recharts (Interactive Intent, Buyer Journey, and Share of Voice models)

### Backend
- **Framework**: FastAPI (Python)
- **Database**: SQLite (SQLAlchemy ORM)
- **Data Engineering**: Pandas, NumPy, Scikit-Learn (K-Means Clustering)
- **Reporting**: ReportLab (Styled PDF builder), OpenPyXL (Styled Excel workbook exporter)

### Local AI Integration
- **Semantic Retrieval**: Sentence Transformers (`BAAI/bge-small-en-v1.5`)
- **Generative Copywriting & RAG**: Ollama (`qwen2.5:7b` Instruct Model)

---

## 🏗️ Architecture & Core Services

The application follows a **Clean Architecture** model, decoupling API endpoints, domain models, database access, and specialized services:

1. **Excel Ingestion Service (`excel.py`)**: Automatically matches columns from Helium 10/Semrush, extracts competitor ranking headers, and validates dataset health.
2. **Data Cleaning Service (`cleaning.py`)**: Dedups keywords based on volume, normalizes spelling and casing, and imputes null values.
3. **Feature Engineering Service (`features.py`)**: Classifies search intents (Commercial, Transactional, Informational, Navigational), maps buyer journey stages, and performs K-Means clustering on BGE semantic embeddings.
4. **Scoring Engine (`scoring.py`)**: Vectorized calculations of 10 strategic scores (0-100) including Opportunity, Competition, Trend, Revenue, and Gap scores.
5. **Listing Optimizer (`listing.py`)**: Compares product titles, descriptions, bullets, and backend terms against top keywords in real-time, displaying a dynamic gauge dial.
6. **Copilot Chat (`copilot.py`)**: Performs semantic RAG over the active dataset to answer questions strictly using uploaded facts, avoiding hallucinations.
7. **Reports Service (`reports.py`)**: Builds styled spreadsheets and executive PDF briefings.

---

## 🚀 Setup Guide

### 1. Prerequisites
- Python 3.10 or higher
- Node.js 18 or higher
- [Ollama](https://ollama.com/) (installed and running locally)

### 2. Ollama Configuration
Ensure Ollama is running, then pull the required model:
```bash
ollama pull qwen2.5:7b
```

### 3. Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the FastAPI development server:
   ```bash
   python -m uvicorn app.main:app --reload --port 8000
   ```
The API will run at `http://localhost:8000`. Swagger documentation is available at `http://localhost:8000/docs`.

### 4. Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd ../frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Start the Next.js development server:
   ```bash
   npm run dev
   ```
The app will run at `http://localhost:3000`.

---

## 📝 Folder Structure

```
├── backend/
│   ├── app/
│   │   ├── api/             # API routes (upload, analyze, chat, listing, export)
│   │   ├── core/            # Config settings and DB connections
│   │   ├── models/          # SQLAlchemy Database Schemas
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # cleaning, features, scoring, listing, copilot, reports
│   │   └── main.py          # FastAPI application entrypoint
│   └── requirements.txt     # Python backend dependencies
├── frontend/
│   ├── src/
│   │   ├── app/             # Next.js pages, layouts, global styles
│   │   ├── store/           # Zustand app state hook
│   │   └── lib/             # Axios REST client integration
│   ├── tailwind.config.ts
│   └── tsconfig.json
└── README.md
```
