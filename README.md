# Reflections

A simple, clean calendar app for daily journaling with scores (0-10) and reflections. Features a Chess.com-inspired color system where scores create a visual spectrum from dark red (blunder days) to bright blue (brilliant days).

## Features

- **Daily Reflections**: Rate your day 0-10 and add a short reflection (max 200 chars)
- **Visual Calendar**: See your month at a glance with color-coded days
- **Chess.com Colors**: Inspired by move analysis - blunder (red) to brilliant (blue)
- **Clean API**: RESTful endpoints for future integrations and insights
- **PWA Support**: Install on iOS/Android home screen
- **Responsive**: Works great on desktop and mobile

## Color Scale

| Score | Color | Meaning |
|-------|-------|---------|
| 0 | Dark Red | Blunder |
| 1-2 | Red | Mistake |
| 3-4 | Orange | Inaccuracy |
| 5 | Gray | Neutral/Book |
| 6-7 | Light Teal | Good |
| 8-9 | Teal | Great |
| 10 | Bright Blue | Brilliant |

## Quick Start

### Prerequisites

- Python 3.11+
- pip

### Installation

```bash
# Clone the repository
cd calendar_app

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env and set a secure SECRET_KEY for production

# Run the app
uvicorn app.main:app --reload
```

Open http://localhost:8000 in your browser.

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Get JWT token |
| GET | `/api/auth/me` | Get current user |
| POST | `/api/auth/logout` | Clear session |
| DELETE | `/api/auth/account` | Delete account |

### Day Entries

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/entries` | List entries (filterable) |
| GET | `/api/entries/{date}` | Get single day |
| POST | `/api/entries` | Create entry |
| PUT | `/api/entries/{date}` | Update entry |
| DELETE | `/api/entries/{date}` | Delete entry |

#### Query Parameters for `/api/entries`

- `start_date`: Filter from date (YYYY-MM-DD)
- `end_date`: Filter to date (YYYY-MM-DD)
- `min_score`: Minimum score filter (0-10)
- `max_score`: Maximum score filter (0-10)

### Example API Usage

```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secret123"}'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -d "username=user@example.com&password=secret123"

# Create entry (with token)
curl -X POST http://localhost:8000/api/entries \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"date": "2026-01-03", "score": 8, "summary": "Great productive day!"}'

# Get entries for a date range
curl "http://localhost:8000/api/entries?start_date=2026-01-01&end_date=2026-01-31" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: HTMX + Jinja2 templates
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Auth**: JWT with bcrypt password hashing
- **ORM**: SQLAlchemy (async)

## Project Structure

```
calendar_app/
├── app/
│   ├── main.py           # FastAPI app entry
│   ├── config.py         # Settings (env vars)
│   ├── database.py       # SQLAlchemy setup
│   ├── models.py         # User, DayEntry models
│   ├── schemas.py        # Pydantic schemas
│   ├── auth.py           # JWT utilities
│   ├── routers/
│   │   ├── auth.py       # Auth endpoints
│   │   ├── entries.py    # Entry CRUD API
│   │   └── pages.py      # HTML page routes
│   └── templates/        # Jinja2 templates
├── static/
│   ├── css/style.css     # Styles
│   ├── manifest.json     # PWA manifest
│   └── sw.js             # Service worker
├── requirements.txt
└── .env.example
```

## iOS/Mobile Installation (PWA)

1. Open the app in Safari on iOS
2. Tap the Share button
3. Tap "Add to Home Screen"
4. The app will work like a native app!

## Production Deployment

1. Set `DEBUG=False` in `.env`
2. Generate a secure `SECRET_KEY`
3. Use PostgreSQL instead of SQLite
4. Deploy with Gunicorn + Uvicorn workers:

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## Future Ideas

- Weekly/monthly insights and statistics
- Streak tracking
- Export data (CSV/JSON)
- Tags/categories for entries
- Year-in-review visualization
- Mood pattern analysis
- API webhooks for integrations

## License

MIT

