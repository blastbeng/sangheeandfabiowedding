from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegisterView, LoginView, ProfileView, LogoutView, MediaListView, MediaUploadView, SocialLoginView, MyUploadsView, MediaModerationView, MediaModerateSingleView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('media/', MediaListView.as_view(), name='media-list'),
    path('media/upload/', MediaUploadView.as_view(), name='media-upload'),
    path('media/my-uploads/', MyUploadsView.as_view(), name='my-uploads'),
    path('media/moderation/', MediaModerationView.as_view(), name='media-moderation'),
    path('media/moderation/<int:media_id>/', MediaModerateSingleView.as_view(), name='media-moderate-single'),
    path('social/login/', SocialLoginView.as_view(), name='social-login'),
]
