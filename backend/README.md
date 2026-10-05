# Greenhouse Backend

Flask backend API for the Greenhouse application.

## Project Structure

```text
backend/
├── app/
│   ├── __init__.py
│   └── routes/
│       ├── __init__.py
│       └── health.py
├── tests/
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

As the backend grows, additional services, integrations, and data access code should be organized within the `app/` package rather than placed directly in route handlers.