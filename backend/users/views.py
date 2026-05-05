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


class RegisterView(APIView):
    """
    Register a new user
    """
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
        media = Media.objects.all()
        serializer = MediaSerializer(media, many=True)
        return Response(serializer.data)


class MediaUploadView(APIView):
    """
    Upload new media (Authenticated)
    """
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

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
        media = Media.objects.all()
        serializer = MediaSerializer(media, many=True)
        return Response(serializer.data)


class MediaUploadView(APIView):
    """
    Upload new media (Authenticated)
    """
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

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
                    params={'fields': 'id,name,email', 'access_token': access_token}
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

            user, created = CustomUser.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0],
                    'first_name': user_data.get('given_name', '') or user_data.get('name', ''),
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
