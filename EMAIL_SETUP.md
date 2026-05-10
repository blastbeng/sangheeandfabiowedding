# Email Setup Guide

This guide explains how to configure the email backend for the Wedding Web App. Email is used for user registration verification, password resets, and other notifications.

## Environment Variables

The following environment variables control the email configuration. Add these to your `.env` file.

| Variable | Description | Example |
|----------|-------------|---------|
| `EMAIL_BACKEND` | The Django email backend to use. | `django.core.mail.backends.console.EmailBackend` (dev) / `django.core.mail.backends.smtp.EmailBackend` (prod) |
| `EMAIL_HOST` | The SMTP server host. | `smtp.gmail.com` |
| `EMAIL_PORT` | The SMTP server port. | `587` |
| `EMAIL_USE_TLS` | Whether to use TLS encryption. | `True` |
| `EMAIL_HOST_USER` | The username for the SMTP server. | `your-email@gmail.com` |
| `EMAIL_HOST_PASSWORD` | The password for the SMTP server. | `your-app-password` |
| `DEFAULT_FROM_EMAIL` | The default email address for outgoing messages. | `noreply@sangheeandfabio.com` |

## Local Development

For local development, it is easiest to use the console email backend. This will print all sent emails directly to the console instead of sending them over the network.

1. Open your `.env` file.
2. Set the `EMAIL_BACKEND` variable to the console backend:
   ```env
   EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
   ```
3. Leave the other `EMAIL_*` variables with their placeholder values. They are not used by the console backend.

When the application sends an email (e.g., during registration), you will see the email content printed in the Django console output.

## Production Setup (SMTP)

For production, you must configure a real SMTP server to deliver emails to users.

### Using a Standard SMTP Provider

1. Obtain SMTP credentials from your email provider (e.g., Gmail, SendGrid, Mailgun, Amazon SES).
2. Update your `.env` file with the provider's details:

   ```env
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.your-provider.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your-smtp-username
   EMAIL_HOST_PASSWORD=your-smtp-password
   DEFAULT_FROM_EMAIL=noreply@sangheeandfabio.com
   ```

3. Restart the application for the changes to take effect.

### Example: Gmail

If you are using Gmail, you can use the following configuration. Note that you must create an "App Password" if you have 2-Factor Authentication enabled on your Google account.

1. Go to your Google Account settings.
2. Navigate to **Security** > **2-Step Verification** > **App passwords**.
3. Create a new app password for "Mail" on your device.
4. Update your `.env` file:

   ```env
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=your-16-digit-app-password
   DEFAULT_FROM_EMAIL=your-email@gmail.com
   ```

> **Note:** Never commit your real SMTP passwords to version control. Always use environment variables or a secure secrets manager.
