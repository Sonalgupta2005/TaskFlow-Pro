# <img src="frontend/public/layers.svg" alt="TaskFlow Pro Logo" width="36" height="36" align="center"> TaskFlow Pro

TaskFlow Pro is a modern, responsive Kanban board powered by a backend Directed Acyclic Graph (DAG) dependency engine. It visually tracks task progress while actively enforcing and evaluating finish-to-start dependencies, showing blocked vs ready tasks, predicting end dates, and preventing circular dependencies.

## ✨ Key Features

- **Strict DAG Dependency Engine:** Validates every edge against cycles before persisting to the DB.
- **Dynamic Re-scheduling:** Automatically recomputes the earliest possible start and end dates based on upstream task completions, without double-counting converging dependency paths (Diamond dependency resolution).
- **Critical Path Highlighting:** Automatically computes tasks with zero slack (backward pass algorithm) and visually highlights them.
- **AI-Augmented Dependency Suggestions:** Uses the Gemini AI model to inspect task descriptions and titles to suggest likely dependencies, with deterministic server-side guardrails against cycles.
- **User Authentication:** Multi-tenant architecture securely isolates user data via JWT authentication.
- **Rich User Interface:** Features a stunning dark mode interface using glassmorphism, fluid drag-and-drop mechanics (using `dnd-kit`), and an interactive Read-Only Dependency Graph View (using `React Flow`).

## 🎥 Demo
<video controls src="demo-video.mp4" title="TaskFlow Pro Demo"></video>

## 🛠️ Setup Instructions

### Backend (FastAPI, Python)
1. Navigate to the `backend` directory.
2. Initialize a virtual environment: `python -m venv venv` and activate it: `.\venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux).
3. Install dependencies: `pip install -r requirements.txt`
4. Create a `.env` file in the `backend` directory and add:
   ```env
   JWT_SECRET_KEY=your_secure_random_string_here
   GEMINI_API_KEY=your_gemini_api_key_here
   ```
5. Run the backend server: `uvicorn main:app --reload`
6. The backend will be available at `http://localhost:8000`.

*(Note: The database is automatically seeded per-user via the frontend "Seed Data" button when a new user registers).*

### Frontend (React, Vite, TypeScript)
1. Navigate to the `frontend` directory.
2. Install dependencies: `npm install`
3. Run the development server: `npm run dev`
4. Access the Kanban board at `http://localhost:5173`.

## 🌍 Deployment (Vercel & Render)

- **Database:** By default, TaskFlow Pro uses SQLite for local development. To run in production, set the `DATABASE_URL` environment variable (e.g., `postgres://...`) and the backend will seamlessly switch to PostgreSQL.
- **Frontend (Vercel):** Connect your repo, set the Framework Preset to Vite, and add `VITE_API_URL` to point to your backend.
- **Backend (Render):** Connect your repo, set the Build Command to `cd backend && pip install -r requirements.txt`, and Start Command to `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`.

## 🏗️ Architecture

TaskFlow Pro is built using a modern decoupled architecture:
- **Frontend (React/Vite/TypeScript):** Uses `dnd-kit` for fluid drag-and-drop interactions and `React Flow` for the interactive DAG visualization. State is optimistically updated for responsiveness.
- **Backend (FastAPI/Python):** Exposes a RESTful API. Business logic is separated into a dedicated scheduling engine (`engine.py`) that performs topological sorting, forward/backward passes for critical path analysis, and strict cycle detection on every mutation.
- **Database (SQLAlchemy):** Supports SQLite for local development and PostgreSQL for production. It uses a strictly multi-tenant design where every record is isolated by a `user_id`.
- **Authentication:** JWT-based stateless authentication using bcrypt for password hashing.
- **AI Integration:** Google Gemini API is used to perform semantic analysis of task titles and descriptions to auto-suggest dependencies.

## 📊 Data Models

The relational schema consists of four primary models:
1. **`User`:** Manages authentication (`username`, `hashed_password`).
2. **`Task`:** Represents a Kanban item. Stores metadata (`title`, `description`), lifecycle data (`status`, `position`), scheduling parameters (`duration_days`, `planned_start`), and computed engine results (`start_date`, `end_date`, `blocked`, `is_critical`).
3. **`Dependency`:** Represents a directed edge (Finish-to-Start) linking a `prerequisite_id` to a `dependent_id`.
4. **`DependencySuggestion`:** Temporarily stores AI-generated edges awaiting human review and acceptance.

## ⚠️ Known Limitations

1. **Weekend and Holiday Scheduling:** The scheduling engine calculates end dates using strict calendar days (adding `duration_days` directly to `start_date`). It does not currently skip weekends or bank holidays.
2. **Time Zones:** Dates are processed in UTC at the backend. If users in vastly different time zones create tasks near midnight, the "planned start date" might occasionally render off-by-one-day on the frontend due to localized browser rendering.
3. **Real-time Sync:** Concurrency is handled gracefully at the database level, but real-time multi-user websocket synchronization is out of scope for this prototype.
4. **Suggestion Rate Limiting:** The AI auto-suggest feature lacks strict debounce/rate-limiting on the frontend. Rapid, consecutive clicks could theoretically queue redundant LLM API calls.

## 📌 Key Assumptions

1. **Finish-to-Start Dependencies Only:** The engine strictly models finish-to-start dependencies, meaning a dependent task cannot begin until all prerequisite tasks are fully completed ("Done").
2. **Fixed Durations in Calendar Days:** Schedule calculations assume simple consecutive calendar days and do not currently skip weekends or holidays.
3. **Optimistic Updates:** The UI updates optimistically when dragging a task. If the backend detects a rule violation (e.g., trying to move a blocked task to "Done"), it will reject the action and the UI state rolls back with an error toast.
4. **Frozen Actuals:** When a task is marked "Done", its dates are frozen and no longer shift forward even if a prerequisite shifts.

## 🎯 Evaluation Criteria Addressed

- **Cycle Detection:** Built into the backend engine (`engine.py`).
- **Diamond Math:** Using `max()` for end dates rather than accumulating deltas solves converging path double counting.
- **Rollback Behavior:** Status changes re-trigger graph recomputation ensuring regression to blocked states if needed.
- **AI/LLM Usage:** Integrates Gemini AI for dependency auto-suggestions, passing output through deterministic guardrails before human acceptance.
- **Critical Path:** Backend implements a forward and backward pass algorithm.
- **Testing & Reliability:** Includes a comprehensive suite of backend tests (`TESTING.md`).
