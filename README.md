# Sang Hee & Fabio - Wedding Web App

A responsive multilingual web platform for managing a wedding event, focused on sharing multimedia memories between spouses and guests. Guests can upload photos and videos during the event, which are stored simultaneously on Nextcloud and Google Drive, with a Redis cache for fast delivery.

## Tech Stack

- **Backend:** Django 5.0, Django REST Framework, Celery, Redis
- **Frontend:** React 18, Vite, Tailwind CSS, i18next
- **Database:** PostgreSQL 15
- **Task Queue:** Celery with Redis broker
- **Storage:** Nextcloud (WebDAV) + Google Drive (API)
- **Cache:** Redis (max 1 GB, LRU eviction)
- **Authentication:** JWT (SimpleJWT), django-allauth (Facebook, Instagram), Google OAuth2
- **Deployment:** Docker Compose, Nginx reverse proxy

## Features

- Multilingual support (Italian, Korean, English)
- User registration with email verification
- Social login via Google, Facebook, Instagram
- Media upload (photos/videos) with asynchronous processing
- Dual cloud storage (Nextcloud + Google Drive) with atomic rollback
- Redis caching for frequently viewed media
- Admin panel with dashboard, user management, site settings
- Moderation workflow: approve/reject single or bulk uploads
- Public gallery with filters (user, date, search)
- Private "My Uploads" section showing approval status
- Profile management (picture, username, password)
- Password reset flow
- Responsive design (mobile-friendly)

## Prerequisites

- Docker and Docker Compose (for containerized deployment)
- Python 3.11+ (for local development)
- Node.js 18+ and npm (for frontend development)
- PostgreSQL 15 (if running services locally)
- Redis (if running services locally)

## Environment Variables

Copy `.env.example` to `.env` and fill in all required values. The following variables are used:

| Variable | Description | Required |
|----------|-------------|----------|
| `POSTGRES_DB` | PostgreSQL database name | Yes |
| `POSTGRES_USER` | PostgreSQL username | Yes |
| `POSTGRES_PASSWORD` | PostgreSQL password | Yes |
| `DJANGO_SECRET_KEY` | Django secret key | Yes |
| `DEBUG` | Debug mode (`1` for True, `0` for False) | Yes |
| `ADMIN_USERNAME` | Default admin username | Yes |
| `ADMIN_PASSWORD` | Default admin password | Yes |
| `ADMIN_EMAIL` | Default admin email | Yes |
| `FRONTEND_URL` | Frontend URL (used for email links) | Yes |
| `GOOGLE_CLIENT_ID` | Google OAuth2 client ID (social login) | Yes |
| `GOOGLE_CLIENT_SECRET` | Google OAuth2 client secret | Yes |
| `FACEBOOK_APP_ID` | Facebook app ID | Yes |
| `FACEBOOK_APP_SECRET` | Facebook app secret | Yes |
| `INSTAGRAM_APP_ID` | Instagram app ID | Yes |
| `INSTAGRAM_APP_SECRET` | Instagram app secret | Yes |
| `NEXTCLOUD_URL` | Nextcloud base URL | Yes |
| `NEXTCLOUD_USERNAME` | Nextcloud username | Yes |
| `NEXTCLOUD_PASSWORD` | Nextcloud password | Yes |
| `NEXTCLOUD_FOLDER` | Nextcloud upload folder path | Yes |
| `GOOGLE_DRIVE_CLIENT_ID` | Google Drive API client ID | Yes |
| `GOOGLE_DRIVE_CLIENT_SECRET` | Google Drive API client secret | Yes |
| `GOOGLE_DRIVE_TOKEN` | Google Drive OAuth2 token | Yes |
| `GOOGLE_DRIVE_FOLDER_ID` | Google Drive folder ID for uploads | Yes |
| `REDIS_HOST` | Redis hostname (default: `redis`) | Yes |
| `REDIS_PORT` | Redis port (default: `6379`) | Yes |
| `TIME_ZONE` | Time zone (e.g., `Europe/Rome`) | Yes |
| `DEFAULT_LANGUAGE` | Default language code (e.g., `it`) | Yes |
| `EMAIL_BACKEND` | Django email backend | Yes |
| `EMAIL_HOST` | SMTP server host | Yes |
| `EMAIL_PORT` | SMTP server port | Yes |
| `EMAIL_USE_TLS` | Use TLS for email (`True`/`False`) | Yes |
| `EMAIL_HOST_USER` | SMTP username | Yes |
| `EMAIL_HOST_PASSWORD` | SMTP password | Yes |
| `DEFAULT_FROM_EMAIL` | Sender email address | Yes |
| `VITE_API_URL` | API base URL for frontend (empty for relative) | Yes |
| `VITE_GOOGLE_CLIENT_ID` | Google OAuth2 client ID for frontend | Yes |
| `VITE_DEFAULT_LANGUAGE` | Default language for frontend | Yes |
| `VITE_SUPPORTED_LANGUAGES` | Comma-separated supported languages | Yes |
| `LOG_LEVEL` | Backend log level (e.g., `INFO`) | Yes |
| `VITE_LOG_LEVEL` | Frontend log level (e.g., `error`) | Yes |

Refer to `.env.example` for the exact variable names and default values.

## Setting Up Social Authentication

This guide walks you through creating the necessary credentials for Google, Facebook, and Instagram social login. You will need these values to fill in the corresponding environment variables in your `.env` file.

### Google OAuth2

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one.
3. Navigate to **APIs & Services** > **Credentials**.
4. Click **Create Credentials** > **OAuth client ID**.
5. If prompted, configure the **OAuth consent screen**:
   - Choose **External** (or Internal if you have a Google Workspace organization).
   - Fill in the app name, user support email, and developer contact information.
   - Add the scopes `email`, `profile`, and `openid` (these are usually pre-selected).
   - Add your email as a test user if the app is in testing mode.
6. After the consent screen is configured, return to **Credentials** and create an **OAuth client ID**.
7. Select **Web application** as the application type.
8. Add a name (e.g., "Wedding Web App").
9. Under **Authorized redirect URIs**, add:
   - For local development: `http://localhost:5232/accounts/google/login/callback/`
   - For production: `https://yourdomain.com/accounts/google/login/callback/`
10. Click **Create**. You will receive a **Client ID** and **Client Secret**.
11. Copy these values into your `.env` file:
    ```
    GOOGLE_CLIENT_ID=your-client-id
    GOOGLE_CLIENT_SECRET=your-client-secret
    ```

### Facebook Login

1. Go to the [Facebook for Developers](https://developers.facebook.com/) portal.
2. Create a new app or use an existing one. Choose **Consumer** as the app type.
3. In the app dashboard, go to **Settings** > **Basic**.
4. Note the **App ID** and **App Secret** (you may need to reveal the secret).
5. Add the **Facebook Login** product to your app:
   - In the left sidebar, click **Add Product** and choose **Facebook Login**.
   - Select **Web** as the platform.
6. Configure the **Valid OAuth Redirect URIs**:
   - For local development: `http://localhost:5232/accounts/facebook/login/callback/`
   - For production: `https://yourdomain.com/accounts/facebook/login/callback/`
7. Save changes.
8. Copy the App ID and App Secret into your `.env` file:
   ```
   FACEBOOK_APP_ID=your-app-id
   FACEBOOK_APP_SECRET=your-app-secret
   ```

### Instagram Login

Instagram login uses the **Instagram Basic Display API**, which is managed through a Facebook app.

1. Ensure you have a Facebook app (see the Facebook section above). You can use the same app.
2. In the Facebook app dashboard, go to **Add Product** and select **Instagram Basic Display**.
3. Configure the **Instagram Basic Display** settings:
   - Set the **Valid OAuth Redirect URIs**:
     - For local development: `http://localhost:5232/accounts/instagram/login/callback/`
     - For production: `https://yourdomain.com/accounts/instagram/login/callback/`
   - Add the required **Deauthorize Callback URL** (optional, can be left blank).
   - Add a **Privacy Policy URL** (required for going live).
4. Under **Instagram Basic Display** > **Basic Display**, you will find the **Instagram App ID** and **Instagram App Secret**.
5. Copy these values into your `.env` file:
   ```
   INSTAGRAM_APP_ID=your-instagram-app-id
   INSTAGRAM_APP_SECRET=your-instagram-app-secret
   ```

> **Note:** For local testing, you may need to add `localhost` as a valid domain in the Facebook app settings (under **Settings** > **Basic** > **App Domains**) and ensure your redirect URIs use `http://localhost`. For production, replace `localhost` with your actual domain and use `https`.

## Quick Start (Docker)

1. Clone the repository.
2. Copy `.env.example` to `.env` and fill in the required values (see Environment Variables above).
3. Run:
   ```bash
   docker-compose up -d
   ```
4. Access the app at `http://localhost:5232`.
5. Default admin credentials: `admin` / `admin$` (change immediately).

## Local Development

### Backend

1. Create a Python virtual environment and install dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
2. Set environment variables (or use a `.env` file in the backend directory).
3. Run migrations:
   ```bash
   python manage.py migrate
   ```
4. Create the default admin:
   ```bash
   python manage.py create_default_admin
   ```
5. Create social apps (for Facebook/Instagram):
   ```bash
   python manage.py create_social_apps
   ```
6. Start the development server:
   ```bash
   python manage.py runserver 0.0.0.0:8032
   ```

### Frontend

1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```
2. Set `VITE_API_URL=http://localhost:8032` in `.env` (or environment).
3. Start the Vite dev server:
   ```bash
   npm run dev
   ```
4. Access the frontend at `http://localhost:5173`.

### Celery Worker

 - In a separate terminal, from the `backend` directory:
   ```celery -A config beat -l info```

 - For periodic tasks (if any), also run:
   ```celery -A config worker -l info```

## API Endpoints

### Authentication
- `POST /api/auth/register/` – Register new user
- `GET /api/auth/verify-email/?token=...` – Verify email
- `POST /api/auth/login/` – Obtain JWT tokens
- `POST /api/auth/logout/` – Blacklist refresh token
- `POST /api/auth/password-reset/` – Request password reset email
- `POST /api/auth/password-reset/<uidb64>/<token>/` – Confirm password reset
- `POST /api/auth/social/login/` – Exchange Google access token for JWT
- `GET /api/auth/social/facebook/` – Initiate Facebook OAuth2 flow
- `GET /api/auth/social/instagram/` – Initiate Instagram OAuth2 flow
- `GET /api/auth/social/callback/` – OAuth2 callback (returns JWT in query params)

### Profile
- `GET /api/auth/profile/` – Get current user profile
- `PUT /api/auth/profile/` – Update profile (including profile picture)

### Media (User)
- `POST /api/auth/media/upload/` – Upload files (multipart/form-data)
- `DELETE /api/auth/media/<media_id>/` – Delete own media
- `GET /api/auth/media/my-uploads/` – List own uploads with status
- `GET /api/auth/media/<media_id>/file/` – Serve media file (public, cached)

### Public Gallery
- `GET /api/auth/media/public/` – List approved media with filters (`user_id`, `date_from`, `date_to`, `search`)

### Admin
- `GET /api/auth/admin/dashboard/` – Dashboard statistics
- `GET /api/auth/admin/settings/` – Get site settings
- `PUT /api/auth/admin/settings/` – Update site settings
- `GET /api/auth/admin/users/` – List all users
- `POST /api/auth/admin/users/` – Create user
- `GET /api/auth/admin/users/<user_id>/` – Get user details
- `PUT /api/auth/admin/users/<user_id>/` – Update user
- `DELETE /api/auth/admin/users/<user_id>/` – Delete user
- `POST /api/auth/admin/users/<user_id>/toggle-staff/` – Toggle staff status
- `GET /api/auth/media/moderation/` – List media for moderation (filters: `status`, `media_type`)
- `PATCH /api/auth/media/moderation/<media_id>/` – Approve/reject single media
- `POST /api/auth/media/moderation/bulk/` – Bulk approve/reject

### Task Status
- `GET /api/auth/task/<task_id>/` – Check Celery task status

## Deployment

The application is fully containerized. For production:

1. Set `DEBUG=0` and generate a strong `DJANGO_SECRET_KEY`.
2. Configure `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS` with your domain.
3. Use a production-grade PostgreSQL and Redis instance.
4. Set up HTTPS (e.g., via Let's Encrypt) and update Nginx configuration accordingly.
5. Change the default admin password immediately after first login.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request. Ensure code follows existing style and includes appropriate tests.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
