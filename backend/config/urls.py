"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from users.views import (
    RegisterView, LoginView, LogoutView, ProfileView,
    MediaListView, MediaUploadView, MediaFileView, MediaDeleteView,
    MyUploadsView, MediaModerationView, MediaModerateSingleView,
    SocialLoginView,
    AdminDashboardView, AdminUserManagementView, AdminUserDetailView,
    AdminToggleStaffView, AdminSettingsView
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),
    path('api/auth/register/', RegisterView.as_view(), name='register'),
    path('api/auth/login/', LoginView.as_view(), name='login'),
    path('api/auth/logout/', LogoutView.as_view(), name='logout'),
    path('api/auth/profile/', ProfileView.as_view(), name='profile'),
    path('api/auth/social/login/', SocialLoginView.as_view(), name='social-login'),
    path('api/auth/media/', MediaListView.as_view(), name='media-list'),
    path('api/auth/media/upload/', MediaUploadView.as_view(), name='media-upload'),
    path('api/auth/media/<int:media_id>/file/', MediaFileView.as_view(), name='media-file'),
    path('api/auth/media/<int:media_id>/', MediaDeleteView.as_view(), name='media-delete'),
    path('api/auth/media/my-uploads/', MyUploadsView.as_view(), name='my-uploads'),
    path('api/auth/media/moderation/', MediaModerationView.as_view(), name='media-moderation'),
    path('api/auth/media/moderation/<int:media_id>/', MediaModerateSingleView.as_view(), name='media-moderate-single'),
    path('api/auth/admin/dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('api/auth/admin/users/', AdminUserManagementView.as_view(), name='admin-users'),
    path('api/auth/admin/users/<int:user_id>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('api/auth/admin/users/<int:user_id>/toggle-staff/', AdminToggleStaffView.as_view(), name='admin-toggle-staff'),
    path('api/auth/admin/settings/', AdminSettingsView.as_view(), name='admin-settings'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
