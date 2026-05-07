import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django.http import Http404
from django.utils import timezone
from django.utils.translation import gettext as _
from django.contrib.auth import get_user_model, login, logout, authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings as django_settings
from .models import Media
from .serializers import CustomUserSerializer, MediaSerializer, MediaModerationSerializer, AdminUserSerializer, WebAppSettingsSerializer
from django.shortcuts import get_object_or_404
from django.core.files.base import ContentFile
import base64
import os
import hashlib
import requests
from io import BytesIO
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from config.settings import (
    NEXTCLOUD_URL, NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD, NEXTCLOUD_FOLDER,
    GOOGLE_DRIVE_CLIENT_ID, GOOGLE_DRIVE_CLIENT_SECRET, GOOGLE_DRIVE_TOKEN, GOOGLE_DRIVE_FOLDER_ID, DEBUG
)

logger = logging.getLogger(__name__)

User = get_user_model()

# ==================== AUTH VIEWS ====================

class RegisterView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = CustomUserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.set_password(request.data['password'])
            user.save()
            
            # Generate verification token
            signer = TimestampSigner()
            token = signer.sign(user.email)
            verification_url = request.build_absolute_uri(
                reverse('verify-email') + f'?token={token}'
            )
            
            # Send email
            try:
                send_mail(
                    subject='Verify your email address',
                    message=f'Please click the link to verify your email: {verification_url}',
                    from_email=django_settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                logger.info(f"Verification email sent to: {user.email}")
            except Exception as e:
                logger.error(f"Failed to send verification email to {user.email}: {e}")
            
            logger.info(f"User registered: {user.email}")
            return Response(
                {'message': 'User registered successfully. Please check your email to verify your account.'},
                status=status.HTTP_201_CREATED
            )
        logger.error(f"Registration failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        token = request.query_params.get('token')
        if not token:
            logger.error("Email verification attempted without token")
            return Response({'error': 'Token missing'}, status=status.HTTP_400_BAD_REQUEST)
        
        signer = TimestampSigner()
        try:
            email = signer.unsign(token, max_age=86400)  # 24 hours
        except SignatureExpired:
            logger.warning(f"Expired verification token for email")
            return Response({'error': 'Verification link expired'}, status=status.HTTP_400_BAD_REQUEST)
        except BadSignature:
            logger.error(f"Invalid verification token")
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            logger.error(f"Verification attempted for non-existent user: {email}")
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if user.email_verified:
            logger.info(f"Email already verified: {email}")
            return Response({'message': 'Email already verified'})
        
        user.email_verified = True
        user.is_active = True
        user.save()
        logger.info(f"Email verified successfully: {email}")
        return Response({'message': 'Email verified successfully. You can now log in.'})


class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            refresh = RefreshToken.for_user(user)
            logger.info(f"User logged in: {user.email}")
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': CustomUserSerializer(user).data
            })
        logger.warning(f"Login failed for: {email}")
        return Response({'error': _('Invalid credentials')}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        username = request.user.username
        logout(request)
        logger.info(f"User logged out: {username}")
        return Response({'message': _('Logged out successfully')})


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        logger.info("Password reset requested")
        # Implement password reset logic
        return Response({'message': _('Password reset email sent')})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request, uidb64, token):
        logger.info("Password reset confirmation attempted")
        # Implement password reset confirm logic
        return Response({'message': _('Password reset successful')})


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        logger.debug(f"Profile retrieved for user: {request.user.username}")
        return Response(CustomUserSerializer(request.user).data)
    
    def put(self, request):
        serializer = CustomUserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Profile updated for user: {request.user.username}")
            return Response(serializer.data)
        logger.error(f"Profile update failed for user {request.user.username}: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SocialLoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        logger.info(f"Social login attempt with provider: {request.data.get('provider', 'unknown')}")
        # Implement social login logic
        return Response({'message': _('Social login successful')})


# ==================== MEDIA VIEWS ====================

class MediaListView(APIView):
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        media = Media.objects.all()
        logger.debug(f"Media list retrieved by admin: {request.user.username}")
        return Response(MediaSerializer(media, many=True).data)


class MediaUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        serializer = MediaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            logger.info(f"Media uploaded by user {request.user.id}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        logger.error(f"Media upload failed for user {request.user.id}: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyUploadsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        media = Media.objects.filter(user=request.user)
        logger.debug(f"My uploads retrieved for user: {request.user.username}")
        return Response(MediaSerializer(media, many=True).data)


class MediaModerationView(APIView):
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        media = Media.objects.filter(status='pending')
        logger.debug(f"Pending media retrieved by admin: {request.user.username}")
        return Response(MediaModerationSerializer(media, many=True).data)


class MediaModerateSingleView(APIView):
    permission_classes = [IsAdminUser]
    
    def put(self, request, media_id):
        media = get_object_or_404(Media, id=media_id)
        serializer = MediaModerationSerializer(media, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Media {media_id} moderated by {request.user.username}")
            return Response(serializer.data)
        logger.error(f"Media moderation failed for {media_id}: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
