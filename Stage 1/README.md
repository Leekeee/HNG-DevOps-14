# Stage 1 API

A minimal REST API built with Node.js/Express, deployed on a VPS behind Nginx.

## Run Locally

```bash
npm install
node index.js
```

API runs on `http://localhost:3000`

## Endpoints

| Method | Path      | Response                                              |
|--------|-----------|-------------------------------------------------------|
| GET    | `/`       | `{"message": "API is running"}`                       |
| GET    | `/health` | `{"message": "healthy"}`                              |
| GET    | `/me`     | `{"name": "...", "email": "...", "github": "..."}`    |

All endpoints return `Content-Type: application/json` and HTTP 200.

## Live URL

http://your-server-ip-or-domain
