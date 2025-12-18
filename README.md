# Customer Health Score - Agentic AI Application

An AI-powered application that analyzes Slack conversations to generate customer health scores, predict churn, and suggest action items. Built with a multi-agent architecture using Google Gemini AI.

## Features

- **Authentication**: Complete email-based and OAuth (Google) authentication system
  - Email signup with verification
  - Secure password management with bcrypt hashing
  - OAuth 2.0 support (Google)
  - JWT-based session management
  - Route protection and user context
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
│   │   ├── models/              # SQLAlchemy models (Customer, Channel, HealthScore, User, VerificationToken, etc.)
│   │   ├── schemas/             # Pydantic schemas for API validation (including auth schemas)
│   │   ├── api/
│   │   │   ├── deps.py          # API dependencies (including auth dependencies)
│   │   │   └── v1/              # API v1 endpoints
│   │   │       ├── router.py    # Main API router
│   │   │       ├── auth.py      # Authentication endpoints (signup, login, verify, OAuth)
│   │   │       ├── customers.py # Customer endpoints
│   │   │       ├── channels.py  # Channel endpoints
│   │   │       ├── health_scores.py # Health score endpoints
│   │   │       ├── action_items.py # Action item endpoints
│   │   │       ├── dashboard.py # Dashboard endpoints
│   │   │       └── settings.py  # Settings endpoints
│   │   ├── services/            # Business logic services
│   │   │   ├── auth_service.py  # Authentication service (user management, password hashing)
│   │   │   ├── email_service.py # Email service (verification emails, notifications)
│   │   │   └── oauth_service.py # OAuth service (Google OAuth integration)
│   │   ├── utils/
│   │   │   └── jwt.py           # JWT token utilities
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
│   │   ├── auth/                # Authentication pages
│   │   │   ├── login/           # Login page
│   │   │   ├── signup/          # Signup page
│   │   │   ├── verify/          # Email verification page
│   │   │   ├── set-password/   # Password setup page
│   │   │   └── oauth/           # OAuth callback page
│   │   ├── customers/           # Customer management pages
│   │   ├── channels/            # Channel management page
│   │   ├── health-scores/       # Health scores page
│   │   ├── action-items/        # Action items page
│   │   ├── trends/              # Trends page
│   │   ├── settings/            # Settings page
│   │   └── layout.tsx           # Root layout with Sidebar & Header (includes AuthProvider)
│   ├── components/
│   │   ├── auth/                # Authentication components
│   │   │   ├── AuthProvider.tsx # Auth context provider
│   │   │   └── AuthGuard.tsx    # Route protection component
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
- SMTP Configuration (for email verification) - can be configured via setup script or database
- OAuth Credentials (optional, for Google OAuth) - can be configured in database

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

## Authentication Setup

### Email-Based Authentication

1. **Configure SMTP Settings**: Use the setup script to configure SMTP for email verification:
   ```bash
   cd backend
   python scripts/setup_smtp.py
   ```
   Or configure directly in the database via `AppConfig`:
   - `SMTP_HOST`: SMTP server hostname (e.g., `smtp.gmail.com`)
   - `SMTP_PORT`: SMTP port (e.g., `587` for STARTTLS or `465` for SSL)
   - `SMTP_USER`: SMTP username (your email)
   - `SMTP_PASSWORD`: SMTP password (for Gmail, use an App Password)
   - `SMTP_FROM_EMAIL`: Sender email address
   - `SMTP_USE_TLS`: `true` for STARTTLS (port 587) or SSL (port 465)

2. **User Flow**:
   - User signs up with email address
   - Verification email sent with secure, time-limited link (expires in 1 hour)
   - User clicks link to verify email
   - User sets password
   - User can now log in

3. **Admin Notifications**: New user signups trigger notification emails to the admin email configured in `ADMIN_NOTIFICATION_EMAIL`.

### OAuth Authentication (Google)

1. **Configure OAuth Credentials**:
   - Create OAuth 2.0 credentials in [Google Cloud Console](https://console.cloud.google.com/)
   - Add authorized redirect URI: `http://localhost:8000/api/v1/auth/oauth/google/callback` (for development)
   - Store credentials in database via `AppConfig`:
     - `GOOGLE_OAUTH_CLIENT_ID`: Your Google OAuth client ID
     - `GOOGLE_OAUTH_CLIENT_SECRET`: Your Google OAuth client secret

2. **User Flow**:
   - User clicks "Sign in with Google"
   - Redirected to Google for authentication
   - User grants permissions
   - Redirected back to application with JWT token
   - User is automatically logged in (no email verification or password required)

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/signup` | Sign up with email address |
| GET | `/api/v1/auth/verify` | Verify email address with token |
| POST | `/api/v1/auth/set-password` | Set password after email verification |
| POST | `/api/v1/auth/login` | Login with email and password |
| GET | `/api/v1/auth/oauth/{provider}` | Initiate OAuth flow (e.g., `google`) |
| GET | `/api/v1/auth/oauth/{provider}/callback` | OAuth callback endpoint |
| GET | `/api/v1/auth/me` | Get current authenticated user |

### Security Features

- **Password Hashing**: Bcrypt with 12 rounds, handles passwords > 72 bytes via SHA256 pre-hashing
- **JWT Tokens**: Secure session management with configurable expiration (default: 24 hours)
- **Email Verification**: Single-use, time-limited tokens (1 hour expiry)
- **OAuth Integration**: Secure OAuth 2.0 flow with state parameter for CSRF protection
- **Route Protection**: Frontend route guards and backend JWT validation

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

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/signup` | Sign up with email address |
| GET | `/api/v1/auth/verify` | Verify email address with token |
| POST | `/api/v1/auth/set-password` | Set password after email verification |
| POST | `/api/v1/auth/login` | Login with email and password |
| GET | `/api/v1/auth/oauth/{provider}` | Initiate OAuth flow (e.g., `google`) |
| GET | `/api/v1/auth/oauth/{provider}/callback` | OAuth callback endpoint |
| GET | `/api/v1/auth/me` | Get current authenticated user (requires authentication) |

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
| `JWT_SECRET_KEY` | Secret key for JWT token signing | `change-me-in-production-jwt` |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token expiration in minutes | `1440` (24 hours) |
| `VERIFICATION_TOKEN_EXPIRY_HOURS` | Email verification token expiration in hours | `1` |
| `ADMIN_NOTIFICATION_EMAIL` | Email address for new user signup notifications | `dinesh.katiyar@trustassist.ai` |
| `FRONTEND_URL` | Frontend URL for email links and redirects | `http://localhost:3000` |
| `BACKEND_URL` | Backend URL for OAuth callbacks | `http://localhost:8000` |

**Note**: 
- `GOOGLE_API_KEY` and `SLACK_API_TOKEN` are stored in the database and configured through the Settings page in the UI
- SMTP settings (for email verification) are stored in the database and can be configured via `scripts/setup_smtp.py` or directly in the database
- OAuth credentials (Google) are stored in the database and can be configured via `AppConfig` service

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
