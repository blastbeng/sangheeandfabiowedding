from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """
    Custom User model extending Django's AbstractUser
    """
    email = models.EmailField(unique=True)
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

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name or self.email.split('@')[0]

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
    # Cloud storage fields
    nextcloud_file_id = models.CharField(max_length=255, null=True, blank=True)
    google_drive_file_id = models.CharField(max_length=255, null=True, blank=True)
    view_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.media_type} by {self.user.email if self.user else 'Guest'} ({self.status})"

    class Meta:
        db_table = 'users_media'
        ordering = ['-uploaded_at']
