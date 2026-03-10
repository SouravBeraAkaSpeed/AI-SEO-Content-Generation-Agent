# AI SEO Content Generation Agent

## Overview
The **AI SEO Content Generation Agent** is a sophisticated backend service designed to produce high-quality, search-engine-optimized articles at scale. Unlike standard LLM text generators, this system functions as an intelligent agent that researches the competitive landscape before drafting content. By analyzing real-world Search Engine Results Page (SERP) data, the agent identifies winning patterns, search intent, and topical gaps to produce content that is both authoritative and rank-ready.

## The Problem Space
In modern SEO, content quantity is no longer enough. Search engines prioritize "Expertise, Authoritativeness, and Trustworthiness" (E-E-A-T). To rank, content must:
1.  **Understand Intent:** Align with what users are actually looking for based on current top results.
2.  **Maintain Structure:** Use proper semantic header hierarchies (H1-H3).
3.  **Provide Context:** Include credible external citations and logical internal linking.
4.  **Read Naturally:** Avoid "bot-like" repetitive structures that trigger quality filters.

This service solves these challenges by implementing a research-first agentic workflow.

---

## Core Features
- **Agentic SERP Analysis:** Automatically analyzes the top 10 search results to identify common themes, subtopics, and competitor strategies.
- **Multi-Stage Workflow:** Uses a state-machine architecture to separate Research, Strategy (Outlining), and Content Generation.
- **Strict Structured Outputs:** Leverages Pydantic models to ensure 100% predictable JSON responses for metadata, links, and FAQ sections.
- **Deterministic SEO Validation:** A programmatic validation layer ensures every article meets strict SEO constraints (Keyword in Title, H1 presence, Meta-length) before completion.
- **Job Resilience & Durability:** Built with a persistent database layer (SQLite/SQLAlchemy) allowing for job tracking, status monitoring, and seamless retries from the last successful state.
- **Human-Centric Content:** Utilizes `gemini-3-flash` with optimized temperature settings to ensure a natural, engaging writing style.

---

## Technical Architecture

### System Flow
The system operates as an asynchronous worker service:
1.  **Ingestion:** User submits a topic and target word count.
2.  **Research Phase:** The agent fetches SERP data (Mocked/Real) to build a context window of what is currently ranking.
3.  **Strategy Phase:** Gemini analyzes the research and produces a logical `ArticleOutline`.
4.  **Generation Phase:** The agent expands the outline into a full markdown article, including metadata, linking suggestions, and citations.
5.  **Validation Phase:** The `SEOValidator` checks the final output against hard SEO requirements.
6.  **Persistence:** All stages are saved to a SQL database, allowing users to query job status at any time.

### State Machine Model
Each generation job moves through a strictly defined lifecycle:
- `PENDING`: Job created and queued.
- `SERP_ANALYZED`: Competitive research successfully gathered.
- `OUTLINE_GENERATED`: Strategy and header structure finalized.
- `COMPLETED`: Article generated, validated, and ready for publishing.
- `FAILED`: Job halted due to API or validation errors (stored with error logs).

---

## Technology Stack
- **Language:** Python 3.12+
- **Framework:** FastAPI (High-performance API layer)
- **AI Model:** Google Gemini-3-Flash (`google-genai`)
- **Database:** SQLAlchemy 2.0 (ORM) with SQLite (Persistence)
- **Data Validation:** Pydantic v2 (Strict schema enforcement)
- **Environment:** python-dotenv (Secure configuration management)
- **Testing:** Pytest (Validation and logic coverage)

---

## Setup & Installation

### 1. Environment Configuration
Create a `.env` file in the root directory:
```text
GEMINI_API_KEY=your_google_gemini_api_key_here
```

### 2. Dependency Installation
```bash
pip install -r requirements.txt
```

### 3. Database Initialization
The system uses SQLite. The tables are automatically created upon the first launch of the FastAPI server.

### 4. Running the Service
```bash
uvicorn main:app --reload
```
The API will be available at `http://localhost:8000`. Full interactive documentation can be found at `http://localhost:8000/docs`.

---

## API Reference

### Create Generation Job
`POST /jobs`
**Input:**
```json
{
  "topic": "best productivity tools for remote teams",
  "target_word_count": 1500,
  "language": "English"
}
```

### Get Job Status & Result
`GET /jobs/{job_id}`
**Response:**
Returns the status. If `COMPLETED`, includes the full `result` object containing:
- `metadata`: Title tag, Meta description, Keywords.
- `article_markdown`: The full text in Markdown format.
- `internal_links`: 3-5 suggestions with anchor text and target context.
- `external_references`: 2-4 authoritative citations.
- `faq_section`: Common questions and answers.

### Retry Failed Job
`POST /jobs/{job_id}/retry`
Rolls back the job to its last successful state and re-triggers the background agent.

---

## Design Decisions

### Why Gemini-3-Flash?
We utilized the `gemini-3-flash` model for its high context window and speed. The model is specifically configured via `GenerateContentConfig` to enforce JSON outputs, ensuring that the backend can reliably parse complex nested data like internal links and SEO metadata without failure.

### Decoupled Agent Logic
The AI logic is encapsulated in the `AgentWorkflow` class. This separates the "thinking" (prompt engineering, AI calls) from the "delivery" (FastAPI routes). This allows for easier testing and the potential to swap AI providers or SERP providers in the future without touching the API layer.

### Programmatic SEO Validation
To guarantee quality, we don't just rely on the LLM's "best effort." The `SEOValidator` class performs hard checks on the final output. If the AI fails to include the primary keyword in the title tag or skips an H1 header, the job is marked as `FAILED`, preventing low-quality content from reaching the end user.

---

## Testing
The suite includes tests for the API lifecycle and the SEO validation logic.
```bash
pytest test_main.py -v
```
**Test Coverage Includes:**
- Successful job creation and queuing.
- SEO Validation: Passing valid content.
- SEO Validation: Rejecting content missing H1 headers.
- SEO Validation: Rejecting content with meta descriptions exceeding length limits.
- Pydantic schema length enforcement (Link count requirements).

---

## Future Roadmap
- **Content Quality Scorer:** An additional AI pass to evaluate the "human-like" quality of the draft and trigger automatic revisions.
- **Image Generation Integration:** Automated generation of featured images based on the article's H1 and metadata.
- **CMS Connectors:** One-click publishing to WordPress, Webflow, or Shopify via their respective APIs.
- **Real SERP Integration:** Currently utilizing high-fidelity mock data for search analysis; modular design allows for instant integration with SerpAPI or DataForSEO.