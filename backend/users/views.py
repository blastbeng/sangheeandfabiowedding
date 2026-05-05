from rest_framework import serializers
from django.contrib.auth import authenticate

class LoginSerializer(serializers.Serializer):
    """
    Serializer for login endpoint
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(request=self.context.get('request'),
                                email=email, password=password)

            if not user:
                raise serializers.ValidationError('Unable to log in with provided credentials.')

            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include "email" and "password".')

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from .models import CustomUser
from .serializers import CustomUserSerializer, LoginSerializer
from .models import Media
from .serializers import MediaSerializer
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import serializers


from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth import authenticate
from rest_framework import serializers
from django.utils import timezone


class LoginSerializer(serializers.Serializer):
    """
    Serializer for login endpoint
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(request=self.context.get('request'),
                                email=email, password=password)

            if not user:
                raise serializers.ValidationError('Unable to log in with provided credentials.')

            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include "email" and "password".')


class RegisterView(APIView):
    """
    Register a new user
    """
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


class MediaListView(APIView):
    """
    List all media (Public)
    """
    permission_classes = [AllowAny]

    def get(self, request):
        media = Media.objects.filter(status='approved')
        serializer = MediaSerializer(media, many=True)
        return Response(serializer.data)


class MediaUploadView(APIView):
    """
    Upload new media (Authenticated)
    """
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        file = request.FILES.get('file')
        caption = request.data.get('caption', '')
        media_type = request.data.get('media_type', 'image')

        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        media = Media.objects.create(
            user=request.user,
            file=file,
            media_type=media_type,
            caption=caption,
            status='pending'
        )

        serializer = MediaSerializer(media)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MyUploadsView(APIView):
    """
    List current user's uploads with status (Authenticated)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        media = Media.objects.filter(user=request.user).order_by('-uploaded_at')
        serializer = MediaSerializer(media, many=True)
        return Response(serializer.data)


class MediaModerationView(APIView):
    """
    Admin moderation endpoint for pending media
    """
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
        """Bulk approve/reject media"""
        media_ids = request.data.get('media_ids', [])
        action = request.data.get('action')  # 'approve' or 'reject'
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
    """
    Admin moderation for single media item
    """
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
class ProfileView(APIView):
    """
    Retrieve or update user profile
    """
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
    """
    List all media (Public)
    """
    permission_classes = [AllowAny]

    def get(self, request):
        media = Media.objects.filter(status='approved')
        serializer = MediaSerializer(media, many=True)
        return Response(serializer.data)


class MediaUploadView(APIView):
    """
    Upload new media (Authenticated)
    """
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        file = request.FILES.get('file')
        caption = request.data.get('caption', '')
        media_type = request.data.get('media_type', 'image')

        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        media = Media.objects.create(
            user=request.user,
            file=file,
            media_type=media_type,
            caption=caption,
            status='pending'
        )

        serializer = MediaSerializer(media)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MyUploadsView(APIView):
    """
    List current user's uploads with status (Authenticated)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        media = Media.objects.filter(user=request.user).order_by('-uploaded_at')
        serializer = MediaSerializer(media, many=True)
        return Response(serializer.data)


class MediaModerationView(APIView):
    """
    Admin moderation endpoint for pending media
    """
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
        """Bulk approve/reject media"""
        media_ids = request.data.get('media_ids', [])
        action = request.data.get('action')  # 'approve' or 'reject'
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
    """
    Admin moderation for single media item
    """
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
class LogoutView(APIView):
    """
    Logout user by blacklisting the refresh token
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)


from allauth.socialaccount.models import SocialAccount
import requests
class SocialLoginView(APIView):
    """
    Handle social authentication from frontend
    """
    permission_classes = [AllowAny]

    def post(self, request):
        provider = request.data.get('provider')
        access_token = request.data.get('access_token')
        custom_username = request.data.get('username', '')

        if not provider or not access_token:
            return Response(
                {'error': 'Provider and access_token required'},
                status=status.HTTP_400_BAD_REQUEST
            )

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
                return Response(
                    {'error': 'Invalid provider'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if response.status_code != 200:
                return Response(
                    {'error': 'Failed to verify token'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user_data = response.json()
            email = user_data.get('email')

            if not email:
                return Response(
                    {'error': 'Email not provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Generate username if not provided
            if not custom_username:
                if provider == 'facebook':
                    name_parts = user_data.get('name', 'user').split()
                    custom_username = f"{name_parts[0]}_{name_parts[-1]}" if len(name_parts) > 1 else name_parts[0]
                elif provider == 'google':
                    given_name = user_data.get('given_name', '')
                    family_name = user_data.get('family_name', '')
                    custom_username = f"{given_name}_{family_name}".strip('_') if given_name or family_name else user_data.get('nickname', 'user')

            # Get profile picture
            profile_picture = 'https://i.imgur.com/V4RclNb.png'
            if provider == 'google':
                profile_picture = user_data.get('picture', profile_picture)
            elif provider == 'facebook':
                picture_data = user_data.get('picture', {})
                if isinstance(picture_data, dict):
                    profile_picture = picture_data.get('data', {}).get('url', profile_picture)

            user, created = CustomUser.objects.get_or_create(
                email=email,
                defaults={
                    'username': custom_username,
                    'first_name': user_data.get('given_name', '') or (user_data.get('name', '').split()[0] if user_data.get('name') else ''),
                    'last_name': user_data.get('family_name', '') or (user_data.get('name', '').split()[-1] if len(user_data.get('name', '').split()) > 1 else ''),
                }
            )

            SocialAccount.objects.get_or_create(
                user=user,
                provider=provider,
                uid=user_data.get('id')
            )

            refresh = RefreshToken.for_user(user)

            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': CustomUserSerializer(user).data,
                'created': created
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
from allauth.socialaccount.models import SocialAccount
import requests
class SocialLoginView(APIView):
    """
    Handle social authentication from frontend
    """
    permission_classes = [AllowAny]

    def post(self, request):
        provider = request.data.get('provider')
        access_token = request.data.get('access_token')
        custom_username = request.data.get('username', '')

        if not provider or not access_token:
            return Response(
                {'error': 'Provider and access_token required'},
                status=status.HTTP_400_BAD_REQUEST
            )

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
                return Response(
                    {'error': 'Invalid provider'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if response.status_code != 200:
                return Response(
                    {'error': 'Failed to verify token'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user_data = response.json()
            email = user_data.get('email')

            if not email:
                return Response(
                    {'error': 'Email not provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Generate username if not provided
            if not custom_username:
                if provider == 'facebook':
                    name_parts = user_data.get('name', 'user').split()
                    custom_username = f"{name_parts[0]}_{name_parts[-1]}" if len(name_parts) > 1 else name_parts[0]
                elif provider == 'google':
                    given_name = user_data.get('given_name', '')
                    family_name = user_data.get('family_name', '')
                    custom_username = f"{given_name}_{family_name}".strip('_') if given_name or family_name else user_data.get('nickname', 'user')

            # Get profile picture
            profile_picture = 'https://i.imgur.com/V4RclNb.png'
            if provider == 'google':
                profile_picture = user_data.get('picture', profile_picture)
            elif provider == 'facebook':
                picture_data = user_data.get('picture', {})
                if isinstance(picture_data, dict):
                    profile_picture = picture_data.get('data', {}).get('url', profile_picture)

            user, created = CustomUser.objects.get_or_create(
                email=email,
                defaults={
                    'username': custom_username,
                    'first_name': user_data.get('given_name', '') or (user_data.get('name', '').split()[0] if user_data.get('name') else ''),
                    'last_name': user_data.get('family_name', '') or (user_data.get('name', '').split()[-1] if len(user_data.get('name', '').split()) > 1 else ''),
                }
            )

            SocialAccount.objects.get_or_create(
                user=user,
                provider=provider,
                uid=user_data.get('id')
            )

            refresh = RefreshToken.for_user(user)

            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': CustomUserSerializer(user).data,
                'created': created
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
