# Enterprise No-Code Agent Platform — Local Demonstration

A **working prototype** intended for a manager / architect demonstration. It is **not** a production-ready identity, AI, or enterprise integration system.

## Start on Windows (beginner steps)

1. Right-click the downloaded ZIP and select **Extract All**.
2. Open the extracted `enterprise-agent-platform` folder.
3. Install Python 3.11 or 3.12 from https://www.python.org/downloads/ if you do not have it. During installation, check **Add Python to PATH** if offered.
4. Make sure you have an internet connection for the initial package installation.
5. Double-click `start_windows.bat`. Windows may show a SmartScreen warning for locally created scripts; inspect the file before running it.
6. Wait while packages install. The browser should open `http://127.0.0.1:8000`.
7. **Keep the black command window open** while demonstrating.
8. To stop, click the command window and press **Ctrl+C**.

If LangGraph cannot be installed, `start_minimal_windows.bat` provides a clearly labeled sequential fallback. **Do not claim parallel LangGraph orchestration while using fallback mode.**

## Demo walkthrough (10–15 minutes)

1. **Chat:** Select Krishna; ask `Check my leave balance, pending reimbursements and upcoming meetings`. Inspect execution engine and trace.
2. **Agent Builder:** Describe `Create an agent to check my expense reimbursements`; generate, review, save draft.
3. **Registry:** Publish the draft; show its version. Create another draft with the same name to demonstrate version increments.
4. **Security:** As Krishna, click `Try restricted customer query`; expect 403. Switch identity to Manager; repeat and get ACME renewal-risk summary.
5. **Recovery:** Click `Run and fail at step 5`, then `Resume same run`. Show steps 1–4 skipped and steps 5–10 completed.
6. **Search:** Search `renewal` as employee and manager; manager can access the restricted playbook.
7. **Logs:** Show recorded execution traces.
8. **Approval:** Request an action; switch to Admin and inspect approval records. Admin can approve via API `/docs` endpoint (there is no approval button in UI).

## Run tests

Double-click `run_tests_windows.bat` after a successful installation. Alternatively, with virtual environment activated: `python -m unittest discover -s tests -v`.

## Architecture

- Static HTML/CSS/JS UI served by FastAPI, not React (intentionally reduced setup complexity).
- FastAPI + Pydantic for API/schema validation.
- SQLite for agent registry, versioning, logs, approvals, and recovery step records.
- Actual LangGraph StateGraph execution **when installed**; independent HR/Finance/Calendar nodes are connected from START and can be scheduled concurrently by LangGraph. Customer -> Support -> Renewal is sequential.
- Fixed, approved tool catalog; mock HR, Finance, Calendar, CRM, Support data.
- Role checks at router and tool-call layer.
- Deterministic configuration generator. No LLM API calls or dynamic model selection.
- Keyword search with role-based document filtering; not embeddings or vector RAG.
- Separate deterministic 10-step recovery demo using SQLite records; **not LangGraph checkpoint persistence**.

## Important limitations — disclose to your manager

- Demo identity selector is **not secure authentication**; headers can be forged. No OAuth/SSO, tenant isolation, or real identity integration.
- No actual cloud deployment, model gateway, MCP tool gateway, Redis, PostgreSQL, pgvector, real Salesforce, or LLM-backed agent generation.
- Agent configurations select among prebuilt agent kinds. They do not dynamically compile arbitrary workflows.
- Approval records are demonstrative and not wired to sensitive tool writes.
- LangGraph graph execution is real only when the package is installed; fallback mode is sequential.
- Failure recovery is persistent step-based simulation, not genuine LangGraph checkpoint/resume.
- No robust retry/backoff, idempotent external writes, async job queue, or full enterprise-grade observability.
- Tests cover representative API and security behavior; no browser automation or production load testing.

This is an honest functional **MVP / starter prototype**, not the complete enterprise-grade system. To meet all senior-architect requirements, extend the platform with LangGraph persistence, real config-driven graphs, secure identity, approvals tied to writes, full tests, and production infrastructure.

## API reference

Open `http://127.0.0.1:8000/docs` for interactive Swagger API documentation. Demo identity is sent via `X-Demo-User` header. Default is `krishna`.

## Reset demo

Close the application and delete `agent_platform.sqlite3` in the project folder. On next start, sample data will be recreated. This deletes locally created demo agents and logs.
