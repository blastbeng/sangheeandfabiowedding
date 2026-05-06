from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth import authenticate
from django.utils import timezone
from django.http import HttpResponse
from django.conf import settings

import os
import hashlib
import requests
import redis
from io import BytesIO
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from .models import CustomUser, Media
from .serializers import CustomUserSerializer, LoginSerializer, MediaSerializer, MediaModerationSerializer


class NextcloudClient:
    """WebDAV client for Nextcloud"""

    def __init__(self):
        self.base_url = settings.NEXTCLOUD_URL
        self.username = settings.NEXTCLOUD_USERNAME
        self.password = settings.NEXTCLOUD_PASSWORD
        self.folder = settings.NEXTCLOUD_FOLDER

    def upload_file(self, file_content, filename):
        """Upload file to Nextcloud, return file ID"""
        url = f"{self.base_url}/remote.php/dav/files/{self.username}{self.folder}/{filename}"
        try:
            response = requests.put(
                url,
                data=file_content,
                auth=(self.username, self.password),
                headers={'Content-Type': 'application/octet-stream'}
            )
            if response.status_code in [201, 204]:
                propfind_url = f"{self.base_url}/remote.php/dav/files/{self.username}{self.folder}/{filename}"
                propfind_response = requests.request(
                    'PROPFIND',
                    propfind_url,
                    auth=(self.username, self.password),
                    headers={'Depth': '0'}
                )
                file_id = propfind_response.headers.get('OC-FileId', filename)
                return file_id
            return None
        except Exception as e:
            print(f"Nextcloud upload error: {e}")
            return None

    def delete_file(self, filename):
        """Delete file from Nextcloud"""
        url = f"{self.base_url}/remote.php/dav/files/{self.username}{self.folder}/{filename}"
        try:
            response = requests.delete(url, auth=(self.username, self.password))
            return response.status_code in [200, 204]
        except Exception as e:
            print(f"Nextcloud delete error: {e}")
            return False

    def download_file(self, filename):
        """Download file from Nextcloud"""
        url = f"{self.base_url}/remote.php/dav/files/{self.username}{self.folder}/{filename}"
        try:
            response = requests.get(url, auth=(self.username, self.password))
            if response.status_code == 200:
                return response.content
            return None
        except Exception as e:
            print(f"Nextcloud download error: {e}")
            return None


class GoogleDriveClient:
    """Google Drive API client"""

    def __init__(self):
        try:
            self.credentials = Credentials(
                token=settings.GOOGLE_DRIVE_TOKEN,
                client_id=settings.GOOGLE_DRIVE_CLIENT_ID,
                client_secret=settings.GOOGLE_DRIVE_CLIENT_SECRET,
                token_uri='https://oauth2.googleapis.com/token',
            )
            self.service = build('drive', 'v3', credentials=self.credentials)
            self.folder_id = settings.GOOGLE_DRIVE_FOLDER_ID
        except Exception as e:
            print(f"Google Drive init error: {e}")
            self.service = None

    def upload_file(self, file_content, filename, mime_type):
        """Upload file to Google Drive, return file ID"""
        if not self.service:
            return None
        try:
            file_metadata = {
                'name': filename,
                'parents': [self.folder_id]
            }
            media = MediaFileUpload(BytesIO(file_content), mimetype=mime_type, resumable=True)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            self.service.permissions().create(
                fileId=file['id'],
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()
            return file['id']
        except HttpError as e:
            print(f"Google Drive upload error: {e}")
            return None

    def delete_file(self, file_id):
        """Delete file from Google Drive"""
        if not self.service:
            return False
        try:
            self.service.files().delete(fileId=file_id).execute()
            return True
        except HttpError as e:
            print(f"Google Drive delete error: {e}")
            return False

    def download_file(self, file_id):
        """Download file from Google Drive"""
        if not self.service:
            return None
        try:
            request = self.service.files().get_media(fileId=file_id)
            return request.execute()
        except HttpError as e:
            print(f"Google Drive download error: {e}")
            return None


class CacheManager:
    """Redis-based cache manager with 1GB limit"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=False
        )
        self.cache_prefix = 'media_cache:'
        
    def _get_cache_key(self, media_id, extension):
        return f"{self.cache_prefix}{media_id}{extension}"
    
    def store(self, media_id, content, extension):
        """Store file in Redis cache"""
        cache_key = self._get_cache_key(media_id, extension)
        try:
            self.redis_client.set(cache_key, content)
            return True
        except Exception as e:
            print(f"Redis cache store error: {e}")
            return False
    
    def get(self, media_id, extension):
        """Retrieve file from Redis cache"""
        cache_key = self._get_cache_key(media_id, extension)
        try:
            content = self.redis_client.get(cache_key)
            return content if content else None
        except Exception as e:
            print(f"Redis cache get error: {e}")
            return None
    
    def delete(self, media_id, extension):
        """Delete file from Redis cache"""
        cache_key = self._get_cache_key(media_id, extension)
        try:
            self.redis_client.delete(cache_key)
            return True
        except Exception as e:
            print(f"Redis cache delete error: {e}")
            return False


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CustomUserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': CustomUserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': CustomUserSerializer(user).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = CustomUserSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = CustomUserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MediaListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        media = Media.objects.filter(status='approved')
        serializer = MediaSerializer(media, many=True)
        return Response(serializer.data)


class MediaUploadView(APIView):
    """Upload multiple files to both Nextcloud and Google Drive simultaneously"""
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        files = request.FILES.getlist('files')
        captions = request.data.getlist('captions')
        media_types = request.data.getlist('media_types')

        if not files:
            return Response({'error': 'No files provided'}, status=status.HTTP_400_BAD_REQUEST)

        nextcloud_client = NextcloudClient()
        google_client = GoogleDriveClient()
        cache_manager = CacheManager()

        uploaded_media = []
        errors = []

        for index, file in enumerate(files):
            try:
                caption = captions[index] if index < len(captions) else ''
                media_type = media_types[index] if index < len(media_types) else 'image'

                filename = f"{request.user.id}_{hashlib.md5(file.name.encode()).hexdigest()[:8]}_{file.name}"
                extension = os.path.splitext(file.name)[1]
                file_content = file.read()

                # Upload to Nextcloud FIRST
                nextcloud_id = nextcloud_client.upload_file(file_content, filename)
                if not nextcloud_id:
                    errors.append(f"Nextcloud upload failed for {file.name}")
                    continue

                # Upload to Google Drive SECOND
                mime_type = 'video/mp4' if media_type == 'video' else 'image/jpeg'
                google_id = google_client.upload_file(file_content, filename, mime_type)
                if not google_id:
                    # ROLLBACK: Delete from Nextcloud since Google Drive failed
                    nextcloud_client.delete_file(filename)
                    errors.append(f"Google Drive upload failed for {file.name}, Nextcloud file deleted")
                    continue

                # Both uploads successful - store in cache and create record
                media = Media.objects.create(
                    user=request.user,
                    media_type=media_type,
                    caption=caption,
                    status='pending',
                    nextcloud_file_id=nextcloud_id,
                    google_drive_file_id=google_id,
                    view_count=0
                )
                uploaded_media.append(media)

            except Exception as e:
                errors.append(f"Error uploading {file.name}: {str(e)}")
                # Attempt cleanup if partial upload occurred
                if 'nextcloud_id' in locals() and nextcloud_id:
                    nextcloud_client.delete_file(filename)
                if 'google_id' in locals() and google_id:
                    google_client.delete_file(google_id)

        if uploaded_media:
            serializer = MediaSerializer(uploaded_media, many=True)
            response_data = {'uploaded': serializer.data}
            if errors:
                response_data['errors'] = errors
                response_data['warning'] = 'Some files failed to upload'
            return Response(response_data, status=status.HTTP_201_CREATED)
        else:
            return Response({'error': 'All uploads failed', 'details': errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MediaFileView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, media_id):
        cache_manager = CacheManager()
        google_client = GoogleDriveClient()
        nextcloud_client = NextcloudClient()

        try:
            media = Media.objects.get(id=media_id)
        except Media.DoesNotExist:
            return Response({'error': 'Media not found'}, status=status.HTTP_404_NOT_FOUND)

        media.view_count += 1
        media.save()

        extension = '.mp4' if media.media_type == 'video' else '.jpg'
        content_type = 'video/mp4' if media.media_type == 'video' else 'image/jpeg'

        # 1. Try Redis cache FIRST (fastest)
        cached_content = cache_manager.get(media.id, extension)
        if cached_content:
            return HttpResponse(cached_content, content_type=content_type)

        # 2. Try Google Drive SECOND
        content = google_client.download_file(media.google_drive_file_id)
        if content:
            cache_manager.store(media.id, content, extension)
            return HttpResponse(content, content_type=content_type)

        # 3. Try Nextcloud THIRD (fallback)
        content = nextcloud_client.download_file(media.nextcloud_file_id)
        if content:
            cache_manager.store(media.id, content, extension)
            return HttpResponse(content, content_type=content_type)

        return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)


class MediaDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, media_id):
        try:
            media = Media.objects.get(id=media_id, user=request.user)
        except Media.DoesNotExist:
            return Response({'error': 'Media not found'}, status=status.HTTP_404_NOT_FOUND)

        nextcloud_client = NextcloudClient()
        google_client = GoogleDriveClient()
        cache_manager = CacheManager()

        # Delete from Nextcloud
        if media.nextcloud_file_id:
            nextcloud_client.delete_file(media.nextcloud_file_id)

        # Delete from Google Drive
        if media.google_drive_file_id:
            google_client.delete_file(media.google_drive_file_id)

        # Delete from Redis cache
        extension = '.mp4' if media.media_type == 'video' else '.jpg'
        cache_manager.delete(media.id, extension)

        media.delete()
        return Response({'message': 'File deleted successfully'})


class MyUploadsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        media = Media.objects.filter(user=request.user).order_by('-uploaded_at')
        serializer = MediaSerializer(media, many=True)
        return Response(serializer.data)


class MediaModerationView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        status_filter = request.query_params.get('status', 'pending')
        user_filter = request.query_params.get('user_id')
        media_type_filter = request.query_params.get('media_type')

        media = Media.objects.all()

        if status_filter:
            media = media.filter(status=status_filter)
        if user_filter:
            media = media.filter(user_id=user_filter)
        if media_type_filter:
            media = media.filter(media_type=media_type_filter)

        serializer = MediaModerationSerializer(media.order_by('-uploaded_at'), many=True)
        return Response(serializer.data)

    def post(self, request):
        media_ids = request.data.get('media_ids', [])
        action = request.data.get('action')
        rejection_reason = request.data.get('rejection_reason', '')

        if not media_ids or action not in ['approve', 'reject']:
            return Response({'error': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)

        updated_count = 0
        for media_id in media_ids:
            try:
                media = Media.objects.get(id=media_id)
                media.status = 'approved' if action == 'approve' else 'rejected'
                media.reviewed_at = timezone.now()
                media.reviewed_by = request.user
                if action == 'reject':
                    media.rejection_reason = rejection_reason
                media.save()
                updated_count += 1
            except Media.DoesNotExist:
                continue

        return Response({'updated': updated_count})


class MediaModerateSingleView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, media_id):
        action = request.data.get('action')
        rejection_reason = request.data.get('rejection_reason', '')

        if action not in ['approve', 'reject']:
            return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            media = Media.objects.get(id=media_id)
            media.status = 'approved' if action == 'approve' else 'rejected'
            media.reviewed_at = timezone.now()
            media.reviewed_by = request.user
            if action == 'reject':
                media.rejection_reason = rejection_reason
            media.save()

            serializer = MediaModerationSerializer(media)
            return Response(serializer.data)
        except Media.DoesNotExist:
            return Response({'error': 'Media not found'}, status=status.HTTP_404_NOT_FOUND)


class SocialLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        provider = request.data.get('provider')
        access_token = request.data.get('access_token')
        custom_username = request.data.get('username', '')

        if not provider or not access_token:
            return Response({'error': 'Provider and access_token required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if provider == 'google':
                response = requests.get(
                    'https://www.googleapis.com/oauth2/v3/userinfo',
                    headers={'Authorization': f'Bearer {access_token}'}
                )
            elif provider == 'facebook':
                response = requests.get(
                    'https://graph.facebook.com/me',
                    params={'fields': 'id,name,email,picture.type(large)', 'access_token': access_token}
                )
            else:
                return Response({'error': 'Invalid provider'}, status=status.HTTP_400_BAD_REQUEST)

            if response.status_code != 200:
                return Response({'error': 'Failed to verify token'}, status=status.HTTP_400_BAD_REQUEST)

            user_data = response.json()
            email = user_data.get('email')

            if not email:
                return Response({'error': 'Email not provided'}, status=status.HTTP_400_BAD_REQUEST)

            if not custom_username:
                if provider == 'facebook':
                    name_parts = user_data.get('name', 'user').split()
                    custom_username = f"{name_parts[0]}_{name_parts[-1]}" if len(name_parts) > 1 else name_parts[0]
                elif provider == 'google':
                    given_name = user_data.get('given_name', '')
                    family_name = user_data.get('family_name', '')
                    custom_username = f"{given_name}_{family_name}".strip('_') if given_name or family_name else user_data.get('nickname', 'user')

            user, created = CustomUser.objects.get_or_create(
                email=email,
                defaults={
                    'username': custom_username,
                    'first_name': user_data.get('given_name', '') or (user_data.get('name', '').split()[0] if user_data.get('name') else ''),
                    'last_name': user_data.get('family_name', '') or (user_data.get('name', '').split()[-1] if len(user_data.get('name', '').split()) > 1 else ''),
                }
            )

            from allauth.socialaccount.models import SocialAccount
            SocialAccount.objects.get_or_create(user=user, provider=provider, uid=user_data.get('id'))

            refresh = RefreshToken.for_user(user)

            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': CustomUserSerializer(user).data,
                'created': created
            })

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
