import logging
import os
import base64
import requests
import redis
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.contrib.auth import get_user_model, login, logout, authenticate
from django.contrib.auth.password_validation import validate_password
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.translation import gettext as _
from django.conf import settings as django_settings
from django.http import HttpResponse, Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Media, SiteSettings
from .serializers import (
    CustomUserSerializer, MediaSerializer, MediaModerationSerializer,
    AdminUserSerializer, SiteSettingsSerializer, BulkModerationSerializer
)
from .cloud_clients import get_file_from_cloud
from .tasks import upload_media_task, delete_media_task

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

            signer = TimestampSigner()
            token = signer.sign(user.email)
            verification_url = f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/verify-email?token={token}"

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
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
        if not token:
            return redirect(f"{frontend_url}/verify-email?error=missing_token")
        signer = TimestampSigner()
        try:
            email = signer.unsign(token, max_age=86400)  # 24 hours
        except SignatureExpired:
            return redirect(f"{frontend_url}/verify-email?error=expired")
        except BadSignature:
            return redirect(f"{frontend_url}/verify-email?error=invalid")
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return redirect(f"{frontend_url}/verify-email?error=user_not_found")
        if user.email_verified:
            return redirect(f"{frontend_url}/verify-email?success=already_verified")
        user.email_verified = True
        user.is_active = True
        user.save()
        return redirect(f"{frontend_url}/verify-email?success=verified")


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username_or_email = request.data.get('username_or_email', '')
        password = request.data.get('password', '')
        user = None
        if '@' in username_or_email:
            try:
                user = User.objects.get(email=username_or_email)
            except User.DoesNotExist:
                pass
        else:
            try:
                user = User.objects.get(username=username_or_email)
            except User.DoesNotExist:
                pass
        if user and user.check_password(password):
            if not user.is_active:
                return Response({'error': 'Account is not active. Please verify your email.'}, status=status.HTTP_401_UNAUTHORIZED)
            login(request, user)
            refresh = RefreshToken.for_user(user)
            logger.info(f"User logged in: {user.email}")
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': CustomUserSerializer(user).data
            })
        logger.warning(f"Login failed for: {username_or_email}")
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        username = request.user.username
        logout(request)
        logger.info(f"User logged out: {username}")
        return Response({'message': 'Logged out successfully'})


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
            logger.error(f"Failed to send password reset email: {e}")
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
        new_password = request.data.get('new_password')
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
        return Response(CustomUserSerializer(request.user).data)

    def put(self, request):
        serializer = CustomUserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Profile updated for user: {request.user.username}")
            return Response(serializer.data)
        logger.error(f"Profile update failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SocialLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        provider = request.data.get('provider')
        access_token = request.data.get('access_token')
        if not provider or not access_token:
            return Response({'error': 'Provider and access_token are required'}, status=status.HTTP_400_BAD_REQUEST)
        if provider == 'google':
            return self.handle_google(access_token)
        return Response({'error': 'Unsupported provider'}, status=status.HTTP_400_BAD_REQUEST)

    def handle_google(self, access_token):
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
            'is_active': True,
            'email_verified': True,
        })
        if created:
            self.download_profile_picture(user, user_info.get('picture'))
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': CustomUserSerializer(user).data
        })

    def get_google_user_info(self, access_token):
        response = requests.get('https://www.googleapis.com/oauth2/v3/userinfo',
                                headers={'Authorization': f'Bearer {access_token}'})
        if response.status_code != 200:
            raise Exception('Failed to fetch user info')
        return response.json()

    def generate_username(self, user_info):
        base = user_info.get('given_name', '') + '_' + user_info.get('family_name', '')
        base = base.strip('_') or user_info.get('email', '').split('@')[0]
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
        files = request.FILES.getlist('files')
        captions = request.POST.getlist('captions')
        if not files:
            return Response({'error': 'No files provided'}, status=status.HTTP_400_BAD_REQUEST)

        file_data_list = []
        for i, file in enumerate(files):
            content = file.read()
            encoded = base64.b64encode(content).decode('utf-8')
            caption = captions[i] if i < len(captions) else ''
            media_type = 'video' if file.content_type.startswith('video') else 'image'
            file_data_list.append({
                'file_content': encoded,
                'filename': file.name,
                'caption': caption,
                'media_type': media_type,
            })

        task = upload_media_task.delay(request.user.id, file_data_list)
        return Response({'task_id': task.id, 'message': 'Upload started'}, status=status.HTTP_202_ACCEPTED)


class MediaDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, media_id):
        media = get_object_or_404(Media, id=media_id, user=request.user)
        delete_media_task.delay(media.id, request.user.id)
        return Response({'message': 'Deletion started'}, status=status.HTTP_202_ACCEPTED)


class MyUploadsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        media = Media.objects.filter(user=request.user)
        return Response(MediaSerializer(media, many=True).data)


class MediaModerationView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        status_filter = request.query_params.get('status', 'pending')
        media_type = request.query_params.get('media_type', '')
        queryset = Media.objects.all()
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if media_type:
            queryset = queryset.filter(media_type=media_type)
        return Response(MediaModerationSerializer(queryset, many=True).data)


class MediaModerateSingleView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, media_id):
        media = get_object_or_404(Media, id=media_id)
        serializer = MediaModerationSerializer(media, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(reviewed_by=request.user, reviewed_at=timezone.now())
            logger.info(f"Media {media_id} moderated by {request.user.username}")
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MediaFileView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, media_id):
        try:
            media = Media.objects.get(id=media_id)
        except Media.DoesNotExist:
            raise Http404("Media not found")
        if media.status != 'approved' and not request.user.is_staff:
            raise Http404("Media not available")

        redis_client = redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'),
                                   port=int(os.getenv('REDIS_PORT', 6379)), decode_responses=False)
        cache_key = f"media_cache:{media.id}"
        cached = redis_client.get(cache_key)
        if cached:
            content_type = 'video/mp4' if media.media_type == 'video' else 'image/jpeg'
            return HttpResponse(cached, content_type=content_type)

        content, content_type = get_file_from_cloud(media)
        if content is None:
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
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if date_from:
            queryset = queryset.filter(uploaded_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(uploaded_at__lte=date_to)
        if search:
            queryset = queryset.filter(caption__icontains=search)
        return Response(MediaSerializer(queryset.order_by('-uploaded_at'), many=True).data)


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
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminUserListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        users = User.objects.all()
        return Response(AdminUserSerializer(users, many=True).data)

    def post(self, request):
        serializer = AdminUserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            if 'password' in request.data:
                user.set_password(request.data['password'])
                user.save()
            return Response(AdminUserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminUserDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get_object(self, user_id):
        return get_object_or_404(User, id=user_id)

    def get(self, request, user_id):
        user = self.get_object(user_id)
        return Response(AdminUserSerializer(user).data)

    def put(self, request, user_id):
        user = self.get_object(user_id)
        serializer = AdminUserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            user = serializer.save()
            if 'password' in request.data:
                user.set_password(request.data['password'])
                user.save()
            return Response(AdminUserSerializer(user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, user_id):
        user = self.get_object(user_id)
        if user.is_superuser:
            return Response({'error': 'Cannot delete superuser'}, status=status.HTTP_403_FORBIDDEN)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminUserToggleStaffView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        user.is_staff = not user.is_staff
        user.save()
        return Response(AdminUserSerializer(user).data)


class MediaBulkModerationView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = BulkModerationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        media_ids = serializer.validated_data['media_ids']
        action = serializer.validated_data['action']
        rejection_reason = serializer.validated_data.get('rejection_reason', '')
        media_items = Media.objects.filter(id__in=media_ids)
        updated_count = 0
        for media in media_items:
            if action == 'approve':
                media.status = 'approved'
                media.reviewed_by = request.user
                media.reviewed_at = timezone.now()
                media.save()
                updated_count += 1
            elif action == 'reject':
                media.status = 'rejected'
                media.rejection_reason = rejection_reason
                media.reviewed_by = request.user
                media.reviewed_at = timezone.now()
                media.save()
                updated_count += 1
        return Response({'message': f'{updated_count} media items {action}d successfully.', 'updated_count': updated_count})
