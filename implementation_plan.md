# Implementation Plan: Amazon SEO Copilot

We are building a production-ready AI SaaS application named **Amazon SEO Copilot** designed to parse Amazon keyword datasets (from exports like Helium10/Semrush/DataDive), run advanced feature engineering, score keywords, analyze competitor metrics, optimize listings dynamically, generate executive reports (Excel/PDF), and provide a local RAG-based AI Copilot using Ollama (Qwen2.5 7B) and Sentence Transformers.

---

## Technical Stack & Architecture

### Backend: FastAPI + SQLAlchemy + SQLite
The backend is structured around Clean Architecture principles, ensuring decoupling between Web APIs, Business Logic, and Data Access layers.
- **FastAPI**: REST API layer with validation via Pydantic.
- **SQLAlchemy (SQLite)**: Relational database to persist keyword uploads, analysis sessions, generated listings, reports, and AI chat histories.
- **Pandas & NumPy & Scikit-Learn**: Core libraries for dataset processing, data cleaning, feature engineering, clustering (K-Means), and scoring calculations.
- **Sentence Transformers & BGE Embeddings**: Running locally (`BAAI/bge-small-en-v1.5`) to create embedding matrices for keyword clustering and semantic search in AI Chat.
- **Ollama (Qwen2.5 7B)**: Handles generative tasks (listing writing, chat, reasoning over tables).
- **ReportLab & OpenPyXL**: Libraries for styled PDF exports and styled Excel exports.

### Frontend: Next.js (TypeScript) + TailwindCSS + shadcn/ui + React Query + Zustand + Recharts
The frontend follows a premium, dark-mode-first dashboard theme.
- **Next.js (App Router)**: Fast rendering, SEO optimization, modular page components.
- **Zustand**: State management for active sessions, active datasets, and app preferences.
- **React Query**: Server-state synchronization, pagination caching, and background sync.
- **shadcn/ui & Tailwind CSS**: Modern custom-tailored glassmorphic UI components, custom gradients, and transitions.
- **Recharts**: High-performance interactive charts for traffic, intent distribution, buyer stages, competitor overlaps, and trends.

---

## Directory Structure

```
ai-seo-copilot/
├── backend/
│   ├── app/
│   │   ├── api/                   # FastAPI endpoints (upload, analyze, chat, etc.)
│   │   ├── core/                  # Configuration, DB connection, logging, security
│   │   ├── models/                # SQLAlchemy Models (DB Schemas)
│   │   ├── schemas/               # Pydantic Schemas (Request/Response validation)
│   │   ├── services/              # Core business services
│   │   │   ├── cleaning.py        # Keyword normalization & validation
│   │   │   ├── features.py        # NLP & feature extraction, intent, clusters
│   │   │   ├── competitor.py      # Overlap analysis, gap finder, leaders
│   │   │   ├── scoring.py         # 10-score engine (Opportunity, SEO, etc.)
│   │   │   ├── listing.py         # Listing Optimizer & Dynamic check
│   │   │   ├── copilot.py         # Ollama + RAG semantic search & reasoning
│   │   │   ├── reports.py         # PDF and Excel report builders
│   │   │   └── excel.py           # Ingestion and openpyxl helpers
│   │   ├── utils/                 # General helpers (clustering, PDF styling)
│   │   └── main.py                # FastAPI entry point
│   ├── tests/                     # Unit & integration tests
│   ├── requirements.txt           # Python dependencies
│   └── Dockerfile                 # Backend dockerization
├── frontend/
│   ├── src/
│   │   ├── app/                   # Next.js App Router (Dashboard, Copilot, etc.)
│   │   ├── components/            # UI components (charts, forms, sheets)
│   │   │   ├── ui/                # shadcn base components (button, card, dialog, etc.)
│   │   │   ├── dashboard/         # Dashboard analytics charts & cards
│   │   │   ├── explorer/          # Keyword explorer table, filtering, grouping
│   │   │   ├── optimizer/         # Listing editor, live score, keyword checklists
│   │   │   └── chat/              # Copilot chat window & prompt shortcuts
│   │   ├── store/                 # Zustand store (session, workspace)
│   │   ├── hooks/                 # React Query custom API query/mutations
│   │   ├── lib/                   # API clients, utils
│   │   └── types/                 # TypeScript type interfaces
│   ├── tailwind.config.js
│   ├── next.config.js
│   ├── package.json
│   └── Dockerfile                 # Frontend dockerization
├── docker-compose.yml             # Full-stack orchestration
└── README.md
```

---

## Database Models & Schema

We define a database file `seo_copilot.db` containing the following schemas:

### 1. `UploadSession`
- `id` (UUID, Primary Key)
- `filename` (String)
- `uploaded_at` (DateTime)
- `status` (String: PENDING, CLEANED, ANALYZED, ERROR)
- `summary_metadata` (JSON: rows count, brands found, competitors identified)

### 2. `Keyword`
- `id` (Integer, Primary Key)
- `session_id` (UUID, Foreign Key to UploadSession)
- `keyword` (String, Indexed)
- `search_volume` (Integer)
- `cpr` (Integer: Cerebro Product Rank / competing products count)
- `position_bias_ctr` (Float)
- **Engineered Features**:
  - `word_count` (Integer), `char_count` (Integer)
  - `contains_number`, `contains_unit`, `contains_brand`, `contains_tech` (Booleans)
  - `brand_name` (String), `brand_type` (String: Generic, Branded, Competitor)
  - `product_type` (String: Charger, Power Bank, Cable, etc.)
  - `tech_type` (String: GaN, PD, Lightning, etc.)
  - `intent` (String: Transactional, Commercial, Informational, Comparison, Review, Navigational)
  - `buyer_stage` (String: Awareness, Interest, Comparison, Purchase, Retention)
  - `traffic_potential`, `ctr_potential`, `ranking_potential`, `commercial_potential` (Floats)
  - `topic_cluster` (String), `keyword_cluster_id` (Integer)
- **Competitor Performance**:
  - `competitor_ranks` (JSON: mapping of competitor name to ranking position)
  - `competitor_coverage` (Integer: count of competitors ranking in top 20)
  - `ranking_gap` (Boolean: whether user lacks ranking where competitors rank)
- **Scores**:
  - `opportunity_score`, `revenue_score`, `competition_score`, `traffic_score`, `trend_score`, `gap_score`, `content_score`, `priority_score`, `business_score`, `seo_score`, `final_ai_score` (Floats 0-100)

### 3. `Listing`
- `id` (Integer, Primary Key)
- `session_id` (UUID, Foreign Key to UploadSession)
- `title` (String)
- `bullet_points` (JSON: array of 5 bullets)
- `description` (Text)
- `search_terms` (String)
- `aplus_content_ideas` (JSON)
- `faq` (JSON)
- `seo_score` (Integer)
- `updated_at` (DateTime)

### 4. `ChatMessage`
- `id` (Integer, Primary Key)
- `session_id` (UUID, Foreign Key to UploadSession)
- `role` (String: user, assistant)
- `content` (Text)
- `timestamp` (DateTime)

---

## Core Backend Services & Business Logic

### 1. Ingestion & Validation (`excel.py`)
- Reads file and validates sheet structure.
- Auto-maps typical export headers (e.g. Helium 10 `Search Volume`, `Competing Products`, `Cerebro IQ Score`, `Search Volume Trend`, `Position (Rank)`).
- Rejects files missing core columns: `keyword` and `search_volume`.

### 2. Data Cleaning (`cleaning.py`)
- Deduplicates keywords (casing-insensitive, keeps highest search volume version).
- Standardizes spelling variations, whitespace trimming, and capitalization.
- Replaces missing numerical metrics (Search Volume, ranks) using median imputation or defaults (e.g. rank = 101 or NULL).
- Generates a statistics report (`CleaningReport`) outlining modified rows and records.

### 3. Feature Engineering (`features.py`)
- **Intent Classifier**: Regular expression and token-based parser for intent:
  - Commercial terms: "best", "top", "premium", "vs", "rating", "review".
  - Buying terms: "buy", "price", "sale", "cheap", "pack", "set", "for phone".
- **Category & Product Type Detectors**: Configurable lexicons to detect accessories (e.g., "cable", "charger", "power bank").
- **Clustering**:
  - Encodes cleaned keywords using `SentenceTransformer('BAAI/bge-small-en-v1.5')` (cached locally).
  - Performs K-Means clustering (dynamic K based on dataset size, target 10-30 clusters).
  - Generates cluster names by extracting the highest search volume keywords from each group.

### 4. Competitor Analysis (`competitor.py`)
- Extracts all competitors listed in competitor rank columns.
- Generates competitor profile metrics: average rank, share of voice, keyword coverage, easy-win opportunities.
- Identifies "Keyword Gaps": keywords where at least 2 key competitors are in the top 15 but the user is not ranking (or is rank > 50).

### 5. Scoring Engine (`scoring.py`)
- Computes 10 normalized scores (0 to 100) using vectorized pandas operations:
  1. `Competition Score` = $100 \times \left(1 - \frac{1}{1 + \ln(competing\_products + 1)}\right)$
  2. `Opportunity Score` = Normalized $f(SearchVolume, CompetitionScore)$
  3. `Traffic Score` = Normalized Search Volume percentile.
  4. `Trend Score` = Percentile of volume trend / growth rate.
  5. `Revenue Score` = Estimate based on $SearchVolume \times CTR \times Price \times ConversionRate$.
  6. `Gap Score` = Measures competitor coverage gap ($100 - (100 \times \frac{competitors\_ranking}{total\_competitors})$).
  7. `Content Score` = Evaluates semantic richness (word length, contains features).
  8. `SEO Score` = Index of listing match potential.
  9. `Priority Score` = Weighted sum of Opportunity, Traffic, and Gap.
  10. `Final AI Score` = Aggregate score mapping overall utility.

### 6. Listing Optimizer (`listing.py`)
- Analyzes a given listing's text (Title, Bullets, Description) against a target list of high-opportunity keywords.
- Dynamic scoring calculation:
  - Title Matches (Weight: 40%): Counts exact and partial matches in Title (primary keywords).
  - Bullet Points Matches (Weight: 35%): Counts keyword inclusion across bullets.
  - Description & Search Terms (Weight: 25%).
  - Provides a list of "Unused Keywords" and "Used Keywords" in real-time.
- Calls Ollama LLM to generate SEO-optimized content incorporating top opportunity keywords.

### 7. AI Copilot Chat (`copilot.py`)
- Performs retrieval using cosine similarity of the user prompt embedding against stored keyword embeddings.
- Bundles matching keywords, aggregate competitor stats, and dataset summary metrics into a structured context window.
- Feeds context to Ollama (`qwen2.5:7b` or alternative specified local endpoint) with instructions to reason only on the provided data context (preventing hallucinations).

---

## API Specifications

### `POST /api/upload`
- **Request**: Multipart Form Data (`file: File`)
- **Response**: `UploadResponse` containing:
  - `session_id` (UUID)
  - `filename` (String)
  - `preview` (List of JSON dicts)
  - `columns_detected` (List of Strings)
  - `cleaning_summary` (JSON reports)

### `POST /api/analyze`
- **Request**: `{ "session_id": "UUID", "competitors": ["BrandA", "BrandB"], "user_brand": "BrandX" }`
- **Response**: Triggers complete features engineering, scoring calculations, and semantic clustering, returning an overall analysis status.

### `GET /api/dashboard?session_id=UUID`
- **Response**: Analytics summary:
  - KPI Cards: Total keywords, category count, competitor count, easy wins, aggregate traffic potential.
  - Charts: Intent distribution, buyer stage percentages, competitor share of voice, keyword cluster distributions.

### `GET /api/keywords?session_id=UUID&search=text&intent=text&cluster=text&limit=50&offset=0`
- **Response**: Paginated keyword records, supporting column sorting, filtering, and grouping.

### `POST /api/chat`
- **Request**: `{ "session_id": "UUID", "message": "String" }`
- **Response**: Streamed or single message response with markdown formatting, referencing specific keywords or stats extracted from the dataset.

### `POST /api/listing/generate`
- **Request**: `{ "session_id": "UUID", "target_keywords": ["keyword1", "keyword2"] }`
- **Response**: Generated Title, Bullets, Description, and Search Terms.

### `POST /api/listing/analyze`
- **Request**: `{ "session_id": "UUID", "title": "String", "bullets": ["String"], "description": "String", "search_terms": "String" }`
- **Response**: Live listing score card (score, matching keyword counts, unused keyword list).

### `POST /api/export`
- **Request**: `{ "session_id": "UUID", "format": "xlsx" | "pdf" }`
- **Response**: Binary file response containing a formatted Excel workbook or styled PDF document.

---

## Frontend Layout & Design System

The frontend will use a modern, interactive Dark Mode design with smooth transitions and high contrast cards.

- **Global Navigation Sidebar**: Collapsible navigation with links:
  - **Dashboard**: Metrics grids, traffic distribution, competitor bubble charts.
  - **Keyword Explorer**: High-performance sorting/filtering grid table with details drawer.
  - **Competitor Gaps**: Gap analysis matrix (where competitors rank but we don't).
  - **Listing Optimizer**: Split-screen listing editor and keyword checklist.
  - **AI Chat Copilot**: Floating ChatGPT-style assistant.
  - **Reports / Export**: Generate execution summaries and download PDF/Excel reports.
  - **Settings**: Adjust weights for opportunity scoring, configure Ollama endpoint, reset DB.

- **Design Details**:
  - Primary Theme: Dark Glassmorphic (deep charcoal `#0B0F19`, slate blue, vibrant indigo and violet gradients).
  - Components: Custom tables with skeleton loaders, glowing card states, progress bars.
  - Notifications: Sonner toast system.

---

## Verification Plan

### Automated Tests
We will write unit tests inside `backend/tests/` to verify:
1. Excel parsing consistency.
2. Data cleaning correctness (whitespace, punctuation, casing, null-handling).
3. Score engine calculations (ensuring values are strictly 0-100 and monotonically reasonable).
4. Feature engineering logic (intent classification, product extraction).
5. Listing parser (live SEO scoring correctness).

### Manual Verification
1. We will verify the Ollama connection using test prompts.
2. We will generate mockup keyword sheets (e.g. 50-100 rows containing chargers, power banks, competitor ranks) to test the end-to-end ingestion and RAG capabilities.
3. We will build the full app locally and open the browser interface to verify visual consistency, sorting, charts rendering, and export functions.
