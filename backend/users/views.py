from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.http import Http404
from django.utils import timezone
from django.utils.translation import gettext as _
from django.contrib.auth import get_user_model
from .models import Media
from .serializers import MediaSerializer, MediaModerationSerializer, AdminUserSerializer, WebAppSettingsSerializer
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
    GOOGLE_DRIVE_CLIENT_ID, GOOGLE_DRIVE_CLIENT_SECRET, GOOGLE_DRIVE_TOKEN, GOOGLE_DRIVE_FOLDER_ID
)


class NextcloudClient:
    """WebDAV client for Nextcloud"""

    def __init__(self):
        self.base_url = NEXTCLOUD_URL
        self.username = NEXTCLOUD_USERNAME
        self.password = NEXTCLOUD_PASSWORD
        self.folder = NEXTCLOUD_FOLDER

    def upload_file(self, file_content, filename):
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
        url = f"{self.base_url}/remote.php/dav/files/{self.username}{self.folder}/{filename}"
        try:
            response = requests.delete(url, auth=(self.username, self.password))
            return response.status_code in [200, 204]
        except Exception as e:
            print(f"Nextcloud delete error: {e}")
            return False


class GoogleDriveClient:
    """Google Drive API client"""

    def __init__(self):
        try:
            self.credentials = Credentials(
                token=GOOGLE_DRIVE_TOKEN,
                client_id=GOOGLE_DRIVE_CLIENT_ID,
                client_secret=GOOGLE_DRIVE_CLIENT_SECRET,
                token_uri='https://oauth2.googleapis.com/token',
            )
            self.service = build('drive', 'v3', credentials=self.credentials)
            self.folder_id = GOOGLE_DRIVE_FOLDER_ID
        except Exception as e:
            print(f"Google Drive init error: {e}")
            self.service = None

    def upload_file(self, file_content, filename, mime_type):
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
        if not self.service:
            return False
        try:
            self.service.files().delete(fileId=file_id).execute()
            return True
        except HttpError as e:
            print(f"Google Drive delete error: {e}")
            return False


class MediaUploadView(APIView):
    """Upload multiple files to both Nextcloud and Google Drive asynchronously via Celery"""
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        files = request.FILES.getlist('files')
        captions = request.data.getlist('captions')
        media_types = request.data.getlist('media_types')

        if not files:
            return Response({'error': _('No files provided')}, status=status.HTTP_400_BAD_REQUEST)

        import base64
        
        # Prepare file data for Celery task
        file_data_list = []
        for index, file in enumerate(files):
            file_content = base64.b64encode(file.read()).decode('utf-8')
            file_data_list.append({
                'file_content': file_content,
                'filename': file.name,
                'caption': captions[index] if index < len(captions) else '',
                'media_type': media_types[index] if index < len(media_types) else 'image'
            })

        # Queue the upload task
        from .tasks import upload_media_task
        task = upload_media_task.delay(request.user.id, file_data_list)

        return Response({
            'message': _('Upload queued for processing'),
            'task_id': task.id,
            'status': _('Files are being processed in the background')
        }, status=status.HTTP_202_ACCEPTED)


class MediaDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, media_id):
        try:
            media = Media.objects.get(id=media_id, user=request.user)
        except Media.DoesNotExist:
            return Response({'error': _('Media not found')}, status=status.HTTP_404_NOT_FOUND)

        # Queue the deletion task
        from .tasks import delete_media_task
        task = delete_media_task.delay(media_id, request.user.id)

        # Optimistically delete from database (or wait for task completion)
        media.delete()

        return Response({
            'message': _('Deletion queued for processing'),
            'task_id': task.id
        }, status=status.HTTP_202_ACCEPTED)


# Additional views that might be needed
class MediaFileView(APIView):
    """View to serve media files"""
    permission_classes = [IsAuthenticated]

    def get(self, request, media_id):
        try:
            media = Media.objects.get(id=media_id, user=request.user)
        except Media.DoesNotExist:
            return Response({'error': _('Media not found')}, status=status.HTTP_404_NOT_FOUND)

        # Return file response or redirect to cloud storage
        # Implementation depends on specific requirements
        return Response({'message': 'File retrieval not implemented'})


class MediaModerationView(APIView):
    """Admin moderation view for media"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Only admins can access this
        if not request.user.is_staff:
            return Response({'error': _('Permission denied')}, status=status.HTTP_403_FORBIDDEN)
        
        media_list = Media.objects.all().order_by('-uploaded_at')
        serializer = MediaModerationSerializer(media_list, many=True)
        return Response(serializer.data)

    def patch(self, request, media_id):
        """Approve or reject media"""
        if not request.user.is_staff:
            return Response({'error': _('Permission denied')}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            media = Media.objects.get(id=media_id)
        except Media.DoesNotExist:
            return Response({'error': _('Media not found')}, status=status.HTTP_404_NOT_FOUND)

        status_update = request.data.get('status')
        rejection_reason = request.data.get('rejection_reason', '')

        if status_update not in ['approved', 'rejected']:
            return Response({'error': _('Invalid status. Must be "approved" or "rejected"')}, 
                          status=status.HTTP_400_BAD_REQUEST)

        media.status = status_update
        media.rejection_reason = rejection_reason
        media.reviewed_by = request.user
        media.reviewed_at = timezone.now()
        media.save()

        return Response({'message': _('Media {status} successfully').format(status=status_update)})


class AdminDashboardView(APIView):
    """Admin dashboard with statistics"""
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        User = get_user_model()
        
        stats = {
            'total_users': User.objects.count(),
            'total_admins': User.objects.filter(is_staff=True).count(),
            'total_media': Media.objects.count(),
            'pending_media': Media.objects.filter(status='pending').count(),
            'approved_media': Media.objects.filter(status='approved').count(),
            'rejected_media': Media.objects.filter(status='rejected').count(),
        }
        
        return Response(stats)


class AdminUserManagementView(APIView):
    """CRUD operations for user management"""
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        User = get_user_model()
        users = User.objects.all().order_by('-created_at')
        serializer = AdminUserSerializer(users, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        User = get_user_model()
        serializer = AdminUserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            if request.data.get('password'):
                user.set_password(request.data['password'])
                user.save()
            return Response(AdminUserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminUserDetailView(APIView):
    """Detail operations for individual user"""
    permission_classes = [IsAdminUser]
    
    def get(self, request, user_id):
        User = get_user_model()
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': _('User not found')}, status=status.HTTP_404_NOT_FOUND)
        return Response(AdminUserSerializer(user).data)
    
    def put(self, request, user_id):
        User = get_user_model()
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': _('User not found')}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AdminUserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            user = serializer.save()
            if request.data.get('password'):
                user.set_password(request.data['password'])
                user.save()
            return Response(AdminUserSerializer(user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, user_id):
        User = get_user_model()
        try:
            user = User.objects.get(id=user_id)
            if user.is_superuser:
                return Response({'error': _('Cannot delete superuser')}, status=status.HTTP_400_BAD_REQUEST)
            user.delete()
            return Response({'message': 'User deleted successfully'})
        except User.DoesNotExist:
            return Response({'error': _('User not found')}, status=status.HTTP_404_NOT_FOUND)


class AdminToggleStaffView(APIView):
    """Promote or demote user to/from admin"""
    permission_classes = [IsAdminUser]
    
    def post(self, request, user_id):
        User = get_user_model()
        try:
            user = User.objects.get(id=user_id)
            if user.is_superuser:
                return Response({'error': _('Cannot modify superuser status')}, status=status.HTTP_400_BAD_REQUEST)
            
            user.is_staff = request.data.get('is_staff', not user.is_staff)
            user.save()
            
            action = 'promoted to' if user.is_staff else 'demoted from'
            return Response({
                'message': f'User {action} admin',
                'user': AdminUserSerializer(user).data
            })
        except User.DoesNotExist:
            return Response({'error': _('User not found')}, status=status.HTTP_404_NOT_FOUND)


class AdminSettingsView(APIView):
    """Webapp configuration settings"""
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        settings = {
            'site_name': 'Sang Hee & Fabio Wedding',
            'maintenance_mode': False,
            'allow_registrations': True,
            'max_upload_size_mb': 50,
            'require_approval': True,
            'default_language': 'it'
        }
        return Response(settings)
    
    def put(self, request):
        serializer = WebAppSettingsSerializer(data=request.data)
        if serializer.is_valid():
            return Response({
                'message': 'Settings updated successfully',
                'settings': serializer.validated_data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
