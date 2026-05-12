from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that returns structured error codes
    when the user is inactive or deleted, so the frontend can
    handle these cases explicitly (e.g. force logout with a message).
    """
    def get_user(self, validated_token):
        """
        Override to return a custom error code when the user is inactive or deleted.
        """
        try:
            user = super().get_user(validated_token)
        except AuthenticationFailed as e:
            detail_str = str(e.detail).lower() if e.detail else ''
            if 'inactive' in detail_str:
                raise AuthenticationFailed({
                    'code': 'user_deactivated',
                    'detail': 'User account is deactivated.'
                })
            elif 'not found' in detail_str:
                raise AuthenticationFailed({
                    'code': 'user_deleted',
                    'detail': 'User account no longer exists.'
                })
            raise  # re-raise any other authentication failure

        # Double-check active status (should already be handled, but just in case)
        if not user.is_active:
            raise AuthenticationFailed({
                'code': 'user_deactivated',
                'detail': 'User account is deactivated.'
            })
        return user
