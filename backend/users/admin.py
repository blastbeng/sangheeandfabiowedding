from django.contrib import admin
from django.contrib import messages
from .models import CustomUser, Media, SiteSettings, FailedAttempt
import os


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'email_verified')
    list_filter = ('is_staff', 'is_active', 'email_verified')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)

    def delete_model(self, request, obj):
        default_admin_username = os.getenv('ADMIN_USERNAME')
        if obj.is_superuser and obj.username == default_admin_username:
            self.message_user(
                request,
                'Cannot delete the default superuser account.',
                level=messages.ERROR
            )
            return
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        default_admin_username = os.getenv('ADMIN_USERNAME')
        protected = queryset.filter(is_superuser=True, username=default_admin_username)
        if protected.exists():
            self.message_user(
                request,
                'Cannot delete the default superuser account.',
                level=messages.ERROR
            )
            # Remove the protected user from the queryset and delete the rest
            queryset = queryset.exclude(pk__in=protected.values_list('pk', flat=True))
        super().delete_queryset(request, queryset)


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'media_type', 'status', 'uploaded_at', 'view_count')
    list_filter = ('media_type', 'status')
    search_fields = ('caption',)
    ordering = ('-uploaded_at',)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'maintenance_mode', 'allow_registrations', 'default_language')


@admin.register(FailedAttempt)
class FailedAttemptAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'endpoint', 'timestamp')
    list_filter = ('endpoint',)
    search_fields = ('ip_address',)
