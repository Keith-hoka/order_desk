# order_desk — exception review UI

A Next.js review desk for the extracted-order exception queue. It reads the
priority-sorted queue from the FastAPI review service (Phase 7 backend) and
lets a reviewer approve, edit, or reject each flagged extraction.

## Design

Warm-paper background, IBM Plex Sans/Mono, and a restrained shipping-blue /
brick / amber signal palette — deliberately not a templated SaaS look. Each
exception surfaces *why* it was flagged (reply-history ask, moderate-confidence
fields in the [0.80, 0.95] band, or a policy violation) rather than an abstract
score, and confidence badges appear only on fields inside the actionable band.

## Running

The UI needs the backend serving a pre-built queue.

### 1. Build the queue (once, requires OpenAI + Modal)

From the repo root: 

caffeinate -i uv run python scripts/build_review_queue.py  

This runs the human .eml corpus through the pipeline and writes
`data/review_queue.json`.

### 2. Start the backend

From the repo root, serving the queue with auth: 

JWT_SECRET=$(grep '^JWT_SECRET=' .env | cut -d= -f2) 
REVIEW_QUEUE_PATH=data/review_queue.json 
uv run uvicorn order_desk.api.app:app --port 8000  

### 3. Configure and start the frontend  

cp .env.local.example .env.local

put a token in .env.local:

JWT_SECRET=$(grep '^JWT_SECRET=' ../.env | cut -d= -f2) 
uv run --project .. python ../scripts/issue_token.py --sub reviewer
npm install
npm run dev  

Open http://localhost:3000.
