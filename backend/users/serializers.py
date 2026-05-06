from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser
from .models import Media


class CustomUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 
                  'date_of_birth', 'password', 'password_confirm', 'language')
        extra_kwargs = {
            'email': {'required': True},
            'language': {'required': False},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        validated_data.setdefault('language', 'it')
        user = CustomUser.objects.create_user(**validated_data)
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


class MediaSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    reviewer_username = serializers.CharField(source='reviewed_by.username', read_only=True, allow_null=True)

    class Meta:
        model = Media
        fields = ['id', 'file', 'file_url', 'media_type', 'caption', 'uploaded_at', 'user', 'status', 'reviewed_at', 'reviewer_username', 'rejection_reason']
        read_only_fields = ['user', 'uploaded_at']

    def get_file_url(self, obj):
        return f'/api/auth/media/{obj.id}/file/'


class MediaModerationSerializer(serializers.ModelSerializer):
    """Serializer for admin moderation with additional fields"""
    username = serializers.CharField(source='user.username', read_only=True, allow_null=True)
    user_email = serializers.CharField(source='user.email', read_only=True, allow_null=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Media
        fields = ['id', 'file', 'file_url', 'media_type', 'caption', 'uploaded_at', 'status', 'username', 'user_email', 'rejection_reason']
        read_only_fields = ['uploaded_at', 'username', 'user_email']

    def get_file_url(self, obj):
        return f'/api/auth/media/{obj.id}/file/'


class SocialLoginSerializer(serializers.Serializer):
    """
    Serializer for social authentication
    """
    provider = serializers.CharField(required=True)
    access_token = serializers.CharField(required=True)


class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer for admin user management"""
    is_staff = serializers.BooleanField(default=False)
    is_superuser = serializers.BooleanField(default=False)
    
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 
                  'date_of_birth', 'is_active', 'is_staff', 'is_superuser', 
                  'created_at', 'language')
        read_only_fields = ('created_at',)

    def create(self, validated_data):
        password = validated_data.pop('password', 'defaultpassword123')
        user = CustomUser.objects.create_user(password=password, **validated_data)
        return user

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class WebAppSettingsSerializer(serializers.Serializer):
    """Serializer for webapp configuration"""
    site_name = serializers.CharField(max_length=100, required=False)
    maintenance_mode = serializers.BooleanField(default=False)
    allow_registrations = serializers.BooleanField(default=True)
    max_upload_size_mb = serializers.IntegerField(default=50)
    require_approval = serializers.BooleanField(default=True)
    default_language = serializers.CharField(max_length=10, default='it')
