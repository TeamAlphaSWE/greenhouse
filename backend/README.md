# Greenhouse Backend

Flask backend API for the Greenhouse application.

## Project Structure

```text
backend/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── db.py
│   ├── json.py
│   ├── repository.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── plants.py
│   └── routes/
│       ├── __init__.py
│       ├── health.py
│       └── plants.py
├── tests/
│   ├── conftest.py
│   ├── test_db.py
│   ├── test_health.py
│   ├── test_plants.py
│   └── test_repository.py
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

### Plants

Example CRUD resource built on a repository.

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| `GET` | `/api/v1/plants` | | `200` list of plants |
| `GET` | `/api/v1/plants/<id>` | | `200` plant, `404` if not found |
| `POST` | `/api/v1/plants` | `{"name": "Basil"}` | `201` created plant, `400` if `name` is missing |
| `PATCH` | `/api/v1/plants/<id>` | `{"name": "Thai Basil"}` | `200` updated plant, `400` / `404` |
| `DELETE` | `/api/v1/plants/<id>` | | `204`, `404` if not found |

A plant looks like:

```json
{
  "id": "6650c1f2a1b2c3d4e5f60718",
  "name": "Basil"
}
```

## Database Access

The app creates one `MongoClient` at startup (`app/db.py`) and shares it across all requests; PyMongo pools connections internally, so no per-request setup or teardown is needed.

### Repositories

Data access goes through a repository per collection, kept in `app/repositories/`. Subclass `Repository` (`app/repository.py`), set the collection name, and add any domain-specific queries. The plants endpoints (`app/repositories/plants.py`, `app/routes/plants.py`, `tests/test_plants.py`) are a complete working example.

```python
from app.repository import Repository


class PlantRepository(Repository):
    collection_name = "plants"

    def find_by_kind(self, kind):
        return self.find({"kind": kind})


plants = PlantRepository()
```

Every repository provides `find(filter)`, `find_one(filter)`, `get(id)`, `create(data)`, `update(id, changes)` and `delete(id)`. Documents come back as plain dicts with a string `id` in place of Mongo's `_id: ObjectId`, and ids are passed in as strings. `get`, `update` and `delete` treat a malformed id like a missing document (`None` / `False`), so route handlers never touch BSON types:

```python
@bp.get("/plants/<plant_id>")
def show(plant_id):
    plant = plants.get(plant_id)
    if plant is None:
        abort(404)
    return jsonify(plant)
```

For queries the base class doesn't cover (aggregations, bulk writes), use `self.collection` inside the repository to reach the PyMongo collection directly.

The app also registers a JSON provider (`app/json.py`) that serializes `ObjectId` values as strings, so documents with ObjectId references can be passed to `jsonify` as-is.

### Lower-level helpers

`app.db` exposes the underlying objects if you need them: `get_collection(name)`, `get_db()`, `get_client()` (e.g. for transactions) and `ping()`.

The client connects lazily, so the app starts even when MongoDB is not running; queries will fail after `MONGO_SERVER_SELECTION_TIMEOUT_MS`.

Tests do not need a running MongoDB: the `app` fixture in `tests/conftest.py` injects an in-memory [mongomock](https://github.com/mongomock/mongomock) client through the `MONGO_CLIENT` config key.

```python
def test_something(app):
    with app.app_context():
        plants.create({"name": "Basil"})
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

As the backend grows, additional services, integrations, and data access code should be organized within the `app/` package rather than placed directly in route handlers. Data access code should live in `Repository` subclasses rather than creating its own `MongoClient` or calling PyMongo from route handlers.