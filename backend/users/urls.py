from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, VerifyEmailView, LoginView, PasswordResetRequestView,
    PasswordResetConfirmView, ProfileView, LogoutView, SocialLoginView,
    SocialLoginRedirectView, SocialLoginCallbackView,
    MediaListView, MediaUploadView, MediaDeleteView, MyUploadsView,
    MediaModerationView, MediaModerateSingleView, MediaFileView,
    PublicMediaListView, AdminDashboardView, AdminSettingsView,
    AdminUserListView, AdminUserDetailView, AdminUserToggleStaffView,
    MediaBulkModerationView, TaskStatusView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('login/', LoginView.as_view(), name='login'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-reset-confirm/<str:uidb64>/<str:token>/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('social/login/', SocialLoginView.as_view(), name='social-login'),
    path('social/facebook/', SocialLoginRedirectView.as_view(provider='facebook'), name='social-facebook'),
    path('social/instagram/', SocialLoginRedirectView.as_view(provider='instagram'), name='social-instagram'),
    path('social/callback/', SocialLoginCallbackView.as_view(), name='social-login-callback'),
    path('media/', MediaListView.as_view(), name='media-list'),
    path('media/upload/', MediaUploadView.as_view(), name='media-upload'),
    path('media/upload/status/<str:task_id>/', TaskStatusView.as_view(), name='upload-task-status'),
    path('media/<int:media_id>/', MediaDeleteView.as_view(), name='media-delete'),
    path('media/my-uploads/', MyUploadsView.as_view(), name='my-uploads'),
    path('media/moderation/', MediaModerationView.as_view(), name='media-moderation'),
    path('media/moderation/<int:media_id>/', MediaModerateSingleView.as_view(), name='media-moderate-single'),
    path('media/moderation/bulk/', MediaBulkModerationView.as_view(), name='media-moderation-bulk'),
    path('media/<int:media_id>/file/', MediaFileView.as_view(), name='media-file'),
    path('media/public/', PublicMediaListView.as_view(), name='media-public'),
    path('admin/dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('admin/settings/', AdminSettingsView.as_view(), name='admin-settings'),
    path('admin/users/', AdminUserListView.as_view(), name='admin-user-list'),
    path('admin/users/<int:user_id>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('admin/users/<int:user_id>/toggle-staff/', AdminUserToggleStaffView.as_view(), name='admin-user-toggle-staff'),
]
