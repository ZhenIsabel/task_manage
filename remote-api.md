# Remote API Usage

## Summary

This project exposes HTTP APIs. If the remote server is already deployed and reachable, prefer calling the API instead of reading the remote SQLite file directly.

Base URL example:

    http://<host-or-ip>

## Authentication

All business endpoints require Bearer authentication except:

- GET /api/health
- POST /api/users

Header format:

    Authorization: Bearer <your-token>

There is no separate login endpoint. POST /api/users is used to register a user and store the api_token you provide. Use the same token in later requests.

## Endpoint List

- GET /api/health
- POST /api/users
- GET /api/tasks
- POST /api/tasks
- DELETE /api/tasks/<task_id>
- GET /api/tasks/<task_id>/history
- GET /api/scheduled_tasks
- POST /api/scheduled_tasks
- DELETE /api/scheduled_tasks/<task_id>

## Endpoint Details

### GET /api/health

Auth: no
Purpose: basic health check
Typical response fields:
- status
- timestamp
- version

### POST /api/users

Auth: no
Purpose: create a user
Request content type:
- application/json
Required body fields:
- username: non-empty string
- api_token: non-empty string
Typical success response fields:
- user_id
- username
Possible error:
- 409 when username or token already exists

### GET /api/tasks

Auth: yes
Purpose: list tasks for the current user
Typical response fields:
- tasks
- count

### POST /api/tasks

Auth: yes
Purpose: create or update a task by id
Request content type:
- application/json
Required body fields:
- id: non-empty string
Optional body fields:
- position.x: integer, default 100
- position.y: integer, default 100
- text: string
- notes: string
- color: string
- completed: boolean
- completed_date: string
- deleted: boolean
- due_date: string
- priority: string
- urgency: string, default low
- importance: string, default low
- directory: string
- create_date: string
Behavior:
- create when id does not exist
- update when id already exists
Typical success response fields:
- success
- action
- task_id

### DELETE /api/tasks/<task_id>

Auth: yes
Purpose: soft delete a task
Typical success response fields:
- success
- message
Possible error:
- 404 when task is missing

### GET /api/tasks/<task_id>/history

Auth: yes
Purpose: fetch task history by field
Typical response fields:
- task_id
- history
Possible error:
- 404 when task is missing

### GET /api/scheduled_tasks

Auth: yes
Purpose: list scheduled tasks for the current user
Typical response fields:
- scheduled_tasks
- count

### POST /api/scheduled_tasks

Auth: yes
Purpose: create or update a scheduled task by id
Request content type:
- application/json
Required body fields:
- id: non-empty string
- title: non-empty string
- frequency: non-empty string
Optional body fields:
- priority: string
- urgency: string, default low
- importance: string, default low
- notes: string
- due_date: string
- week_day: integer or null
- month_day: integer or null
- quarter_day: integer or null
- year_month: integer or null
- year_day: integer or null
- next_run_at: string
- active: boolean
Behavior:
- create when id does not exist
- update when id already exists
Typical success response fields:
- success
- action
- task_id

### DELETE /api/scheduled_tasks/<task_id>

Auth: yes
Purpose: delete a scheduled task
Typical success response fields:
- success
- message
Possible error:
- 404 when scheduled task is missing

## Error Format

Errors are returned as JSON with one top-level field:

- error

Common status codes:

- 400 invalid payload, missing required field, or wrong type
- 401 missing or invalid token
- 404 resource not found
- 405 method not allowed
- 409 username or token conflict
- 500 internal server error

## Recommendation

For local access to remote production data, prefer this order:

1. Call the remote HTTP API
2. Sync the remote SQLite files to local
3. Only then consider reading a remotely shared SQLite file directly

The project already exposes business APIs, while direct SQLite file access is more fragile and can hit file locking issues.
