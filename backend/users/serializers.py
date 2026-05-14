import logging
import os
from rest_framework import serializers
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, Media, SiteSettings, FaceGroup, FaceTag, CookieConsent
from .profanity_words import contains_profanity
from .nsfw_utils import check_nsfw_image, is_image_file

logger = logging.getLogger(__name__)


class CustomUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    password_confirm = serializers.CharField(write_only=True, required=False, allow_blank=True)
    profile_picture_url = serializers.SerializerMethodField()
    has_password = serializers.SerializerMethodField()
    is_default_admin = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'first_name', 'last_name',
                  'date_of_birth', 'password', 'password_confirm', 'language',
                  'profile_picture', 'profile_picture_url',
                  'is_staff', 'is_superuser', 'has_password', 'is_default_admin')
        extra_kwargs = {
            'email': {'required': False, 'allow_blank': True},
            'username': {'required': False},
            'language': {'required': False},
            'profile_picture': {'required': False},
            'is_staff': {'read_only': True},
            'is_superuser': {'read_only': True},
        }

    def get_profile_picture_url(self, obj):
        request = self.context.get('request')
        url = f'/api/auth/users/{obj.id}/profile-picture/'
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_has_password(self, obj):
        return obj.has_usable_password()

    def get_is_default_admin(self, obj):
        default_admin_username = os.getenv('ADMIN_USERNAME')
        default_admin_email = os.getenv('ADMIN_EMAIL')
        return obj.is_superuser and (
            obj.username == default_admin_username or obj.email == default_admin_email
        )

    def validate(self, attrs):
        password = attrs.get('password')
        password_confirm = attrs.get('password_confirm')

        if password:
            if password != password_confirm:
                raise serializers.ValidationError({"password_confirm": _("Passwords don't match")})
            try:
                validate_password(password)
            except Exception as e:
                raise serializers.ValidationError({"password": list(e.messages)})

        # Check for duplicate email during registration
        if self.instance is None and attrs.get('email'):
            email = attrs['email']
            if CustomUser.objects.filter(email=email).exists():
                raise serializers.ValidationError({"email": "An account with this email already exists."})

        # Check for duplicate username during registration
        if self.instance is None and attrs.get('username'):
            username = attrs['username']
            if CustomUser.objects.filter(username=username).exists():
                raise serializers.ValidationError({"username": "This username is already taken."})

        # Check for profanity in text fields
        for field in ['username', 'first_name', 'last_name']:
            if field in attrs and attrs[field] and contains_profanity(str(attrs[field])):
                raise serializers.ValidationError({
                    field: _("Content contains inappropriate language")
                })

        # Check for NSFW content in profile picture
        if 'profile_picture' in attrs:
            is_nsfw, confidence = check_nsfw_image(attrs['profile_picture'])
            if is_nsfw:
                raise serializers.ValidationError({
                    'profile_picture': _("Image contains inappropriate content")
                })

        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm', None)
        password = validated_data.pop('password', None)

        if not password:
            raise serializers.ValidationError({"password": "Password is required"})

        validated_data.setdefault('language', 'it')
        validated_data['is_active'] = False
        validated_data['email_verified'] = False
        user = CustomUser.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()

        if not user.profile_picture or user.profile_picture.name == 'profile_pics/default.png':
            self.set_default_profile_picture(user)
        return user

    def update(self, instance, validated_data):
        validated_data.pop('password_confirm', None)
        password = validated_data.pop('password', None)

        # Handle profile picture replacement
        new_picture = validated_data.pop('profile_picture', None)
        if new_picture:
            # Delete old picture if it's not the default
            if instance.profile_picture and instance.profile_picture.name != 'profile_pics/default.png':
                instance.profile_picture.delete(save=False)
            instance.profile_picture = new_picture

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()

        # Trigger face detection on new profile picture
        if new_picture:
            from .tasks import detect_faces_profile_picture
            detect_faces_profile_picture.delay(instance.id)

        return instance

    def set_default_profile_picture(self, user):
        from django.core.files.base import ContentFile
        try:
            default_pic_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'default_profile_pic.png')
            with open(default_pic_path, 'rb') as f:
                user.profile_picture.save('default.png', ContentFile(f.read()), save=True)
        except Exception as e:
            print(f"Failed to set default profile picture: {e}")


class PublicUserSerializer(serializers.ModelSerializer):
    profile_picture_url = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'first_name', 'last_name', 'profile_picture_url', 'language')
        read_only_fields = fields

    def get_profile_picture_url(self, obj):
        request = self.context.get('request')
        url = f'/api/auth/users/{obj.id}/profile-picture/'
        if request:
            return request.build_absolute_uri(url)
        return url


class MediaSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Media
        fields = ('id', 'user', 'file', 'media_type', 'caption',
                  'uploaded_at', 'status', 'view_count', 'file_url')
        read_only_fields = ('user', 'uploaded_at', 'status', 'view_count', 'file_url')

    def get_file_url(self, obj):
        return f"/api/auth/media/{obj.id}/file/"

    def validate(self, attrs):
        # Check for profanity in caption
        if 'caption' in attrs and attrs['caption'] and contains_profanity(str(attrs['caption'])):
            raise serializers.ValidationError({
                'caption': _("Content contains inappropriate language")
            })

        # Check for NSFW content in uploaded file (if it's an image)
        if 'file' in attrs and is_image_file(attrs['file']):
            is_nsfw, confidence = check_nsfw_image(attrs['file'])
            if is_nsfw:
                raise serializers.ValidationError({
                    'file': _("Image contains inappropriate content")
                })

        return attrs


class PublicMediaSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    uploader_username = serializers.CharField(source='user.username', read_only=True)
    uploader_first_name = serializers.CharField(source='user.first_name', read_only=True)
    uploader_last_name = serializers.CharField(source='user.last_name', read_only=True)
    uploader_profile_picture = serializers.SerializerMethodField()
    face_tags = serializers.SerializerMethodField()
    user_id = serializers.IntegerField(source='user.id', read_only=True)

    class Meta:
        model = Media
        fields = (
            'id', 'user', 'file', 'media_type', 'caption',
            'uploaded_at', 'status', 'view_count', 'file_url',
            'uploader_username', 'uploader_first_name', 'uploader_last_name',
            'uploader_profile_picture', 'face_tags', 'user_id',
        )
        read_only_fields = fields

    def get_file_url(self, obj):
        return f"/api/auth/media/{obj.id}/file/"

    def get_uploader_profile_picture(self, obj):
        if obj.user:
            request = self.context.get('request')
            url = f'/api/auth/users/{obj.user.id}/profile-picture/'
            if request:
                return request.build_absolute_uri(url)
            return url
        return None

    def get_face_tags(self, obj):
        tags = obj.face_tags.select_related('face_group').all()
        result = []
        for tag in tags:
            if tag.face_group:
                result.append({
                    'group_id': tag.face_group.id,
                    'thumbnail_url': self._get_group_thumbnail(tag.face_group),
                })
        return result

    def _get_group_thumbnail(self, group):
        if group.thumbnail:
            request = self.context.get('request')
            url = group.thumbnail.url
            if request:
                return request.build_absolute_uri(url)
            return url
        return None


class MediaModerationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Media
        fields = ('id', 'user', 'username', 'user_email', 'file', 'media_type',
                  'caption', 'uploaded_at', 'status', 'reviewed_at',
                  'reviewed_by', 'view_count', 'file_url')
        read_only_fields = ('user', 'uploaded_at', 'reviewed_by', 'file_url')

    def get_file_url(self, obj):
        return f"/api/auth/media/{obj.id}/file/"


class AdminUserSerializer(serializers.ModelSerializer):
    profile_picture_url = serializers.SerializerMethodField()
    profile_picture = serializers.ImageField(required=False, write_only=True)
    remove_profile_picture = serializers.BooleanField(write_only=True, required=False, default=False)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    password_confirm = serializers.CharField(write_only=True, required=False, allow_blank=True)
    username = serializers.CharField(max_length=150, required=True)
    is_default_admin = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'first_name', 'last_name',
                  'is_staff', 'is_superuser', 'is_active', 'email_verified',
                  'created_at', 'updated_at', 'language', 'profile_picture', 'profile_picture_url',
                  'remove_profile_picture', 'password', 'password_confirm', 'is_default_admin')
        read_only_fields = ('created_at', 'updated_at')

    def get_profile_picture_url(self, obj):
        request = self.context.get('request')
        url = f'/api/auth/users/{obj.id}/profile-picture/'
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_is_default_admin(self, obj):
        return obj.username == os.getenv('ADMIN_USERNAME') and obj.is_superuser

    def validate(self, attrs):
        password = attrs.get('password')
        password_confirm = attrs.get('password_confirm')
        if password:
            if password != password_confirm:
                raise serializers.ValidationError({"password_confirm": _("Passwords don't match")})

        # Check for profanity in text fields
        for field in ['username', 'first_name', 'last_name']:
            if field in attrs and attrs[field] and contains_profanity(str(attrs[field])):
                raise serializers.ValidationError({
                    field: _("Content contains inappropriate language")
                })

        # Check for NSFW content in profile picture
        if 'profile_picture' in attrs:
            is_nsfw, confidence = check_nsfw_image(attrs['profile_picture'])
            if is_nsfw:
                raise serializers.ValidationError({
                    'profile_picture': _("Image contains inappropriate content")
                })

        return attrs

    def update(self, instance, validated_data):
        validated_data.pop('password_confirm', None)
        password = validated_data.pop('password', None)
        remove_pic = validated_data.pop('remove_profile_picture', False)
        new_picture = validated_data.pop('profile_picture', None)

        if new_picture:
            if instance.profile_picture and instance.profile_picture.name != 'profile_pics/default.png':
                instance.profile_picture.delete(save=False)
            instance.profile_picture = new_picture
        elif remove_pic:
            if instance.profile_picture and instance.profile_picture.name != 'profile_pics/default.png':
                instance.profile_picture.delete(save=False)

        instance = super().update(instance, validated_data)

        if password:
            instance.set_password(password)
            instance.save()

        if remove_pic and not new_picture:
            self._set_default_profile_picture(instance)

        # Trigger face detection if a new picture was uploaded
        if new_picture:
            from .tasks import detect_faces_profile_picture
            detect_faces_profile_picture.delay(instance.id)

        return instance

    def _set_default_profile_picture(self, user):
        from django.core.files.base import ContentFile
        try:
            default_pic_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'default_profile_pic.png')
            with open(default_pic_path, 'rb') as f:
                user.profile_picture.save('default.png', ContentFile(f.read()), save=True)
        except Exception as e:
            logger.error(f"Failed to set default profile picture: {e}")


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = '__all__'


class BulkModerationSerializer(serializers.Serializer):
    media_ids = serializers.ListField(
        child=serializers.IntegerField(), min_length=1
    )
    action = serializers.ChoiceField(choices=['approve', 'reject', 'delete'])


class AdminDashboardSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    total_admins = serializers.IntegerField()
    total_media = serializers.IntegerField()
    pending_media = serializers.IntegerField()
    approved_media = serializers.IntegerField()
    rejected_media = serializers.IntegerField()
    recent_uploads = MediaSerializer(many=True, read_only=True)


class FaceGroupSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()
    user_id = serializers.IntegerField(source='user.id', read_only=True, allow_null=True)
    user_display_name = serializers.SerializerMethodField()

    class Meta:
        model = FaceGroup
        fields = ['id', 'name', 'thumbnail_url', 'user_id', 'user_display_name']

    def get_thumbnail_url(self, obj):
        if obj.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
            return obj.thumbnail.url
        return None

    def get_user_display_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return None


class FaceTagSerializer(serializers.ModelSerializer):
    face_group_id = serializers.IntegerField(source='face_group.id', read_only=True)
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = FaceTag
        fields = ('id', 'media', 'face_group_id', 'name', 'thumbnail', 'thumbnail_url', 'created_at')
        read_only_fields = ('id', 'media', 'created_at')

    def get_thumbnail_url(self, obj):
        if obj.thumbnail:
            request = self.context.get('request')
            url = obj.thumbnail.url
            if request:
                return request.build_absolute_uri(url)
            return url
        return None


class CookieConsentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CookieConsent
        fields = ('id', 'user', 'analytics', 'marketing', 'necessary', 'created_at', 'updated_at')
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')
