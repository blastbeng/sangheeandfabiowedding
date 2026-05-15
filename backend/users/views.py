import logging
import os
import uuid
import base64
import re
import requests
import redis
from io import BytesIO
from datetime import timedelta
from urllib.parse import quote
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.contrib.auth import get_user_model, login, logout, authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.exceptions import ValidationError
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings as django_settings
from django.http import HttpResponse, Http404
from dotenv import load_dotenv, set_key
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from allauth.socialaccount.models import SocialAccount
from celery.result import AsyncResult
from .models import Media, SiteSettings, FaceGroup, FaceTag, CookieConsent
from .serializers import (
    CustomUserSerializer, MediaSerializer, MediaModerationSerializer,
    AdminUserSerializer, SiteSettingsSerializer, BulkModerationSerializer,
    PublicMediaSerializer, PublicUserSerializer, FaceGroupSerializer,
    FaceTagSerializer,
    CookieConsentSerializer
)
from .cloud_clients import get_file_from_cloud, NextcloudClient
from .tasks import upload_media_task, delete_media_task, detect_faces_task
from .utils import process_profile_picture
from .rate_limit import check_rate_limit, record_failed_attempt

logger = logging.getLogger(__name__)
User = get_user_model()

ENV_MAPPING = {
    'google_client_id': 'GOOGLE_CLIENT_ID',
    'google_client_secret': 'GOOGLE_CLIENT_SECRET',
    'facebook_app_id': 'FACEBOOK_APP_ID',
    'facebook_app_secret': 'FACEBOOK_APP_SECRET',
    'instagram_app_id': 'INSTAGRAM_APP_ID',
    'instagram_app_secret': 'INSTAGRAM_APP_SECRET',
    'nextcloud_url': 'NEXTCLOUD_URL',
    'nextcloud_username': 'NEXTCLOUD_USERNAME',
    'nextcloud_password': 'NEXTCLOUD_PASSWORD',
    'nextcloud_folder': 'NEXTCLOUD_FOLDER',
    'email_host': 'EMAIL_HOST',
    'email_port': 'EMAIL_PORT',
    'email_use_tls': 'EMAIL_USE_TLS',
    'email_host_user': 'EMAIL_HOST_USER',
    'email_host_password': 'EMAIL_HOST_PASSWORD',
    'default_from_email': 'DEFAULT_FROM_EMAIL',
}


# Email translations
_EMAIL_TRANSLATIONS = {
    'en': {
        'subject': "Verify your email for SangHee & Fabio's Wedding",
        'header': "💕 SangHee & Fabio's Wedding 💕",
        'welcome': "Welcome to our wedding celebration!",
        'body': "Please verify your email address to activate your account and start sharing beautiful memories with us.",
        'button': "Verify Email Address",
        'after_button': "After you verify your email, an administrator will activate your account. You will then be able to log in.",
        'ignore': "If you didn't create an account, you can safely ignore this email.",
        'footer': f"&copy; {timezone.now().year} SangHee & Fabio's Wedding. All rights reserved.",
    },
    'it': {
        'subject': "Verifica la tua email per il Matrimonio di SangHee & Fabio",
        'header': "💕 Matrimonio di SangHee & Fabio 💕",
        'welcome': "Benvenuti alla nostra celebrazione di nozze!",
        'body': "Verifica il tuo indirizzo email per attivare il tuo account e iniziare a condividere bellissimi ricordi con noi.",
        'button': "Verifica Indirizzo Email",
        'after_button': "Dopo aver verificato la tua email, un amministratore attiverà il tuo account. Potrai quindi accedere.",
        'ignore': "Se non hai creato un account, puoi ignorare questa email.",
        'footer': f"&copy; {timezone.now().year} Matrimonio di SangHee & Fabio. Tutti i diritti riservati.",
    },
    'ko': {
        'subject': "SangHee & Fabio의 결혼식을 위한 이메일 인증",
        'header': "💕 SangHee & Fabio의 결혼식 💕",
        'welcome': "저희 결혼식에 오신 것을 환영합니다!",
        'body': "계정을 활성화하고 아름다운 추억을 공유하려면 이메일 주소를 인증해 주세요.",
        'button': "이메일 인증",
        'after_button': "이메일 인증 후 관리자가 계정을 활성화할 것입니다. 그 후에 로그인할 수 있습니다.",
        'ignore': "계정을 생성하지 않으셨다면 이 이메일을 무시하셔도 됩니다.",
        'footer': f"&copy; {timezone.now().year} SangHee & Fabio의 결혼식. 모든 권리 보유.",
    }
}


def _get_email_subject(language):
    return _EMAIL_TRANSLATIONS.get(language, _EMAIL_TRANSLATIONS['en'])['subject']


def sanitize_username(raw_username):
    """
    Replace any character that is not alphanumeric or one of @ . + - _ with underscore.
    Returns a non-empty string suitable as a Django username.
    """
    sanitized = re.sub(r'[^a-zA-Z0-9@.+\-_]', '_', raw_username)
    sanitized = sanitized.strip('_')
    if not sanitized:
        sanitized = 'user'
    return sanitized


def build_verification_email(verification_url, site_name="SangHee & Fabio's Wedding", language='en'):
    t = _EMAIL_TRANSLATIONS.get(language, _EMAIL_TRANSLATIONS['en'])
    return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0; padding:0; background-color:#fdf2f8; font-family: 'Georgia', serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#fdf2f8; padding: 40px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
          <!-- Header -->
          <tr>
            <td style="background: linear-gradient(135deg, #f9a8d4, #f472b6); padding: 30px; text-align: center;">
              <h1 style="color: #ffffff; margin: 0; font-size: 28px;">{t['header']}</h1>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding: 40px 30px; text-align: center; color: #4b5563;">
              <p style="font-size: 18px; margin-bottom: 20px;">{t['welcome']}</p>
              <p style="font-size: 16px; line-height: 1.6; margin-bottom: 30px;">
                {t['body']}
              </p>
              <a href="{verification_url}" style="display: inline-block; background-color: #ec4899; color: #ffffff; text-decoration: none; padding: 14px 36px; border-radius: 30px; font-size: 16px; font-weight: bold; margin-bottom: 30px;">{t['button']}</a>
              <p style="font-size: 14px; color: #6b7280; margin-top: 20px;">
                {t['after_button']}
              </p>
              <p style="font-size: 14px; color: #9ca3af;">
                {t['ignore']}
              </p>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="background-color: #fce7f3; padding: 20px; text-align: center; font-size: 12px; color: #9ca3af;">
              {t['footer']}
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def reload_django_settings():
    """Reload .env into os.environ and update django.conf.settings."""
    env_path = os.path.join(django_settings.BASE_DIR, '.env')
    if not os.path.exists(env_path):
        env_path = os.path.join(django_settings.BASE_DIR.parent, '.env')
    load_dotenv(dotenv_path=env_path, override=True)
    django_settings.GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
    django_settings.GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    django_settings.FACEBOOK_APP_ID = os.environ.get('FACEBOOK_APP_ID', '')
    django_settings.FACEBOOK_APP_SECRET = os.environ.get('FACEBOOK_APP_SECRET', '')
    django_settings.INSTAGRAM_APP_ID = os.environ.get('INSTAGRAM_APP_ID', '')
    django_settings.INSTAGRAM_APP_SECRET = os.environ.get('INSTAGRAM_APP_SECRET', '')
    django_settings.NEXTCLOUD_URL = os.environ.get('NEXTCLOUD_URL', '')
    django_settings.NEXTCLOUD_USERNAME = os.environ.get('NEXTCLOUD_USERNAME', '')
    django_settings.NEXTCLOUD_PASSWORD = os.environ.get('NEXTCLOUD_PASSWORD', '')
    django_settings.NEXTCLOUD_FOLDER = os.environ.get('NEXTCLOUD_FOLDER', '')
    django_settings.EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
    django_settings.EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
    django_settings.EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
    django_settings.EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
    django_settings.EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
    django_settings.DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@sangheeandfabio.com')

    # Validate Google client ID format after reloading
    google_client_id = django_settings.GOOGLE_CLIENT_ID
    if google_client_id and not is_valid_google_client_id(google_client_id):
        logger.warning(
            "GOOGLE_CLIENT_ID appears invalid after settings reload: '%s'. "
            "It should end with '.apps.googleusercontent.com'. "
            "Google login will be disabled until this is corrected in the .env file.",
            google_client_id
        )


def is_provider_enabled(setting_value):
    """Check if a social provider is enabled based on its environment variable value."""
    return bool(setting_value) and setting_value.strip().lower() != 'disabled'


def is_valid_google_client_id(client_id):
    """Check if the Google client ID looks like a valid OAuth 2.0 client ID for a web application.

    Valid Google OAuth 2.0 client IDs for web applications follow the format:
    <numeric-id>.apps.googleusercontent.com

    This prevents common misconfigurations such as:
    - Using the client secret instead of the client ID
    - Using a client ID from a different project or application type
    - Using an empty or whitespace-only string
    """
    if not client_id:
        return False
    client_id = client_id.strip()
    return client_id.endswith('.apps.googleusercontent.com')


def update_env_file(settings_obj):
    try:
        env_path = os.path.join(django_settings.BASE_DIR, '.env')
        for field_name, env_key in ENV_MAPPING.items():
            value = getattr(settings_obj, field_name, None)
            if value is not None:
                if isinstance(value, bool):
                    value = 'True' if value else 'False'
                else:
                    value = str(value)
                set_key(env_path, env_key, value)
        logger.info("Updated .env file with new settings")
    except Exception as e:
        logger.error(f"Failed to update .env file: {e}")


def update_user_from_social(user, provider, extra_data):
    """Update user's name and profile picture from social account data if missing."""
    updated = False

    if not user.first_name:
        first = extra_data.get('given_name') or extra_data.get('first_name')
        if first:
            user.first_name = first
            updated = True
    if not user.last_name:
        last = extra_data.get('family_name') or extra_data.get('last_name')
        if last:
            user.last_name = last
            updated = True

    if not user.profile_picture or user.profile_picture.name == 'profile_pics/default.png':
        picture_url = None
        if provider == 'google':
            picture_url = extra_data.get('picture')
        elif provider == 'facebook':
            fb_id = extra_data.get('id')
            if fb_id:
                picture_url = f"https://graph.facebook.com/{fb_id}/picture?type=large"
        elif provider == 'instagram':
            picture_url = extra_data.get('profile_picture')

        if picture_url:
            try:
                resp = requests.get(picture_url)
                if resp.status_code == 200:
                    try:
                        processed = process_profile_picture(ContentFile(resp.content, name='social.jpg'))
                        user.profile_picture.save(f"{user.username}_social.jpg", processed, save=False)
                        updated = True
                    except ValidationError:
                        logger.warning(f"Social profile picture too large for {user.email}, using default.")
            except Exception as e:
                logger.error(f"Failed to download profile picture for {user.email}: {e}")

    if updated:
        user.save()


# ==================== AUTH VIEWS ====================

class SocialProvidersStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        google_enabled = is_provider_enabled(django_settings.GOOGLE_CLIENT_ID)
        google_client_id = django_settings.GOOGLE_CLIENT_ID if google_enabled else None

        # Validate that the Google client ID has the correct format.
        # If it doesn't look like a valid client ID (e.g. it's the client secret
        # or a client ID from the wrong project), don't return it — this prevents
        # the frontend from rendering a Google button that will always fail with
        # `invalid_client`.
        if google_client_id and not is_valid_google_client_id(google_client_id):
            logger.warning(
                "SocialProvidersStatusView: GOOGLE_CLIENT_ID appears invalid: '%s'. "
                "It should end with '.apps.googleusercontent.com'. "
                "Google login will be disabled until this is corrected in the .env file.",
                google_client_id
            )
            google_client_id = None
            google_enabled = False

        return Response({
            'google': google_enabled,
            'google_client_id': google_client_id,
            'facebook': is_provider_enabled(django_settings.FACEBOOK_APP_ID),
            'instagram': is_provider_enabled(django_settings.INSTAGRAM_APP_ID),
        })


@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        # Rate limit check
        check_rate_limit(request, 'register')

        # Process profile picture if provided
        if 'profile_picture' in request.FILES:
            try:
                processed = process_profile_picture(request.FILES['profile_picture'])
            except ValidationError as e:
                return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            data = request.data.copy()
            data['profile_picture'] = processed
        else:
            data = request.data

        email = data.get('email')
        existing_user = None
        if email:
            existing_user = User.objects.filter(email=email).first()

        # If an unverified, inactive account already exists, update it instead of creating a new one
        if existing_user and not existing_user.is_active and not existing_user.email_verified:
            # Ensure the new username (if changed) isn't already taken by another user
            new_username = data.get('username')
            if new_username and new_username != existing_user.username:
                if User.objects.filter(username=new_username).exclude(id=existing_user.id).exists():
                    record_failed_attempt(request, 'register')
                    return Response({'username': 'This username is already taken.'}, status=status.HTTP_400_BAD_REQUEST)

            serializer = CustomUserSerializer(existing_user, data=data, partial=True)
            if serializer.is_valid():
                user = serializer.save()
                # Update password if a new one was provided
                password = data.get('password')
                if password:
                    user.set_password(password)
                    user.save()

                # Trigger face detection if a profile picture was uploaded
                if 'profile_picture' in data:
                    from .tasks import detect_faces_profile_picture
                    detect_faces_profile_picture.delay(user.id)

                # Resend verification email
                signer = TimestampSigner()
                token = signer.sign(user.email)
                verification_url = request.build_absolute_uri(f'/api/auth/verify-email/?token={token}')
                language = data.get('language', user.language or 'en')
                if language not in ['en', 'it', 'ko']:
                    language = 'en'

                try:
                    html_message = build_verification_email(verification_url, language=language)
                    subject = _get_email_subject(language)
                    send_mail(
                        subject=subject,
                        message='Please click the link to verify your email: ' + verification_url,
                        from_email=django_settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=False,
                        html_message=html_message,
                    )
                    logger.info(f"Verification email resent (re-registration) to: {user.email}")
                except Exception as e:
                    logger.error(f"Failed to resend verification email to {user.email}: {e}")

                return Response(
                    {'message': 'A new verification email has been sent. Please check your inbox.'},
                    status=status.HTTP_200_OK
                )
            else:
                record_failed_attempt(request, 'register')
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Normal registration flow (new user)
        serializer = CustomUserSerializer(data=data)
        if serializer.is_valid():
            user = serializer.save()
            user.is_active = False
            user.set_password(request.data['password'])
            user.save()

            # Trigger face detection if a profile picture was uploaded
            if 'profile_picture' in data:
                from .tasks import detect_faces_profile_picture
                detect_faces_profile_picture.delay(user.id)

            signer = TimestampSigner()
            token = signer.sign(user.email)
            verification_url = request.build_absolute_uri(f'/api/auth/verify-email/?token={token}')
            language = request.data.get('language', 'en')
            if language not in ['en', 'it', 'ko']:
                language = 'en'

            try:
                html_message = build_verification_email(verification_url, language=language)
                subject = _get_email_subject(language)
                send_mail(
                    subject=subject,
                    message='Please click the link to verify your email: ' + verification_url,
                    from_email=django_settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                    html_message=html_message,
                )
                logger.info(f"Verification email sent to: {user.email}")
            except Exception as e:
                logger.error(f"Failed to send verification email to {user.email}: {e}")

            logger.info(f"User registered: {user.email}")
            return Response(
                {'message': 'User registered successfully. Please check your email to verify your account.'},
                status=status.HTTP_201_CREATED
            )

        record_failed_attempt(request, 'register')
        logger.error(f"Registration failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get('token')
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
        wants_json = 'application/json' in request.accepted_media_type

        if not token:
            if wants_json:
                return Response({'error': 'missing_token'}, status=status.HTTP_400_BAD_REQUEST)
            return redirect(f"{frontend_url}/verify-email?error=missing_token")

        signer = TimestampSigner()
        try:
            email = signer.unsign(token, max_age=86400)  # 24 hours
        except SignatureExpired:
            if wants_json:
                return Response({'error': 'expired'}, status=status.HTTP_400_BAD_REQUEST)
            return redirect(f"{frontend_url}/verify-email?error=expired")
        except BadSignature:
            if wants_json:
                return Response({'error': 'invalid'}, status=status.HTTP_400_BAD_REQUEST)
            return redirect(f"{frontend_url}/verify-email?error=invalid")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            if wants_json:
                return Response({'error': 'user_not_found'}, status=status.HTTP_404_NOT_FOUND)
            return redirect(f"{frontend_url}/verify-email?error=user_not_found")

        if user.email_verified and user.is_active:
            # Already verified and active – log them in automatically
            refresh = RefreshToken.for_user(user)
            access = str(refresh.access_token)
            refresh_token = str(refresh)
            if wants_json:
                return Response({
                    'status': 'active',
                    'access': access,
                    'refresh': refresh_token
                })
            return redirect(
                f"{frontend_url}/verify-email?access={access}&refresh={refresh_token}"
            )

        # Mark email as verified but do NOT activate – admin must approve
        user.email_verified = True
        # user.is_active remains False
        user.save()

        if wants_json:
            return Response({'status': 'pending_approval'})
        return redirect(f"{frontend_url}/verify-email?status=pending_approval")


class ResendVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Don't reveal whether the email exists
            return Response({'message': 'If the email exists and is not verified, a new verification email has been sent.'})

        if user.email_verified:
            return Response({'message': 'This account is already verified. You can log in once an administrator activates it.'})

        # Rate limit the resend action
        check_rate_limit(request, 'resend_verification')

        # Generate a new token and send the email
        signer = TimestampSigner()
        token = signer.sign(user.email)
        verification_url = request.build_absolute_uri(f'/api/auth/verify-email/?token={token}')

        language = user.language or 'en'
        try:
            html_message = build_verification_email(verification_url, language=language)
            subject = _get_email_subject(language)
            send_mail(
                subject=subject,
                message='Please click the link to verify your email: ' + verification_url,
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
                html_message=html_message,
            )
            logger.info(f"Verification email resent to: {user.email}")
        except Exception as e:
            logger.error(f"Failed to resend verification email to {user.email}: {e}")
            return Response({'error': 'Failed to send email. Please try again later.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'message': 'A new verification email has been sent. Please check your inbox.'})


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # Disable authentication to avoid CSRF check on login

    def post(self, request):
        # Rate limit check
        check_rate_limit(request, 'login')

        username_or_email = request.data.get('username_or_email', '')
        password = request.data.get('password', '')
        user = None
        if '@' in username_or_email:
            try:
                user = User.objects.get(email__iexact=username_or_email)
            except User.DoesNotExist:
                pass
        else:
            try:
                user = User.objects.get(username=username_or_email)
            except User.DoesNotExist:
                pass
        if user and user.check_password(password):
            if not user.is_active:
                if not user.email_verified:
                    msg = 'Account is not verified. Please check your email for the verification link.'
                    return Response({
                        'error': msg,
                        'can_resend': True,
                        'email': user.email
                    }, status=status.HTTP_401_UNAUTHORIZED)
                else:
                    msg = 'Your account is pending admin approval.'
                    return Response({'error': msg}, status=status.HTTP_401_UNAUTHORIZED)
            login(request, user)

            remember_me = request.data.get('remember_me', False)
            refresh = RefreshToken.for_user(user)

            if remember_me:
                # Long-lived tokens: access 30 days, refresh 90 days
                access_lifetime = timedelta(days=30)
                refresh_lifetime = timedelta(days=90)
                refresh.access_token.set_exp(lifetime=access_lifetime)
                refresh.set_exp(lifetime=refresh_lifetime)

            logger.info(f"User logged in: {user.email}")
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': CustomUserSerializer(user, context={'request': request}).data
            })
        # Record failed attempt
        record_failed_attempt(request, 'login')
        logger.warning(f"Login failed for: {username_or_email}")
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        username = request.user.username
        logout(request)
        logger.info(f"User logged out: {username}")
        return Response({'message': 'Logged out successfully'})


class CustomTokenRefreshView(TokenRefreshView):
    """
    Override the default token refresh to reject tokens belonging to
    inactive or deleted users.
    """
    def post(self, request, *args, **kwargs):
        # First, try to decode the refresh token to get the user
        refresh_token = request.data.get('refresh')
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                user_id = token.payload.get('user_id')
                if user_id:
                    user = User.objects.filter(id=user_id).first()
                    if not user:
                        return Response(
                            {'code': 'user_deleted', 'detail': 'User account no longer exists.'},
                            status=status.HTTP_401_UNAUTHORIZED
                        )
                    if not user.is_active:
                        return Response(
                            {'code': 'user_deactivated', 'detail': 'User account is deactivated.'},
                            status=status.HTTP_401_UNAUTHORIZED
                        )
            except Exception:
                # If the token is invalid, let the parent class handle it
                pass

        return super().post(request, *args, **kwargs)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'message': 'If the email exists, a reset link has been sent.'})
        signer = TimestampSigner()
        token = signer.sign(user.email)
        reset_url = f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/password-reset-confirm/{user.pk}/{token}/"
        try:
            send_mail(
                subject='Password Reset Request',
                message=f'Click the link to reset your password: {reset_url}',
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            logger.info(f"Password reset email sent to: {user.email}")
        except Exception as e:
            logger.error(f"Failed to send password reset email to {user.email}: {e}")
        return Response({'message': 'If the email exists, a reset link has been sent.'})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, uidb64, token):
        try:
            user = User.objects.get(pk=uidb64)
        except User.DoesNotExist:
            return Response({'error': 'Invalid user'}, status=status.HTTP_400_BAD_REQUEST)
        signer = TimestampSigner()
        try:
            email = signer.unsign(token, max_age=3600)
            if email != user.email:
                return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)
        except (SignatureExpired, BadSignature):
            return Response({'error': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)
        new_password = request.data.get('password')
        if not new_password:
            return Response({'error': 'New password is required'}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)
        user.save()
        logger.info(f"Password reset for user: {user.email}")
        return Response({'message': 'Password reset successfully'})


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        return Response(CustomUserSerializer(request.user, context={'request': request}).data)

    def put(self, request):
        # Check if this is a password change request
        new_password = request.data.get('password')

        if new_password:
            # If user already has a password, require current password
            if request.user.has_usable_password():
                current_password = request.data.get('current_password')
                if not current_password:
                    return Response({'detail': 'Current password is required'}, status=status.HTTP_400_BAD_REQUEST)
                if not request.user.check_password(current_password):
                    return Response({'detail': 'Current password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)
            # Validate new password
            try:
                validate_password(new_password, user=request.user)
            except Exception as e:
                return Response({'detail': list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
            request.user.set_password(new_password)
            request.user.save()
            logger.info(f"Password updated for user: {request.user.username}")
            return Response({'message': 'Password updated successfully'})

        # Process profile picture if provided
        if 'profile_picture' in request.FILES:
            try:
                processed = process_profile_picture(request.FILES['profile_picture'])
            except ValidationError as e:
                return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

            data = request.data.copy()
            data['profile_picture'] = processed
        else:
            data = request.data

        # Regular profile update
        serializer = CustomUserSerializer(request.user, data=data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            # Trigger face detection if a new profile picture was provided
            if 'profile_picture' in request.FILES:
                from .tasks import detect_faces_profile_picture
                detect_faces_profile_picture.delay(request.user.id)
            # Invalidate profile picture cache
            redis_client = redis.Redis(
                host=django_settings.REDIS_HOST,
                port=django_settings.REDIS_PORT,
            )
            cache_key = f"user_profile_pic:{request.user.id}"
            redis_client.delete(cache_key)
            logger.info(f"Profile updated for user: {request.user.username}")
            return Response(serializer.data)
        logger.error(f"Profile update failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        user = request.user

        # Protect the default superuser created from environment variables
        default_admin_username = os.getenv('ADMIN_USERNAME')
        default_admin_email = os.getenv('ADMIN_EMAIL')
        if user.is_superuser and (user.username == default_admin_username or user.email == default_admin_email):
            return Response(
                {'error': 'Cannot delete the default superuser account'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Delete all media owned by this user from cloud storage and DB
        for media in user.uploaded_media.all():
            delete_media_task.delay(media.id)

        # Delete the user (media objects will be cleaned up by the tasks)
        user.delete()
        logger.info(f"User self-deleted: {user.username}")
        return Response(status=status.HTTP_204_NO_CONTENT)


class SocialLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        provider = request.data.get('provider')
        access_token = request.data.get('access_token')
        if not provider or not access_token:
            return Response({'error': 'Provider and access_token are required'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if provider is enabled
        if provider == 'google' and not is_provider_enabled(django_settings.GOOGLE_CLIENT_ID):
            return Response({'error': 'Google login is currently disabled.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate Google client ID format before attempting login
        if provider == 'google' and not is_valid_google_client_id(django_settings.GOOGLE_CLIENT_ID):
            logger.error(
                "SocialLoginView: GOOGLE_CLIENT_ID appears invalid: '%s'. "
                "It should end with '.apps.googleusercontent.com'. "
                "Google login is disabled until this is corrected in the .env file.",
                django_settings.GOOGLE_CLIENT_ID
            )
            return Response(
                {'error': 'Google login is not properly configured. Please contact the site administrator.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        if provider == 'google':
            return self.handle_google(access_token, request)
        return Response({'error': 'Unsupported provider'}, status=status.HTTP_400_BAD_REQUEST)

    def handle_google(self, access_token, request):
        try:
            user_info = self.get_google_user_info(access_token)
        except Exception as e:
            return Response({'error': f'Google token verification failed: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        email = user_info.get('email')
        if not email:
            return Response({'error': 'Email not provided by Google'}, status=status.HTTP_400_BAD_REQUEST)

        user, created = User.objects.get_or_create(email=email, defaults={
            'username': self.generate_username(user_info),
            'first_name': user_info.get('given_name', ''),
            'last_name': user_info.get('family_name', ''),
            'is_active': False,
            'email_verified': True,
        })

        # Link Google social account to the user
        google_uid = user_info.get('sub')
        if google_uid:
            SocialAccount.objects.get_or_create(
                user=user,
                provider='google',
                uid=google_uid,
                defaults={'extra_data': user_info}
            )

        # Update profile with Google data if user already existed
        if not created:
            update_user_from_social(user, 'google', user_info)

        # Trigger face detection if a profile picture was set
        if user.profile_picture and user.profile_picture.name != 'profile_pics/default.png':
            from .tasks import detect_faces_profile_picture
            detect_faces_profile_picture.delay(user.id)

        # If user is not active, they need admin approval
        if not user.is_active:
            return Response(
                {'error': 'Your account is pending admin approval. You will be able to log in once an administrator activates your account.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': CustomUserSerializer(user, context={'request': request}).data
        })

    def get_google_user_info(self, id_token):
        # Verify the ID token using Google's tokeninfo endpoint
        response = requests.get(f'https://oauth2.googleapis.com/tokeninfo?id_token={id_token}')
        if response.status_code != 200:
            raise Exception('Failed to verify ID token')
        data = response.json()
        # tokeninfo returns fields like email, given_name, family_name, picture
        return data

    def generate_username(self, user_info):
        base = user_info.get('given_name', '') + '_' + user_info.get('family_name', '')
        base = base.strip('_') or user_info.get('email', '').split('@')[0]
        # Sanitize to only allowed characters
        base = sanitize_username(base)
        username = base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}{counter}"
            counter += 1
        return username

    def download_profile_picture(self, user, url):
        if not url:
            return
        try:
            response = requests.get(url)
            if response.status_code == 200:
                user.profile_picture.save(f"{user.username}_profile.jpg", ContentFile(response.content), save=True)
        except Exception as e:
            logger.error(f"Failed to download profile picture: {e}")


class SocialLoginRedirectView(APIView):
    """Redirect to OAuth provider for Facebook/Instagram login via django-allauth"""
    permission_classes = [AllowAny]
    provider = None

    def get(self, request):
        return redirect(f'/accounts/{self.provider}/login/')


class FacebookRedirectView(SocialLoginRedirectView):
    provider = 'facebook'

    def get(self, request):
        if not is_provider_enabled(django_settings.FACEBOOK_APP_ID):
            return Response({'error': 'Facebook login is currently disabled.'}, status=status.HTTP_400_BAD_REQUEST)
        return redirect(f'/accounts/{self.provider}/login/')


class InstagramRedirectView(SocialLoginRedirectView):
    provider = 'instagram'

    def get(self, request):
        if not is_provider_enabled(django_settings.INSTAGRAM_APP_ID):
            return Response({'error': 'Instagram login is currently disabled.'}, status=status.HTTP_400_BAD_REQUEST)
        return redirect(f'/accounts/{self.provider}/login/')


class SocialLoginCallbackView(APIView):
    """
    Called by django-allauth after successful OAuth login.
    Generates JWT tokens and redirects to frontend with tokens.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect(f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/login?error=social_callback_failed")

        user = request.user
        email = user.email

        # Check if another user already has this email (merge accounts)
        if email:
            existing_user = User.objects.filter(email=email).exclude(id=user.id).first()
            if existing_user:
                # Transfer all social accounts from the new user to the existing user
                for sa in SocialAccount.objects.filter(user=user):
                    # Avoid duplicate provider+uid on the existing user
                    if not SocialAccount.objects.filter(user=existing_user, provider=sa.provider, uid=sa.uid).exists():
                        sa.user = existing_user
                        sa.save()
                    else:
                        sa.delete()
                # Update existing user's profile with social data
                social_account = SocialAccount.objects.filter(user=existing_user).first()
                if social_account:
                    update_user_from_social(existing_user, social_account.provider, social_account.extra_data)
                # Delete the newly created user
                user.delete()
                # Log in as the existing user
                logout(request)
                login(request, existing_user)
                user = existing_user

        # Mark email as verified for social logins (but do NOT activate – admin must approve)
        user.email_verified = True

        # Ensure username is set properly from social account
        social_account = SocialAccount.objects.filter(user=user).first()
        if social_account:
            extra_data = social_account.extra_data
            provider = social_account.provider

            # Set username if not already meaningful
            if not user.username or user.username.startswith('user_'):
                if provider == 'facebook':
                    first = extra_data.get('first_name', '')
                    last = extra_data.get('last_name', '')
                    base = f"{first}_{last}".strip('_') or extra_data.get('email', '').split('@')[0]
                elif provider == 'instagram':
                    base = extra_data.get('username', '') or extra_data.get('full_name', '').replace(' ', '_')
                else:  # google or fallback
                    base = extra_data.get('given_name', '') + '_' + extra_data.get('family_name', '')
                    base = base.strip('_') or extra_data.get('email', '').split('@')[0]

                # Sanitize to only allowed characters
                base = sanitize_username(base)

                # Make unique
                username = base
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base}{counter}"
                    counter += 1
                user.username = username

            # Download profile picture if not already set
            if not user.profile_picture or user.profile_picture.name == 'profile_pics/default.png':
                picture_url = None
                if provider == 'facebook':
                    fb_id = extra_data.get('id')
                    if fb_id:
                        picture_url = f"https://graph.facebook.com/{fb_id}/picture?type=large"
                elif provider == 'instagram':
                    picture_url = extra_data.get('profile_picture')
                elif provider == 'google':
                    picture_url = extra_data.get('picture')
                if picture_url:
                    try:
                        resp = requests.get(picture_url)
                        if resp.status_code == 200:
                            # Process the downloaded picture to enforce size limit
                            try:
                                processed = process_profile_picture(ContentFile(resp.content, name='social.jpg'))
                                user.profile_picture.save(f"{user.username}_social.jpg", processed, save=False)
                                # Trigger face detection on the new social profile picture
                                from .tasks import detect_faces_profile_picture
                                detect_faces_profile_picture.delay(user.id)
                            except ValidationError:
                                logger.warning(f"Could not process social profile picture for {user.email}, using default.")
                    except Exception as e:
                        logger.error(f"Failed to download profile picture for {user.email}: {e}")

            # Fallback to default profile picture from local static file if none was set
            if not user.profile_picture or user.profile_picture.name == 'profile_pics/default.png':
                try:
                    with staticfiles_storage.open('images/default_profile_pic.png', 'rb') as f:
                        user.profile_picture.save('default.png', ContentFile(f.read()), save=False)
                except Exception as e:
                    logger.error(f"Failed to set default profile picture for {user.email}: {e}")

        user.save()

        if not user.is_active:
            # Account is not yet approved – redirect with pending status
            frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
            return redirect(f"{frontend_url}/social-callback?status=pending_approval")

        # Generate JWT tokens only for active users
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        refresh_token = str(refresh)

        # Redirect to frontend social-callback with tokens
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
        redirect_url = f"{frontend_url}/social-callback?access={access}&refresh={refresh_token}"
        return redirect(redirect_url)


# ==================== PUBLIC USER VIEWS ====================

class PublicUserListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        queryset = User.objects.filter(is_active=True)
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(username__icontains=search)
        serializer = PublicUserSerializer(queryset.order_by('username'), many=True, context={'request': request})
        return Response(serializer.data)


class PublicUserDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id, is_active=True)
        serializer = PublicUserSerializer(user, context={'request': request})
        return Response(serializer.data)


class UserProfilePictureView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id, is_active=True)

        # If user has a custom picture and the file exists, serve it (with caching)
        if user.profile_picture and user.profile_picture.storage.exists(user.profile_picture.name):
            redis_client = redis.Redis(
                host=django_settings.REDIS_HOST,
                port=django_settings.REDIS_PORT,
                decode_responses=False
            )
            cache_key = f"user_profile_pic:{user.id}"
            cached = redis_client.get(cache_key)
            if cached:
                ext = os.path.splitext(user.profile_picture.name)[1].lower()
                content_type = 'image/jpeg' if ext in ['.jpg', '.jpeg'] else 'image/png'
                return HttpResponse(cached, content_type=content_type)

            try:
                with user.profile_picture.open('rb') as f:
                    content = f.read()
            except Exception:
                raise Http404("Profile picture not found")

            redis_client.setex(cache_key, 3600, content)
            ext = os.path.splitext(user.profile_picture.name)[1].lower()
            content_type = 'image/jpeg' if ext in ['.jpg', '.jpeg'] else 'image/png'
            return HttpResponse(content, content_type=content_type)

        # Fallback: serve the default profile picture from static files
        try:
            with staticfiles_storage.open('images/default_profile_pic.png', 'rb') as f:
                content = f.read()
            return HttpResponse(content, content_type='image/png')
        except Exception:
            raise Http404("Profile picture not found")


# ==================== MEDIA VIEWS ====================

class MediaListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        media = Media.objects.all()
        return Response(MediaSerializer(media, many=True).data)


class MediaUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        caption = request.POST.get('caption', '')

        # Temporary storage for the single file
        tmp_dir = os.path.join(django_settings.MEDIA_ROOT, 'tmp_uploads')
        os.makedirs(tmp_dir, exist_ok=True)

        tmp_name = f"{request.user.id}_{uuid.uuid4().hex}_{file.name}"
        tmp_path = os.path.join(tmp_dir, tmp_name)

        with open(tmp_path, 'wb') as dst:
            for chunk in file.chunks():
                dst.write(chunk)

        media_type = 'video' if file.content_type.startswith('video') else 'image'
        file_data = {
            'tmp_path': tmp_path,
            'original_filename': file.name,
            'caption': caption,
            'media_type': media_type,
        }

        task = upload_media_task.delay(request.user.id, [file_data])
        return Response({'task_id': task.id, 'message': 'Upload started'}, status=status.HTTP_202_ACCEPTED)


class MediaDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, media_id):
        media = get_object_or_404(Media, id=media_id, user=request.user)
        delete_media_task.delay(media.id)
        return Response({'message': 'Deletion started'}, status=status.HTTP_202_ACCEPTED)


class MediaBulkDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        media_ids = request.data.get('media_ids', [])
        if not media_ids:
            return Response({'error': 'No media IDs provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Only delete media that belongs to the requesting user
        media_items = Media.objects.filter(id__in=media_ids, user=request.user)
        deleted_count = media_items.count()
        for media in media_items:
            delete_media_task.delay(media.id)

        return Response({
            'message': f'{deleted_count} media items deleted successfully.',
            'deleted_count': deleted_count
        })


class MyUploadsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        start = (page - 1) * page_size
        end = start + page_size
        media = Media.objects.filter(user=request.user).order_by('-uploaded_at')
        page_media = media[start:end]
        return Response(MediaSerializer(page_media, many=True).data)


class MediaModerationView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        status_filter = request.query_params.get('status', 'pending')
        media_type = request.query_params.get('media_type', '')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        start = (page - 1) * page_size
        end = start + page_size

        queryset = Media.objects.all()
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if media_type:
            queryset = queryset.filter(media_type=media_type)
        queryset = queryset.order_by('-uploaded_at')
        page_media = queryset[start:end]
        return Response(MediaModerationSerializer(page_media, many=True).data)


class MediaModerateSingleView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, media_id):
        media = get_object_or_404(Media, id=media_id)
        serializer = MediaModerationSerializer(media, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(reviewed_by=request.user, reviewed_at=timezone.now())
            if media.status == 'approved':
                detect_faces_task.delay(media.id)
            logger.info(f"Media {media_id} moderated by {request.user.username}")
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, media_id):
        media = get_object_or_404(Media, id=media_id)

        # Delete from Nextcloud
        nc = NextcloudClient()
        if media.nextcloud_file_id:
            nc.delete_file(media.nextcloud_file_id)

        # Delete from Redis cache
        try:
            redis_client = redis.Redis(
                host=django_settings.REDIS_HOST,
                port=django_settings.REDIS_PORT,
                decode_responses=False
            )
            cache_key = f"media_cache:{media.id}"
            redis_client.delete(cache_key)
        except Exception as e:
            logger.error(f"Redis cache delete error: {e}")

        # Delete from database
        media.delete()
        logger.info(f"Admin {request.user.username} deleted media {media_id}")

        # Clean up empty FaceGroups
        empty_groups = FaceGroup.objects.annotate(
            tag_count=Count('face_tags')
        ).filter(tag_count=0)
        for group in empty_groups:
            if group.thumbnail:
                group.thumbnail.delete(save=False)
            group.delete()
            logger.info(f"Deleted empty FaceGroup {group.id}")

        return Response({'message': 'Media deleted successfully'}, status=status.HTTP_200_OK)


class MediaFileView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, media_id):
        try:
            media = Media.objects.get(id=media_id)
        except Media.DoesNotExist:
            raise Http404("Media not found")
        if media.status != 'approved' and not (
            request.user.is_staff or
            (request.user.is_authenticated and request.user == media.user)
        ):
            raise Http404("Media not available")

        redis_client = redis.Redis(
            host=django_settings.REDIS_HOST,
            port=django_settings.REDIS_PORT,
            decode_responses=False
        )
        cache_key = f"media_cache:{media.id}"
        cached = redis_client.get(cache_key)
        if cached:
            content_type = 'video/mp4' if media.media_type == 'video' else 'image/jpeg'
            return HttpResponse(cached, content_type=content_type)

        content, content_type = get_file_from_cloud(media)
        if content is None:
            # Fallback to local file storage
            if media.file and media.file.storage.exists(media.file.name):
                with media.file.open('rb') as f:
                    content = f.read()
                ext = os.path.splitext(media.file.name)[1].lower()
                if ext in ['.jpg', '.jpeg']:
                    content_type = 'image/jpeg'
                elif ext == '.png':
                    content_type = 'image/png'
                elif ext == '.gif':
                    content_type = 'image/gif'
                elif ext == '.mp4':
                    content_type = 'video/mp4'
                else:
                    content_type = 'application/octet-stream'
            else:
                raise Http404("File not found")
        redis_client.set(cache_key, content)
        media.view_count += 1
        media.save(update_fields=['view_count'])
        return HttpResponse(content, content_type=content_type)


class PublicMediaListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        queryset = Media.objects.filter(status='approved')
        user_id = request.query_params.get('user_id')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        search = request.query_params.get('search')
        user_search = request.query_params.get('user_search')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if date_from:
            queryset = queryset.filter(uploaded_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(uploaded_at__lte=date_to)
        if search:
            queryset = queryset.filter(caption__icontains=search)
        if user_search:
            queryset = queryset.filter(
                Q(user__username__icontains=user_search) |
                Q(user__first_name__icontains=user_search) |
                Q(user__last_name__icontains=user_search)
            )
        face_group_ids = request.query_params.getlist('face_group_id')
        if face_group_ids:
            # AND logic: media must have a FaceTag for EVERY selected group
            for gid in face_group_ids:
                queryset = queryset.filter(face_tags__face_group_id=gid)
            queryset = queryset.distinct()
        serializer = PublicMediaSerializer(queryset.order_by('-uploaded_at'), many=True, context={'request': request})
        return Response(serializer.data)


class TaskStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        task = AsyncResult(task_id)
        response_data = {
            'task_id': task_id,
            'status': task.status,
        }
        if task.status == 'SUCCESS':
            response_data['result'] = task.result
        elif task.status == 'FAILURE':
            response_data['error'] = str(task.result)
        return Response(response_data)


# ==================== ADMIN VIEWS ====================

class AdminDashboardView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        total_users = User.objects.count()
        total_admins = User.objects.filter(is_staff=True).count()
        total_media = Media.objects.count()
        pending_media = Media.objects.filter(status='pending').count()
        approved_media = Media.objects.filter(status='approved').count()
        rejected_media = Media.objects.filter(status='rejected').count()
        recent_uploads = Media.objects.order_by('-uploaded_at')[:10]
        data = {
            'total_users': total_users,
            'total_admins': total_admins,
            'total_media': total_media,
            'pending_media': pending_media,
            'approved_media': approved_media,
            'rejected_media': rejected_media,
            'recent_uploads': MediaSerializer(recent_uploads, many=True).data,
        }
        return Response(data)


class AdminSettingsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        settings = SiteSettings.load()
        return Response(SiteSettingsSerializer(settings).data)

    def put(self, request):
        settings = SiteSettings.load()
        serializer = SiteSettingsSerializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            update_env_file(settings)
            reload_django_settings()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminUserListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        users = User.objects.all()
        return Response(AdminUserSerializer(users, many=True, context={'request': request}).data)

    def post(self, request):
        serializer = AdminUserSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.save()
            if 'password' in request.data:
                user.set_password(request.data['password'])
                user.save()
            return Response(AdminUserSerializer(user, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminUserDetailView(APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self, user_id):
        return get_object_or_404(User, id=user_id)

    def get(self, request, user_id):
        user = self.get_object(user_id)
        return Response(AdminUserSerializer(user, context={'request': request}).data)

    def put(self, request, user_id):
        user = self.get_object(user_id)

        # Prevent non-superusers from changing the password of staff users
        if 'password' in request.data and user.is_staff and not request.user.is_superuser:
            return Response(
                {'error': 'Only superusers can change the password of an admin.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Process profile picture if provided
        if 'profile_picture' in request.FILES:
            try:
                processed = process_profile_picture(request.FILES['profile_picture'])
            except ValidationError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

            data = request.data.copy()
            data['profile_picture'] = processed
        else:
            data = request.data

        serializer = AdminUserSerializer(user, data=data, partial=True, context={'request': request})
        if serializer.is_valid():
            user = serializer.save()
            # Invalidate the cached profile picture so the new one is served immediately
            redis_client = redis.Redis(
                host=django_settings.REDIS_HOST,
                port=django_settings.REDIS_PORT,
            )
            cache_key = f"user_profile_pic:{user.id}"
            redis_client.delete(cache_key)
            return Response(AdminUserSerializer(user, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, user_id):
        user = self.get_object(user_id)

        # Protect the default superuser created from environment variables
        default_admin_username = os.getenv('ADMIN_USERNAME')
        if user.is_superuser and user.username == default_admin_username:
            return Response(
                {'error': 'Cannot delete the default superuser account'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Delete all media owned by this user from cloud storage and DB
        for media in user.uploaded_media.all():
            delete_media_task.delay(media.id)

        # Now delete the user (media objects will be cleaned up by the tasks)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminUserToggleStaffView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        user.is_staff = not user.is_staff
        user.save()
        return Response(AdminUserSerializer(user, context={'request': request}).data)


class AdminUserBulkUpdateView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        user_ids = request.data.get('user_ids', [])
        action = request.data.get('action')
        if not user_ids or not action:
            return Response({'error': 'user_ids and action are required.'}, status=status.HTTP_400_BAD_REQUEST)

        valid_actions = ['activate', 'deactivate', 'verify_email']
        if action not in valid_actions:
            return Response({'error': f'Invalid action. Must be one of {valid_actions}.'}, status=status.HTTP_400_BAD_REQUEST)

        users = User.objects.filter(id__in=user_ids)
        updated_count = 0
        for user in users:
            if action == 'activate':
                user.is_active = True
                user.email_verified = True  # activating also verifies email
                updated_count += 1
            elif action == 'deactivate':
                user.is_active = False
                updated_count += 1
            elif action == 'verify_email':
                user.email_verified = True
                updated_count += 1
            user.save()

        return Response({'message': f'{updated_count} users updated.', 'updated_count': updated_count})


class MediaBulkModerationView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = BulkModerationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        media_ids = serializer.validated_data['media_ids']
        action = serializer.validated_data['action']
        media_items = Media.objects.filter(id__in=media_ids)
        updated_count = 0
        for media in media_items:
            if action == 'approve':
                media.status = 'approved'
                media.reviewed_by = request.user
                media.reviewed_at = timezone.now()
                media.save()
                detect_faces_task.delay(media.id)
                updated_count += 1
            elif action == 'reject':
                media.status = 'rejected'
                media.reviewed_by = request.user
                media.reviewed_at = timezone.now()
                media.save()
                updated_count += 1
            elif action == 'delete':
                delete_media_task.delay(media.id)
                updated_count += 1
        action_past = {'approve': 'approved', 'reject': 'rejected', 'delete': 'deleted'}.get(action, action)
        return Response({'message': f'{updated_count} media items {action_past} successfully.', 'updated_count': updated_count})


class MediaDetectFacesView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        media_ids = request.data.get('media_ids', [])
        force = True   # This endpoint always forces re-detection

        logger.info(f"[MediaDetectFacesView] force={force}, media_ids={media_ids}")

        if not media_ids:
            return Response({'error': 'No media IDs provided.'}, status=status.HTTP_400_BAD_REQUEST)

        if force:
            # Process all selected images, regardless of status or previous processing
            eligible = Media.objects.filter(
                id__in=media_ids,
                media_type='image'
            )
        else:
            # Original behaviour: only approved images with no existing face tags
            eligible = Media.objects.filter(
                id__in=media_ids,
                status='approved',
                media_type='image'
            ).exclude(
                face_tags__isnull=False
            )

        processed = 0
        for media in eligible:
            detect_faces_task.delay(media.id, force=force)
            processed += 1

        skipped = len(media_ids) - processed
        return Response({
            'message': f'Face detection started for {processed} media items.',
            'processed': processed,
            'skipped': skipped,
        })


class FaceGroupListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        groups = FaceGroup.objects.annotate(
            face_count=Count('face_tags')
        ).filter(face_count__gt=0).order_by('-face_count')
        serializer = FaceGroupSerializer(groups, many=True, context={'request': request})
        return Response(serializer.data)


class FaceTagListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        tags = FaceTag.objects.all()
        serializer = FaceTagSerializer(tags, many=True)
        return Response(serializer.data)


class FaceTagDetailView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, tag_id):
        try:
            tag = FaceTag.objects.get(id=tag_id)
        except FaceTag.DoesNotExist:
            return Response({'error': 'Tag not found'}, status=status.HTTP_404_NOT_FOUND)
        name = request.data.get('name')
        if not name:
            return Response({'error': 'Name is required'}, status=status.HTTP_400_BAD_REQUEST)
        tag.name = name
        tag.save()
        return Response(FaceTagSerializer(tag).data)


# ==================== COOKIE CONSENT VIEWS ====================

class CookieConsentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get the current user's cookie consent preferences."""
        consent, created = CookieConsent.objects.get_or_create(
            user=request.user,
            defaults={'analytics': False, 'marketing': False, 'necessary': True}
        )
        serializer = CookieConsentSerializer(consent)
        return Response(serializer.data)

    def put(self, request):
        """Update the current user's cookie consent preferences."""
        consent, created = CookieConsent.objects.get_or_create(
            user=request.user,
            defaults={'analytics': False, 'marketing': False, 'necessary': True}
        )
        serializer = CookieConsentSerializer(consent, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
