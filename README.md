# Customer Health Score - Agentic AI Application

An AI-powered application that analyzes Slack conversations to generate customer health scores, predict churn, and suggest action items. Built with a multi-agent architecture using Google Gemini AI.

## Features

- **Slack Integration**: Batch-on-demand message processing via Slack API
- **Customer Management**: Create, update, and delete customers with Slack user linking
- **Channel Management**: Sync and monitor Slack channels, link channels to customers
- **Sentiment Analysis**: AI-powered sentiment analysis of customer communications using Google Gemini
- **Health Score Calculation**: Customer health score (1-10) based on sentiment, engagement, and communication patterns
- **Churn Prediction**: Probability-based churn prediction with risk factors
- **Action Items**: AI-generated recommendations to improve customer health
- **Dashboard**: Real-time dashboard with health score trends and at-risk customers
- **Collapsible Sidebar**: Responsive navigation with collapsible sidebar
- **Settings Management**: Configure API keys (Slack and Gemini) through the UI, stored securely in the database

## Tech Stack

- **Backend**: Python FastAPI
- **Frontend**: Next.js 14 with Tailwind CSS
- **Database**: SQLite
- **AI**: Google Gemini
- **Slack**: slack-bolt + Slack SDK
- **Scheduler**: APScheduler

## Project Structure

```
AgenticHealthscore/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Settings & environment variables
│   │   ├── database.py          # Database connection & session management
│   │   ├── models/              # SQLAlchemy models (Customer, Channel, HealthScore, etc.)
│   │   ├── schemas/             # Pydantic schemas for API validation
│   │   ├── api/
│   │   │   ├── deps.py          # API dependencies
│   │   │   └── v1/              # API v1 endpoints
│   │   │       ├── router.py    # Main API router
│   │   │       ├── customers.py # Customer endpoints
│   │   │       ├── channels.py  # Channel endpoints
│   │   │       ├── health_scores.py # Health score endpoints
│   │   │       ├── action_items.py # Action item endpoints
│   │   │       ├── dashboard.py # Dashboard endpoints
│   │   │       └── settings.py  # Settings endpoints
│   │   ├── services/            # Business logic services
│   │   ├── slack/               # Slack integration (API client, bot)
│   │   ├── agents/              # AI agents (sentiment, health score, churn, action items)
│   │   ├── gemini/              # Gemini AI client & prompts
│   │   ├── scheduler/           # Background jobs (scheduled tasks)
│   │   └── utils/               # Utility functions (logging, etc.)
│   ├── alembic/                 # Database migrations
│   ├── tests/                   # Test files
│   ├── requirements.txt         # Python dependencies
│   ├── Dockerfile               # Backend Docker image
│   └── .gitignore              # Backend-specific gitignore
├── frontend/
│   ├── app/                     # Next.js 14 App Router pages
│   │   ├── page.tsx             # Dashboard page
│   │   ├── customers/           # Customer management pages
│   │   ├── channels/            # Channel management page
│   │   ├── health-scores/       # Health scores page
│   │   ├── action-items/        # Action items page
│   │   ├── trends/              # Trends page
│   │   ├── settings/            # Settings page
│   │   └── layout.tsx           # Root layout with Sidebar & Header
│   ├── components/
│   │   ├── layout/              # Layout components (Sidebar, Header)
│   │   ├── dashboard/           # Dashboard-specific components
│   │   └── ui/                  # Reusable UI components
│   ├── lib/
│   │   ├── api.ts               # API client functions
│   │   └── utils.ts             # Utility functions
│   ├── types/                   # TypeScript type definitions
│   ├── package.json             # Node.js dependencies
│   ├── Dockerfile               # Frontend Docker image
│   └── .gitignore               # Frontend-specific gitignore
├── docker-compose.yml           # Docker Compose configuration
├── .env.example                  # Example environment variables
└── README.md                    # This file
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Google API Key (for Gemini) - can be configured in Settings page
- Slack API Token (bot token) - can be configured in Settings page

### 1. Clone and Configure

```bash
cd AgenticHealthscore
cp .env.example .env
# Edit .env with database and other configuration (API keys are set via UI)
```

### 2. Start with Docker

```bash
docker-compose up -d
```

The application will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### 3. Manual Setup (Development)

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Database:**
SQLite database is created automatically on first run. No separate database setup needed.

## Slack API Setup

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app (or use an existing one)
2. Navigate to **OAuth & Permissions** in the sidebar
3. Under **Bot Token Scopes**, add the following scopes:
   - `channels:read` - View basic channel information (required for syncing channels)
   - `channels:history` - Read message history (required for fetching messages)
   - `groups:read` - View private channel information (required for syncing private channels)
   - `mpim:read` - View group direct messages (required for syncing group DMs)
   - `im:read` - View direct messages (required for syncing DMs)
   - `users:read` - View user information (required for user identification)
4. Click **Install to Workspace** to install the app
5. Copy the **Bot User OAuth Token** (starts with `xoxb-`) from the **OAuth & Permissions** page
6. Add it in the **Settings** page of the application (stored securely in the database)

**Important**: After adding scopes, you must reinstall the app to your workspace for the new scopes to take effect.

**Note**: 
- API keys (Slack and Gemini) are stored in the database and can be configured through the Settings page in the UI
- This deployment uses batch-on-demand processing via API calls. Real-time event processing (Socket Mode) is disabled for initial deployment

## API Endpoints

### Customers
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/customers` | List all customers with pagination |
| POST | `/api/v1/customers` | Create a new customer |
| GET | `/api/v1/customers/{id}` | Get customer details |
| PUT | `/api/v1/customers/{id}` | Update customer |
| DELETE | `/api/v1/customers/{id}` | Delete customer |
| GET | `/api/v1/customers/{id}/health-scores` | Get customer health score history |
| GET | `/api/v1/customers/{id}/health-score/latest` | Get latest health score |
| POST | `/api/v1/customers/{id}/health-score/calculate` | Calculate health score for customer (validates channels, fetches recent messages from Slack, then calculates) |

### Channels
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/channels` | List Slack channels |
| POST | `/api/v1/channels/sync` | Sync channels from Slack |
| GET | `/api/v1/channels/{id}` | Get channel details |
| PUT | `/api/v1/channels/{id}` | Update channel (link to customer, toggle monitoring) |
| POST | `/api/v1/channels/{id}/fetch-history` | Fetch message history from Slack |

### Health Scores
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health-scores` | List health scores (latest per customer) |
| GET | `/api/v1/health-scores/{id}` | Get health score by ID |
| POST | `/api/v1/health-scores/calculate-all` | Calculate health scores for all customers (fetches messages from all monitored channels first) |

### Action Items
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/action-items` | List action items with filters |
| GET | `/api/v1/action-items/{id}` | Get action item by ID |
| PATCH | `/api/v1/action-items/{id}/status` | Update action item status |
| PUT | `/api/v1/action-items/{id}` | Update action item |

### Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/dashboard/summary` | Get dashboard statistics |
| GET | `/api/v1/dashboard/at-risk` | Get at-risk customers |
| GET | `/api/v1/dashboard/trends` | Get health score trends |

### Settings
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/settings` | Get application settings |
| PUT | `/api/v1/settings` | Update API keys (Slack and Gemini) |

## Agentic Workflow

The system uses a multi-agent architecture:

1. **Message Fetching**: When calculating a health score, recent messages are automatically fetched from Slack channels linked to the customer. Messages are committed immediately after each channel to ensure visibility and accurate message counts.
2. **Sentiment Agent**: Analyzes message sentiment using Gemini
3. **Health Score Agent**: Calculates health score (1-10) with component breakdown
4. **Churn Prediction Agent**: Predicts churn probability with risk factors
5. **Action Item Agent**: Generates actionable recommendations

The **Orchestrator** coordinates these agents in sequence for each customer analysis. When using the "Recalculate Score" button, the system first fetches fresh messages from Slack before performing the analysis.

### Recent Improvements

- **Transaction Visibility**: Messages are now committed and flushed immediately after each channel fetch, ensuring they're visible to subsequent queries and accurate message counts in the UI
- **Enhanced Error Handling**: Better validation and error messages for missing channels, unmonitored channels, and message fetching failures
- **Improved Logging**: Comprehensive logging throughout the message fetching and health score calculation process for better debugging
- **Message Count Accuracy**: Fixed message count calculation to use actual stored messages (excluding duplicates) rather than raw Slack API responses
- **Type Safety**: Fixed type annotations throughout the codebase (UUID → str for SQLite compatibility)

## Scheduled Tasks

Health scores are automatically calculated daily at 2 AM (configurable via `HEALTH_SCORE_CALCULATION_HOUR`).

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLite connection string | `sqlite+aiosqlite:///./healthscore.db` |
| `GEMINI_MODEL` | Gemini model ID | `gemini-2.0-flash-exp` |
| `CORS_ORIGINS` | Allowed CORS origins (JSON array) | `["http://localhost:3000"]` |
| `ANALYSIS_PERIOD_DAYS` | Default analysis period in days | `30` |
| `MESSAGE_BATCH_SIZE` | Number of messages to process per batch | `50` |
| `HEALTH_SCORE_CALCULATION_HOUR` | Hour of day for scheduled calculations (0-23) | `2` |
| `DEBUG` | Enable debug mode | `False` |
| `SECRET_KEY` | Secret key for application | `change-me-in-production` |

**Note**: `GOOGLE_API_KEY` and `SLACK_API_TOKEN` are now stored in the database and configured through the Settings page in the UI. They are no longer required in the `.env` file.

## Cloud Run Deployment

Deploy to Google Cloud Run using the Cloud Run UI with GitHub integration:

- **Deployment Guide**: See [CLOUD_RUN_UI_DEPLOYMENT.md](CLOUD_RUN_UI_DEPLOYMENT.md)

### Key Points:

1. **Backend**: Deploy from `backend/Dockerfile` with SQLite database
2. **Frontend**: Deploy from `frontend/Dockerfile` with backend URL configured
3. **Environment Variables**: Set `DATABASE_URL` via Cloud Run UI (must point to mounted volume: `sqlite+aiosqlite:///mnt/data/healthscore.db`)
4. **Persistent Storage**: Mount Cloud Storage bucket as volume in Cloud Run UI (much cheaper than Filestore)
5. **Database Path**: Ensure `DATABASE_URL` matches the volume mount path (`/mnt/data`) for proper persistence

### Troubleshooting

**"No messages found" error:**
- Verify channels are linked to customers
- Ensure channels have monitoring enabled
- Check that messages exist in the selected time period
- Verify `DATABASE_URL` points to the mounted volume path
- Check Cloud Run logs for detailed error messages

**Message counts not updating:**
- Messages are now committed immediately after each channel fetch
- Refresh the channels page to see updated counts
- Verify database path is correctly configured

## License

MIT
