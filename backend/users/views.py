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
