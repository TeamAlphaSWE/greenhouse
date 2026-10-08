# Greenhouse Backend

Flask backend API for the Greenhouse application.

## Project Structure

```text
backend/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── db.py
│   └── routes/
│       ├── __init__.py
│       └── health.py
├── tests/
│   ├── conftest.py
│   ├── test_db.py
│   └── test_health.py
├── requirements.txt
└── README.md
```

## Setup

From the repository root, activate the project virtual environment:

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Install the backend dependencies:

```bash
pip install -r backend/requirements.txt
```

## Configuration

The backend reads its settings from environment variables. When started through the Flask CLI (`flask run` or `make run`), variables in the repository's `.env` file are loaded automatically; copy `.env.example` to `.env` to get started.

| Variable | Default | Description |
| --- | --- | --- |
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGO_DB_NAME` | `greenhouse` | Database used by the app |
| `MONGO_SERVER_SELECTION_TIMEOUT_MS` | `5000` | How long a query waits for a reachable server before failing |

## Running the Backend

From the `backend` directory:

```bash
flask --app app run --debug
```

By default, the Flask API will be available at:

```text
http://localhost:5000
```

## API

### Health Check

Used to verify that the backend is running and available.

```http
GET /api/v1/health
```

Response:

```json
{
  "status": "ok"
}
```

## Database Access

The app creates one `MongoClient` at startup (`app/db.py`) and shares it across all requests; PyMongo pools connections internally, so no per-request setup or teardown is needed. Use the helpers in `app.db` anywhere inside a request or app context:

```python
from app.db import get_collection

def list_plants():
    return list(get_collection("plants").find({}, {"_id": 0}))
```

- `get_collection(name)` – a collection in the configured database
- `get_db()` – the configured `Database`
- `get_client()` – the shared `MongoClient` (e.g. for transactions)
- `ping()` – `True` if MongoDB is reachable

The client connects lazily, so the app starts even when MongoDB is not running; queries will fail after `MONGO_SERVER_SELECTION_TIMEOUT_MS`.

Tests do not need a running MongoDB: the `app` fixture in `tests/conftest.py` injects an in-memory [mongomock](https://github.com/mongomock/mongomock) client through the `MONGO_CLIENT` config key.

```python
def test_something(app):
    with app.app_context():
        get_collection("plants").insert_one({"name": "Basil"})
```

## Running Tests

From the `backend` directory with the virtual environment active:

```bash
pytest
```

To run tests with additional output:

```bash
pytest -v
```

## Development

The backend uses Flask's application factory pattern. The application is created by `create_app()` in `app/__init__.py`.

API routes should be organized using Flask Blueprints under `app/routes/`.

As the backend grows, additional services, integrations, and data access code should be organized within the `app/` package rather than placed directly in route handlers. Data access code should get collections through `app.db` rather than creating its own `MongoClient`.