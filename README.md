# OpenHR Interview Practice

POC web app for voice-based interview practice for intern/fresher candidates.

## Current phase

Phase 1 provides the React/Vite shell, FastAPI configuration API, startup config validation, API contracts, mock provider interfaces, and an in-memory mock session lifecycle. Document upload/parsing, interview turns, and final report are intentionally not implemented yet.

The POC accepts text-based PDF and DOCX documents once Phase 2 is implemented. Scanned-document OCR is out of scope.

## Prerequisites

- Python 3.12 or compatible version supported by the backend dependencies.
- Node.js 22.12 or newer for the current Vite toolchain.

## Run the API

From the project root, create and activate a virtual environment, then install backend dependencies:

    python -m venv backend/.venv
    backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
    backend/.venv/Scripts/python.exe -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

The interactive API schema is available at /docs. Runtime profiles are served from GET /api/v1/config.

## Run the web app

In another terminal:

    cd frontend
    npm install
    npm run dev

Copy frontend/.env.example to frontend/.env.local only if the API URL differs from the default. Copy the root .env.example to .env to customize backend CORS or config location.

## Phase 1 API behavior

- GET /api/v1/health reports API/config readiness.
- GET /api/v1/config returns languages, levels, and pressure profiles loaded from YAML.
- POST /api/v1/sessions creates an in-memory development session from document IDs and configured profiles. Phase 1 does not check that the documents exist.
- POST /api/v1/sessions/{id}/start and /complete exercise the mock session lifecycle.
- Document upload, turn submission, and report routes are documented placeholders and return 501 until their planned phases.

Config schema and semantic validation run during API startup. Correct invalid YAML/config before starting the backend.
