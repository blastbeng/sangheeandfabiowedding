
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
