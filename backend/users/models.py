import os
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings as django_settings


class CustomUser(AbstractUser):
    """
    Custom User model extending Django's AbstractUser
    """
    email = models.EmailField(unique=True, blank=True, null=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    language = models.CharField(max_length=10, default='it', choices=[
        ('it', 'Italiano'),
        ('ko', '한국어'),
        ('en', 'English'),
    ])
    email_verified = models.BooleanField(default=False)
    profile_picture = models.ImageField(
        upload_to='profile_pics/',
        null=True,
        blank=True,
        default='profile_pics/default.png'
    )
    
    # Override groups and user_permissions to avoid reverse accessor clashes
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='customuser_groups',
        related_query_name='customuser',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='customuser_permissions',
        related_query_name='customuser',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return self.username

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name or self.email.split('@')[0] if self.email else self.username

    class Meta:
        db_table = 'users_customuser'


class Media(models.Model):
    """
    Model for storing guest and spouse uploads
    """
    MEDIA_TYPES = (
        ('image', 'Image'),
        ('video', 'Video'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='uploaded_media'
    )
    file = models.FileField(upload_to='wedding_uploads/', null=True, blank=True)
    original_filename = models.CharField(max_length=255, null=True, blank=True)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES)
    caption = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='reviewed_media'
    )
    rejection_reason = models.TextField(blank=True, null=True)
    # Cloud storage field
    nextcloud_file_id = models.CharField(max_length=255, null=True, blank=True)
    view_count = models.IntegerField(default=0)

    class Meta:
        db_table = 'users_media'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.media_type} - {self.caption or 'Untitled'} - {self.status}"


class SiteSettings(models.Model):
    """Singleton model for webapp settings"""
    site_name = models.CharField(max_length=255, default='Sang Hee & Fabio')
    maintenance_mode = models.BooleanField(default=False)
    allow_registrations = models.BooleanField(default=True)
    max_upload_size_mb = models.IntegerField(default=50)
    require_approval = models.BooleanField(default=True)
    default_language = models.CharField(max_length=10, default='it', choices=[
        ('it', 'Italiano'),
        ('ko', '한국어'),
        ('en', 'English'),
    ])
    # Google OAuth
    google_client_id = models.CharField(max_length=255, blank=True, null=True)
    google_client_secret = models.CharField(max_length=255, blank=True, null=True)
    # Facebook OAuth
    facebook_app_id = models.CharField(max_length=255, blank=True, null=True)
    facebook_app_secret = models.CharField(max_length=255, blank=True, null=True)
    # Instagram OAuth
    instagram_app_id = models.CharField(max_length=255, blank=True, null=True)
    instagram_app_secret = models.CharField(max_length=255, blank=True, null=True)
    # Nextcloud
    nextcloud_url = models.CharField(max_length=255, blank=True, null=True)
    nextcloud_username = models.CharField(max_length=255, blank=True, null=True)
    nextcloud_password = models.CharField(max_length=255, blank=True, null=True)
    nextcloud_folder = models.CharField(max_length=255, blank=True, null=True)
    # SMTP
    email_host = models.CharField(max_length=255, blank=True, null=True)
    email_port = models.IntegerField(null=True, blank=True)
    email_use_tls = models.BooleanField(default=True)
    email_host_user = models.CharField(max_length=255, blank=True, null=True)
    email_host_password = models.CharField(max_length=255, blank=True, null=True)
    default_from_email = models.EmailField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'users_site_settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        updated = False

        # Map model field names to django settings attributes
        field_map = {
            'google_client_id': 'GOOGLE_CLIENT_ID',
            'google_client_secret': 'GOOGLE_CLIENT_SECRET',
            'facebook_app_id': 'FACEBOOK_APP_ID',
            'facebook_app_secret': 'FACEBOOK_APP_SECRET',
            'instagram_app_id': 'INSTAGRAM_APP_ID',
            'instagram_app_secret': 'INSTAGRAM_APP_SECRET',
            'nextcloud_url': 'NEXTCLOUD_URL',
            'nextcloud_username': 'NEXTCLOUD_USERNAME',
            'nextcloud_password': 'NEXTCLOUD_PASSWORD',
            'nextcloud_folder': 'NEXTCLOUD_FOLDER',
            'email_host': 'EMAIL_HOST',
            'email_port': 'EMAIL_PORT',
            'email_use_tls': 'EMAIL_USE_TLS',
            'email_host_user': 'EMAIL_HOST_USER',
            'email_host_password': 'EMAIL_HOST_PASSWORD',
            'default_from_email': 'DEFAULT_FROM_EMAIL',
        }

        for field, setting_name in field_map.items():
            env_value = getattr(django_settings, setting_name, None)
            if env_value is None:
                env_value = os.environ.get(setting_name, '')
            # Convert to appropriate type for the model field
            if isinstance(env_value, bool):
                pass  # already bool
            elif field == 'email_port':
                env_value = int(env_value) if env_value != '' else None
            elif field == 'email_use_tls':
                env_value = bool(env_value)
            else:
                env_value = str(env_value) if env_value else ''

            current = getattr(obj, field)
            if current != env_value:
                setattr(obj, field, env_value)
                updated = True

        if updated:
            obj.save()

        return obj


class FaceTag(models.Model):
    media = models.ForeignKey(Media, on_delete=models.CASCADE, related_name='face_tags')
    name = models.CharField(max_length=100, default='Unknown')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('media', 'name')

    def __str__(self):
        return f"{self.name} in {self.media}"
