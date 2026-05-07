# Health Data Management Application

A modern health data management application built with FastAPI, Vite + React, and PostgreSQL. The application stores flexible JSONB health measurements and dynamically renders them based on the stored data structure.

## Features

- **Flexible Data Storage**: Accepts any JSON structure and stores it in PostgreSQL JSONB
- **Dynamic Rendering**: Automatically detects and renders common health metrics (BMI, blood pressure, heart rate, etc.)
- **Modern UI**: Beautiful, responsive interface matching the provided mockups
- **Dark Mode**: Full dark mode support
- **Docker Compose**: Complete containerized setup

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Vite      │────▶│   FastAPI    │────▶│ PostgreSQL  │
│  (React)    │     │   (Python)   │     │  (JSONB)    │
└─────────────┘     └──────────────┘     └─────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Ports 5173 (frontend), 8000 (backend), and 5432 (postgres) available

### Running the Application

1. **Clone/Navigate to the project directory**:
   ```bash
   cd health-data-app
   ```

2. **Start all services**:
   ```bash
   docker-compose up --build
   ```

3. **Access the application**:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### First Run

The database tables will be created automatically on first startup. You can start using the application immediately.

## API Endpoints

### Health Data

- `GET /health-data/receive-measurement` - List all measurements (with pagination)
  - Query params: `page`, `page_size`, `patient_id`
- `POST /health-data/receive-measurement` - Create new measurement
  - Body: `{ "patient_id": "NDT-98241", "kiosk_location": "Station A1", "measurement_data": {...} }`
- `GET /health-data/receive-measurement/{id}` - Get single measurement
- `GET /health-data/stats` - Get statistics (BMI categories, counts)

### Example POST Request

```json
{
  "patient_id": "NDT-98241",
  "kiosk_location": "Station Santé A1",
  "measurement_data": {
    "height": 178,
    "weight": 76.5,
    "blood_pressure": "122/81",
    "heart_rate": 72
  }
}
```

The `measurement_data` field accepts **any JSON structure**, making it completely flexible.

## Project Structure

```
health-data-app/
├── docker-compose.yml
├── README.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py              # FastAPI app
│       ├── database.py           # DB connection
│       ├── models.py             # SQLAlchemy models
│       ├── schemas.py            # Pydantic schemas
│       └── routers/
│           └── health_data.py    # API endpoints
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.jsx
        ├── components/
        │   ├── Dashboard.jsx     # List view
        │   ├── ReportDetail.jsx  # Detail view
        │   ├── MeasurementForm.jsx
        │   └── DynamicField.jsx   # Dynamic renderer
        ├── services/
        │   └── api.js            # API client
        └── styles/
            └── index.css
```

## Development

### Backend Development

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

## Data Structure Flexibility

The application is designed to handle any JSON structure. The frontend intelligently detects common health metrics:

- **Known metrics**: Height, weight, BMI, blood pressure, heart rate → Special formatting
- **Unknown fields**: Rendered as generic key-value pairs
- **Nested objects**: Recursively rendered
- **Arrays**: Displayed as lists

## Environment Variables

The application uses the following environment variables (set in docker-compose.yml):

- `DATABASE_URL`: PostgreSQL connection string
- `CORS_ORIGINS`: Allowed CORS origins (comma-separated)
- `VITE_API_URL`: Backend API URL for frontend

## Database

The application uses PostgreSQL with a single table:

```sql
health_measurements
- id (UUID, primary key)
- patient_id (String, nullable)
- kiosk_location (String, nullable)
- measurement_data (JSONB, required)
- created_at (Timestamp)
- updated_at (Timestamp)
```

## Troubleshooting

### Port conflicts
If ports are already in use, modify `docker-compose.yml` to use different ports.

### Database connection issues
Ensure PostgreSQL container is healthy before starting backend:
```bash
docker-compose ps
```

### Frontend not connecting to backend
Check that `VITE_API_URL` in docker-compose.yml matches your backend URL.

## License

MIT
