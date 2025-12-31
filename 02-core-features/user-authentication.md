---
title: User Accounts & Authentication
category: core-features
dependencies: django-allauth-headless
styleguide: hacksoft-django-styleguide
lichess_equivalent: lila/modules/user, lila/modules/security, lila/modules/oauth
status: complete
---

# User Accounts & Authentication Specification

This document specifies the user authentication system for our Django/React Lichess clone.

> **Styleguide Reference**: This implementation follows the [Hacksoft Django Styleguide](/.claude/skills/hacksoft-django-styleguide/SKILL.md). User creation logic belongs in **services** (e.g., `user_create`), not in serializer `create()` methods. The frontend uses **django-allauth headless** for authentication (see [init-django-backend skill](/.claude/skills/init-django-backend/SKILL.md)).

## Overview

Lichess uses a custom authentication system built on Play Framework with OAuth2 support. Our Django implementation leverages **django-allauth headless** for a React SPA:

| Lichess | Our Stack |
|---------|-----------|
| lila/modules/user | Custom Django User model |
| lila/modules/security | django-allauth headless + rate limiting |
| lila/modules/oauth | django-allauth social providers |
| Session-based auth | Session tokens via allauth headless (`/_allauth/browser/v1/`) |

## User Model

### Custom User Model

```python
# <project_slug>/users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Custom user model for chess platform.

    Extends Django's AbstractUser with chess-specific fields.
    """

    # Profile
    bio = models.TextField(max_length=500, blank=True)
    country = models.CharField(max_length=2, blank=True)  # ISO 3166-1 alpha-2
    location = models.CharField(max_length=100, blank=True)

    # Chess-specific
    fide_rating = models.PositiveIntegerField(null=True, blank=True)
    title = models.CharField(max_length=10, blank=True, choices=[
        ('GM', 'Grandmaster'),
        ('IM', 'International Master'),
        ('FM', 'FIDE Master'),
        ('CM', 'Candidate Master'),
        ('WGM', 'Woman Grandmaster'),
        ('WIM', 'Woman International Master'),
        ('WFM', 'Woman FIDE Master'),
        ('WCM', 'Woman Candidate Master'),
        ('NM', 'National Master'),
        ('LM', 'Lichess Master'),  # Titled on our platform
    ])

    # Account status
    is_patron = models.BooleanField(default=False)  # Supporter
    is_verified = models.BooleanField(default=False)  # Email verified
    is_bot = models.BooleanField(default=False)  # Bot account

    # Privacy settings
    profile_visible = models.BooleanField(default=True)
    online_status_visible = models.BooleanField(default=True)

    # Timestamps
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['is_bot']),
        ]

    def __str__(self):
        return self.username

    @property
    def display_name(self):
        """Username with title prefix if applicable."""
        if self.title:
            return f"{self.title} {self.username}"
        return self.username
```

### Username Validation

```python
# <project_slug>/users/validators.py
import re
from django.core.exceptions import ValidationError

USERNAME_REGEX = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]{1,19}$')
RESERVED_USERNAMES = {
    'admin', 'administrator', 'lichess', 'api', 'www',
    'anonymous', 'system', 'bot', 'engine', 'stockfish',
}

def validate_username(value: str) -> None:
    """
    Validate username according to Lichess-like rules:
    - 2-20 characters
    - Must start with a letter
    - Only alphanumeric, underscore, hyphen allowed
    - Case insensitive uniqueness
    """
    if not USERNAME_REGEX.match(value):
        raise ValidationError(
            'Username must be 2-20 characters, start with a letter, '
            'and contain only letters, numbers, underscores, or hyphens.'
        )

    if value.lower() in RESERVED_USERNAMES:
        raise ValidationError('This username is reserved.')

    # Check case-insensitive uniqueness
    from <project_slug>.users.models import User
    if User.objects.filter(username__iexact=value).exists():
        raise ValidationError('A user with this username already exists.')
```

## Authentication Configuration

### django-allauth Setup

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.github',
    # ...
]

SITE_ID = 1

# Allauth settings
ACCOUNT_AUTHENTICATION_METHOD = 'username_email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_USERNAME_VALIDATORS = '<project_slug>.users.validators.username_validators'
ACCOUNT_USERNAME_MIN_LENGTH = 2
ACCOUNT_USERNAME_MAX_LENGTH = 20
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True

# Rate limiting
ACCOUNT_LOGIN_ATTEMPTS_LIMIT = 5
ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT = 300  # 5 minutes

# Session settings
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30  # 30 days
SESSION_COOKIE_SECURE = True  # Production
SESSION_COOKIE_HTTPONLY = True
```

### JWT Authentication (API)

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
}

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

## API Endpoints

Following the Hacksoft pattern: APIs are thin wrappers that delegate to **services** for business logic.

### User Services (Business Logic)

```python
# <project_slug>/users/services.py
from django.db import transaction
from django.contrib.auth import get_user_model, authenticate
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from allauth.account.utils import send_email_confirmation
from typing import Optional, Dict, Any

User = get_user_model()


@transaction.atomic
def user_create(
    *,
    username: str,
    email: str,
    password: str,
    request=None,  # For email confirmation
) -> User:
    """
    Create a new user account and send verification email.

    Raises ValidationError if username/email already exists.
    """
    user = User(username=username, email=email)
    user.set_password(password)
    user.full_clean()
    user.save()

    # Send verification email
    if request:
        send_email_confirmation(request, user)

    return user


def user_login(
    *,
    username: str,
    password: str,
) -> Optional[Dict[str, Any]]:
    """
    Authenticate user and return JWT tokens.

    Attempts authentication by username first, then by email.
    Updates last_seen_at on successful login.

    Returns:
        None if authentication fails
        {'error': 'email_not_verified', 'user': user} if email not verified
        {'user': user, 'access': token, 'refresh': token} on success
    """
    # Try username authentication
    user = authenticate(username=username, password=password)

    if not user:
        # Try email login
        try:
            user_obj = User.objects.get(email__iexact=username)
            user = authenticate(username=user_obj.username, password=password)
        except User.DoesNotExist:
            pass

    if not user:
        return None

    if not user.is_verified:
        return {'error': 'email_not_verified', 'user': user}

    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)

    # Update last seen
    user.last_seen_at = timezone.now()
    user.save(update_fields=['last_seen_at'])

    return {
        'user': user,
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


@transaction.atomic
def user_update_last_seen(
    *,
    user: User,
) -> User:
    """Update user's last_seen_at timestamp."""
    user.last_seen_at = timezone.now()
    user.save(update_fields=['last_seen_at'])
    return user
```

### Registration

```python
# <project_slug>/users/apis.py
from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from <project_slug>.users.services import user_create


class RegisterApi(APIView):
    """
    User registration endpoint.

    POST /api/auth/register/
    """
    permission_classes = [AllowAny]

    class InputSerializer(serializers.Serializer):
        username = serializers.CharField(min_length=2, max_length=20)
        email = serializers.EmailField()
        password = serializers.CharField(min_length=8, write_only=True)

    class OutputSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        username = serializers.CharField()
        email = serializers.EmailField()

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Delegate to service
        user = user_create(
            username=serializer.validated_data['username'],
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
            request=request,
        )

        output = self.OutputSerializer(user)
        return Response({
            'message': 'Registration successful. Please check your email.',
            'user': output.data,
        }, status=status.HTTP_201_CREATED)
```

### Login

```python
# <project_slug>/users/apis.py (continued)
from <project_slug>.users.services import user_login

class LoginApi(APIView):
    """
    User login endpoint. Returns JWT tokens.

    POST /api/auth/login/
    """
    permission_classes = [AllowAny]

    class InputSerializer(serializers.Serializer):
        username = serializers.CharField()
        password = serializers.CharField(write_only=True)

    class OutputSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        username = serializers.CharField()
        display_name = serializers.CharField()

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Delegate to service - no business logic in API
        result = user_login(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password'],
        )

        if result is None:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if result.get('error') == 'email_not_verified':
            return Response(
                {'error': 'Please verify your email address before logging in.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response({
            'access': result['access'],
            'refresh': result['refresh'],
            'user': self.OutputSerializer(result['user']).data,
        })
```

### Token Refresh

```python
# <project_slug>/users/apis.py (continued)
from rest_framework_simplejwt.views import TokenRefreshView

class TokenRefreshApi(TokenRefreshView):
    """
    Refresh access token.

    POST /api/auth/refresh/
    {
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
    """
    pass
```

### Current User

```python
# <project_slug>/users/apis.py (continued)
from rest_framework.permissions import IsAuthenticated

class UserMeApi(APIView):
    """
    Get current authenticated user.

    GET /api/auth/me/
    """
    permission_classes = [IsAuthenticated]

    class OutputSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        username = serializers.CharField()
        email = serializers.EmailField()
        display_name = serializers.CharField()
        title = serializers.CharField(allow_blank=True)
        is_patron = serializers.BooleanField()
        is_verified = serializers.BooleanField()

    def get(self, request):
        serializer = self.OutputSerializer(request.user)
        return Response(serializer.data)
```

### Password Reset

First, add the password reset service:

```python
# <project_slug>/users/services.py (add to existing services)
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes


def password_reset_token_create(
    *,
    email: str,
) -> Optional[Dict[str, Any]]:
    """
    Generate password reset token for user with given email.

    Returns None if no user exists with that email (for security).
    Returns dict with 'uid', 'token', and 'user' on success.
    """
    try:
        user = User.objects.get(email__iexact=email)
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        return {'uid': uid, 'token': token, 'user': user}
    except User.DoesNotExist:
        return None
```

Then the API:

```python
# <project_slug>/users/apis.py (continued)
from <project_slug>.users.services import password_reset_token_create

class PasswordResetRequestApi(APIView):
    """
    Request password reset email.

    POST /api/auth/password/reset/
    """
    permission_classes = [AllowAny]

    class InputSerializer(serializers.Serializer):
        email = serializers.EmailField()

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Delegate to service - no business logic in API
        result = password_reset_token_create(
            email=serializer.validated_data['email'],
        )

        # TODO: If result is not None, send email with reset link
        # reset_url = f"{settings.FRONTEND_URL}/reset-password/{result['uid']}/{result['token']}/"
        # send_password_reset_email(result['user'].email, reset_url)

        # Always return success message (don't reveal if email exists)
        return Response({
            'message': 'If an account with that email exists, a password reset link has been sent.'
        })
```

## Serializers (Input Validation Only)

Serializers handle validation only—no `create()` method per Hacksoft pattern:

```python
# <project_slug>/users/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

class RegisterInputSerializer(serializers.Serializer):
    """Input validation for registration. No create() method per Hacksoft."""
    username = serializers.CharField(max_length=20)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    def validate_username(self, value):
        from <project_slug>.users.validators import validate_username
        validate_username(value)
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        return attrs

    # NOTE: No create() method - user creation is handled by user_create service


class UserSerializer(serializers.ModelSerializer):
    display_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'display_name', 'title',
            'bio', 'country', 'location',
            'is_patron', 'is_verified', 'is_bot',
            'date_joined', 'last_seen_at',
        ]
        read_only_fields = ['id', 'date_joined', 'last_seen_at', 'is_verified']


class PublicUserSerializer(serializers.ModelSerializer):
    """Limited user data for public profiles."""
    display_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = ['id', 'username', 'display_name', 'title', 'country', 'is_patron', 'is_bot']
```

## URL Configuration

```python
# <project_slug>/users/urls.py
from django.urls import path
from <project_slug>.users import apis

urlpatterns = [
    path('register/', apis.RegisterApi.as_view(), name='register'),
    path('login/', apis.LoginApi.as_view(), name='login'),
    path('refresh/', apis.TokenRefreshApi.as_view(), name='token_refresh'),
    path('me/', apis.UserMeApi.as_view(), name='me'),
    path('password/reset/', apis.PasswordResetRequestApi.as_view(), name='password_reset'),
]
```

## Social Authentication

### OAuth2 Providers

```python
# settings.py
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    },
    'github': {
        'SCOPE': ['read:user', 'user:email'],
    },
}

# Auto-connect social accounts to existing users with same email
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
```

### Social Auth APIs

```python
# <project_slug>/users/apis.py (continued)
class SocialAuthApi(APIView):
    """
    Social authentication callback.

    POST /api/auth/social/{provider}/
    {
        "code": "oauth_code_from_provider",
        "redirect_uri": "https://example.com/callback"
    }
    """
    permission_classes = [AllowAny]

    def post(self, request, provider):
        from allauth.socialaccount.providers.oauth2.client import OAuth2Client
        from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
        from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter

        adapters = {
            'google': GoogleOAuth2Adapter,
            'github': GitHubOAuth2Adapter,
        }

        adapter_class = adapters.get(provider)
        if not adapter_class:
            return Response({'error': 'Invalid provider'}, status=400)

        # Process OAuth callback and get/create user
        # Return JWT tokens
        # ...
```

## Security Features

### Rate Limiting

```python
# <project_slug>/users/throttling.py
from rest_framework.throttling import AnonRateThrottle

class LoginRateThrottle(AnonRateThrottle):
    rate = '5/minute'

class RegisterRateThrottle(AnonRateThrottle):
    rate = '3/hour'

class PasswordResetRateThrottle(AnonRateThrottle):
    rate = '3/hour'
```

### Account Security

```python
# <project_slug>/users/models.py (additional)
class LoginHistory(models.Model):
    """Track login attempts for security."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    success = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['ip_address', '-timestamp']),
        ]


class ActiveSession(models.Model):
    """Track active sessions for session management."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'session_key']
```

### Two-Factor Authentication (Future)

```python
# <project_slug>/users/models.py (additional)
class TwoFactorAuth(models.Model):
    """TOTP-based two-factor authentication."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='two_factor')
    secret = models.CharField(max_length=32)
    is_enabled = models.BooleanField(default=False)
    backup_codes = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
```

## Frontend Integration

### Auth Context

```typescript
// frontend/src/contexts/AuthContext.tsx
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api } from '@/lib/api';

interface User {
  id: number;
  username: string;
  displayName: string;
  title?: string;
  isPatron: boolean;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  register: (username: string, email: string, password: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check for existing auth on mount
    const token = localStorage.getItem('accessToken');
    if (token) {
      fetchUser();
    } else {
      setIsLoading(false);
    }
  }, []);

  const fetchUser = async () => {
    try {
      const response = await api.get('/auth/me/');
      setUser(response.data);
    } catch {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (username: string, password: string) => {
    const response = await api.post('/auth/login/', { username, password });
    localStorage.setItem('accessToken', response.data.access);
    localStorage.setItem('refreshToken', response.data.refresh);
    setUser(response.data.user);
  };

  const logout = () => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    setUser(null);
  };

  const register = async (username: string, email: string, password: string) => {
    await api.post('/auth/register/', {
      username,
      email,
      password,
      password_confirm: password,
    });
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, register }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
```

### API Client with Token Refresh

```typescript
// frontend/src/lib/api.ts
import axios from 'axios';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
});

// Add access token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('accessToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle token refresh on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = localStorage.getItem('refreshToken');
      if (refreshToken) {
        try {
          const response = await axios.post('/api/auth/refresh/', {
            refresh: refreshToken,
          });
          localStorage.setItem('accessToken', response.data.access);
          originalRequest.headers.Authorization = `Bearer ${response.data.access}`;
          return api(originalRequest);
        } catch {
          // Refresh failed, logout
          localStorage.removeItem('accessToken');
          localStorage.removeItem('refreshToken');
          window.location.href = '/login';
        }
      }
    }

    return Promise.reject(error);
  }
);
```

## WebSocket Authentication

```python
# <project_slug>/users/middleware.py
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

@database_sync_to_async
def get_user_from_token(token_key):
    from django.contrib.auth import get_user_model
    User = get_user_model()

    try:
        access_token = AccessToken(token_key)
        user_id = access_token.payload.get('user_id')
        return User.objects.get(id=user_id)
    except (InvalidToken, TokenError, User.DoesNotExist):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """Authenticate WebSocket connections using JWT token from query string."""

    async def __call__(self, scope, receive, send):
        query_string = scope.get('query_string', b'').decode()
        params = dict(x.split('=') for x in query_string.split('&') if '=' in x)
        token = params.get('token')

        if token:
            scope['user'] = await get_user_from_token(token)
        else:
            scope['user'] = AnonymousUser()

        return await super().__call__(scope, receive, send)
```

## Sources

- [Hacksoft Django Styleguide](https://github.com/HackSoftware/Django-Styleguide)
- [django-allauth Documentation](https://django-allauth.readthedocs.io/)
- [djangorestframework-simplejwt](https://django-rest-framework-simplejwt.readthedocs.io/)
- [lila/modules/user](https://github.com/lichess-org/lila/tree/master/modules/user)
- [lila/modules/security](https://github.com/lichess-org/lila/tree/master/modules/security)
- [OWASP Authentication Guidelines](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
