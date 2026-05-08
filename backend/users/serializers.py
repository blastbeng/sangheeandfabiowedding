from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser, Media, SiteSettings


class CustomUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    password_confirm = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'first_name', 'last_name',
                  'date_of_birth', 'password', 'password_confirm', 'language',
                  'profile_picture', 'is_staff', 'is_superuser')
        extra_kwargs = {
            'email': {'required': False, 'allow_blank': True},
            'username': {'required': False},
            'language': {'required': False},
            'profile_picture': {'required': False},
            'is_staff': {'read_only': True},
            'is_superuser': {'read_only': True},
        }

    def validate(self, attrs):
        password = attrs.get('password')
        password_confirm = attrs.get('password_confirm')

        if password:
            if password != password_confirm:
                raise serializers.ValidationError({"password_confirm": "Passwords don't match"})
            try:
                validate_password(password)
            except Exception as e:
                raise serializers.ValidationError({"password": list(e.messages)})

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

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance

    def set_default_profile_picture(self, user):
        import requests
        from django.core.files.base import ContentFile
        try:
            response = requests.get('https://i.imgur.com/V4RclNb.png')
            if response.status_code == 200:
                user.profile_picture.save('default.png', ContentFile(response.content), save=True)
        except Exception as e:
            print(f"Failed to download default profile picture: {e}")


class MediaSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Media
        fields = ('id', 'user', 'file', 'media_type', 'caption',
                  'uploaded_at', 'status', 'view_count', 'file_url')
        read_only_fields = ('user', 'uploaded_at', 'status', 'view_count', 'file_url')

    def get_file_url(self, obj):
        return f"/api/auth/media/{obj.id}/file/"


class PublicMediaSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    uploader_username = serializers.CharField(source='user.username', read_only=True)
    uploader_profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = Media
        fields = (
            'id', 'user', 'file', 'media_type', 'caption',
            'uploaded_at', 'status', 'view_count', 'file_url',
            'uploader_username', 'uploader_profile_picture'
        )
        read_only_fields = fields

    def get_file_url(self, obj):
        return f"/api/auth/media/{obj.id}/file/"

    def get_uploader_profile_picture(self, obj):
        if obj.user and obj.user.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.user.profile_picture.url)
            return obj.user.profile_picture.url
        return None


class MediaModerationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Media
        fields = ('id', 'user', 'username', 'user_email', 'file', 'media_type',
                  'caption', 'uploaded_at', 'status', 'reviewed_at',
                  'reviewed_by', 'rejection_reason', 'view_count', 'file_url')
        read_only_fields = ('user', 'uploaded_at', 'reviewed_by', 'file_url')

    def get_file_url(self, obj):
        return f"/api/auth/media/{obj.id}/file/"


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'first_name', 'last_name',
                  'is_staff', 'is_superuser', 'is_active', 'created_at',
                  'updated_at', 'language', 'profile_picture')
        read_only_fields = ('created_at', 'updated_at')


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = '__all__'


class BulkModerationSerializer(serializers.Serializer):
    media_ids = serializers.ListField(
        child=serializers.IntegerField(), min_length=1
    )
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)


class AdminDashboardSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    total_admins = serializers.IntegerField()
    total_media = serializers.IntegerField()
    pending_media = serializers.IntegerField()
    approved_media = serializers.IntegerField()
    rejected_media = serializers.IntegerField()
    recent_uploads = MediaSerializer(many=True, read_only=True)
