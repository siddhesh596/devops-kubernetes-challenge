# DevOps Kubernetes Challenge — Task Management API

A small, intentionally minimal Task Management REST API built as the
application under test for a Kubernetes / CI-CD infrastructure challenge.
The focus of the challenge is infrastructure (Docker, Kubernetes, CI/CD),
so the app itself is kept as simple as possible.

## Stack

- Python 3.12
- Flask
- PostgreSQL (via `psycopg2-binary`)
- Plain `logging` to stdout/stderr

## Project Structure

```text
devops-kubernetes-challenge/
├── app/
│   ├── app.py            # Flask app, routes, validation, error handling
│   ├── database.py       # psycopg2 connection + SQL
│   ├── requirements.txt
│   └── config.py         # env-var based configuration
├── tests/
│   └── test_app.py       # pytest suite (DB layer is mocked)
├── .gitignore
├── README.md
└── Dockerfile
```

## Configuration

All configuration is via environment variables — nothing is hardcoded.
The same Docker image is used unchanged across local dev, Docker, and
Kubernetes; only these values change:

| Variable      | Example (local) | Example (Kubernetes)  |
|---------------|------------------|------------------------|
| `DB_HOST`     | `localhost`      | `postgres-service`     |
| `DB_PORT`     | `5432`           | `5432`                 |
| `DB_NAME`     | `appdb`          | `appdb`                |
| `DB_USER`     | `postgres`       | (from Secret)          |
| `DB_PASSWORD` | `postgres`       | (from Secret)          |

## Running Locally

1. Start PostgreSQL (locally or via Docker) and export the env vars above.
2. Install dependencies:

   ```bash
   cd app
   pip install -r requirements.txt
   ```

3. Run the app:

   ```bash
   python app.py
   ```

   The API listens on `http://0.0.0.0:5000`. The table is created
   automatically on startup — no manual SQL required.

## Running with Docker

```bash
docker build -t devops-challenge-api .
docker run -p 5000:5000 \
  -e DB_HOST=host.docker.internal \
  -e DB_PORT=5432 \
  -e DB_NAME=appdb \
  -e DB_USER=postgres \
  -e DB_PASSWORD=postgres \
  devops-challenge-api
```

## Running Tests

Tests exercise the real Flask routes with the database layer mocked out,
so they run without a live PostgreSQL instance (useful in CI):

```bash
cd app
pip install -r requirements.txt
cd ..
pytest tests/
```

## API Reference

| Method | Path           | Description                          |
|--------|----------------|---------------------------------------|
| GET    | `/`            | Application info                      |
| GET    | `/health`      | Liveness/readiness — no DB dependency |
| GET    | `/db-health`   | Database connectivity check           |
| GET    | `/tasks`       | List all tasks                        |
| GET    | `/tasks/<id>`  | Get one task                          |
| POST   | `/tasks`       | Create a task                         |
| PUT    | `/tasks/<id>`  | Update a task                         |
| DELETE | `/tasks/<id>`  | Delete a task                         |

### Task fields

- `title` — required, string, max 200 characters
- `description` — optional, string
- `status` — one of `pending`, `in-progress`, `completed` (default `pending`)

### Example: create a task

```bash
curl -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Learn Kubernetes", "description": "Practice deployments"}'
```

## Why `/health` and `/db-health` Are Separate

`/health` never touches PostgreSQL. It only reports that the Flask process
is alive, which is what Kubernetes liveness/readiness probes should check —
a temporary database outage should not cause Kubernetes to kill and
restart otherwise-healthy pods. `/db-health` reports database connectivity
separately, returning HTTP 503 when PostgreSQL is unreachable.

## Roadmap (Next Phase)

This application is designed to be deployed as-is into Kubernetes:

- Deployment (2 replicas) + Service for the API
- Deployment + Service for PostgreSQL
- Secret for DB credentials
- Liveness probe → `/health`
- Readiness probe → `/db-health` or `/health`
- Resource requests/limits
- CI/CD pipeline (build, test, push, deploy)

## Constraints

By design, this project intentionally does **not** include: a frontend,
authentication/JWT, Redis, Kafka, microservices, message queues, a complex
ORM, external API integrations, or any AI/payment functionality. The goal
is to keep the application simple so the challenge stays focused on
infrastructure.
