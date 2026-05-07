from django.contrib import admin
from .models import CustomUser, Media, SiteSettings


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'email_verified')
    list_filter = ('is_staff', 'is_active', 'email_verified')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'media_type', 'status', 'uploaded_at', 'view_count')
    list_filter = ('media_type', 'status')
    search_fields = ('caption',)
    ordering = ('-uploaded_at',)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'maintenance_mode', 'allow_registrations', 'default_language')
