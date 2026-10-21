# API Conventions

## Routes

- One Blueprint per resource in `app/routes/<name>.py`, registered in `create_app()`.
- Database access goes through `app/repositories/<name>.py`, never directly from routes.

## URLs

- Format: `/api/v1/<plural-noun>`, lowercase, no verbs, e.g. `/api/v1/zones`.
- One item: `/api/v1/zones/<id>`.
- Methods: `GET` read, `POST` create, `PATCH` update, `DELETE` delete.

## Responses

- JSON with `snake_case` fields. Using '_'
- Lists are wrapped: `{"zones": [...], "total": 3}`

## Errors

- Format: `{"error": "message"}`
- `200` OK, `201` created, `204` deleted, `400` bad input, `404` not found, `500` server error.

## Validation

- Missing or invalid input returns `400` with an error message.
- Save only the expected fields from the request.
