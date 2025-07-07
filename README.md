# SOW Solution Recommender

An AI-powered consulting strategist tool that matches new client needs to past Statements of Work (SOWs) and generates solution recommendations. Built with FastAPI, Supabase, OpenAI, and Streamlit.

## 🔧 Features

- Match client prompts to similar past SOWs using embeddings
- Generate 2–3 tailored solution suggestions via GPT-4o
- Save suggestions to Supabase
- Export recommendations as a text file
- Simple, clean Streamlit interface

---

## 🗂️ Project Structure

```bash

consulting-app/
│
├── app.py               # FastAPI backend with API endpoints
├── seed_db.py           # Script to generate and store embeddings
├── streamlit_app.py     # Streamlit frontend UI
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (not committed)
└── consulting/          # Supabase schema and data tables
    ├── sows             # Statements of Work
    ├── clients          # Client info
    ├── solutions        # Past solutions
    └── embeddings       # Vector embeddings for SOW matching
```
---

## 🚀 Setup Instructions

### 1. Environment Setup

```bash
git clone https://github.com/your-repo/sow-recommender
cd sow-recommender
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment Variables

Create a .env file with:
```bash
OPENAI_API_KEY=your_openai_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_or_service_role_key
SUPABASE_POSTGRES_URL=postgresql://user:pass@host:port/dbname
```

### 3. Database

Ensure you’ve created the following tables in your Supabase PostgreSQL instance:

```postgresql
-- consulting.sows, consulting.clients, consulting.solutions
-- Plus:
CREATE TABLE consulting.embeddings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  sow_id UUID UNIQUE REFERENCES consulting.sows(id) ON DELETE CASCADE,
  embedding BYTEA
);

CREATE TABLE consulting.saved_suggestions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prompt TEXT,
  suggestions TEXT[]
);
```

### 4. Seed Embeddings

```bash
python seed_db.py
```

### 5. Run Backend

```bash
uvicorn app:app --reload
```

### 5. Run Frontend

```bash
streamlit run streamlit_app.py
```

## ✨ Example Prompt

```bash
We need to integrate multiple hospital data sources
 into a unified analytics platform on the cloud.
```

## ✅ To-Do / Ideas
	•	Deploy FastAPI + Streamlit online
	•	Add user login and project history
	•	Support multi-SOW report generation
	•	Add confidence score visualizations


## Powered By

	•	FastAPI
	•	Streamlit
	•	OpenAI
	•	Supabase
