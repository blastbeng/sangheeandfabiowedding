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
            'email': {'required': False, 'allow_blank': True},
            'username': {'required': True},
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
    """Serializer for displaying media to users"""
    class Meta:
        model = Media
        fields = ('id', 'user', 'file', 'media_type', 'caption', 
                  'uploaded_at', 'status', 'view_count')
        read_only_fields = ('user', 'uploaded_at', 'status', 'view_count')

    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None


class MediaModerationSerializer(serializers.ModelSerializer):
    """Serializer for admin media moderation"""
    username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Media
        fields = ('id', 'user', 'username', 'user_email', 'file', 'media_type', 
                  'caption', 'uploaded_at', 'status', 'reviewed_at', 
                  'reviewed_by', 'rejection_reason', 'view_count')
        read_only_fields = ('user', 'uploaded_at', 'reviewed_by')


class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer for admin user management"""
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 
                  'is_staff', 'is_superuser', 'is_active', 'created_at', 
                  'updated_at', 'language')
        read_only_fields = ('created_at', 'updated_at')


class WebAppSettingsSerializer(serializers.Serializer):
    """Serializer for webapp settings"""
    site_name = serializers.CharField(max_length=255)
    maintenance_mode = serializers.BooleanField()
    allow_registrations = serializers.BooleanField()
    max_upload_size_mb = serializers.IntegerField()
    require_approval = serializers.BooleanField()
    default_language = serializers.CharField(max_length=10)
