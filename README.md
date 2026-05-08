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

## Quick Start (Docker)

1. Clone the repository.
2. Copy `.env.example` to `.env` and fill in the required values (see Environment Variables below).
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

In a separate terminal, from the `backend` directory:
