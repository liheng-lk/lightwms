"""
Tests for authentication module.
"""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import User, UserRole
from apps.users.services import AuthService


@pytest.fixture
def api_client():
    """Return an API client."""
    return APIClient()


@pytest.fixture
def test_user(db):
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        password='testpass123',
        email='test@example.com',
        role=UserRole.ITEM_MANAGER
    )


@pytest.fixture
def super_admin(db):
    """Create a super admin user."""
    return User.objects.create_superuser(
        username='admin',
        password='adminpass123',
        email='admin@example.com'
    )


class TestLoginEndpoint:
    """Tests for POST /api/v1/auth/login/"""
    
    def test_login_success(self, api_client, test_user):
        """Test successful login returns tokens."""
        response = api_client.post('/api/v1/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
    
    def test_login_invalid_password(self, api_client, test_user):
        """Test login with invalid password returns 401."""
        response = api_client.post('/api/v1/auth/login/', {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_nonexistent_user(self, api_client, db):
        """Test login with non-existent user returns 401."""
        response = api_client.post('/api/v1/auth/login/', {
            'username': 'nonexistent',
            'password': 'somepassword'
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_disabled_user(self, api_client, test_user):
        """Test login with disabled user returns 401."""
        test_user.is_active = False
        test_user.save()
        
        response = api_client.post('/api/v1/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestLogoutEndpoint:
    """Tests for POST /api/v1/auth/logout/"""
    
    def test_logout_success(self, api_client, test_user):
        """Test successful logout blacklists token."""
        # First login
        login_response = api_client.post('/api/v1/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        access_token = login_response.data['access']
        refresh_token = login_response.data['refresh']
        
        # Logout
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        logout_response = api_client.post('/api/v1/auth/logout/', {
            'refresh': refresh_token
        })
        
        assert logout_response.status_code == status.HTTP_200_OK
    
    def test_logout_without_auth(self, api_client, db):
        """Test logout without authentication returns 401."""
        response = api_client.post('/api/v1/auth/logout/', {
            'refresh': 'some_token'
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestRefreshEndpoint:
    """Tests for POST /api/v1/auth/refresh/"""
    
    def test_refresh_success(self, api_client, test_user):
        """Test successful token refresh."""
        # First login
        login_response = api_client.post('/api/v1/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        refresh_token = login_response.data['refresh']
        
        # Refresh
        refresh_response = api_client.post('/api/v1/auth/refresh/', {
            'refresh': refresh_token
        })
        
        assert refresh_response.status_code == status.HTTP_200_OK
        assert 'access' in refresh_response.data
        assert 'refresh' in refresh_response.data
        # New refresh token should be different (rotation)
        assert refresh_response.data['refresh'] != refresh_token
    
    def test_refresh_invalid_token(self, api_client, db):
        """Test refresh with invalid token returns 401."""
        response = api_client.post('/api/v1/auth/refresh/', {
            'refresh': 'invalid_token'
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestUserMeEndpoint:
    """Tests for GET /api/v1/users/me/"""
    
    def test_get_current_user(self, api_client, test_user):
        """Test getting current user info."""
        # Login
        login_response = api_client.post('/api/v1/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        access_token = login_response.data['access']
        
        # Get user info
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = api_client.get('/api/v1/users/me/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['username'] == 'testuser'
        assert response.data['role'] == UserRole.ITEM_MANAGER
    
    def test_get_current_user_without_auth(self, api_client, db):
        """Test getting user info without auth returns 401."""
        response = api_client.get('/api/v1/users/me/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAuthService:
    """Tests for AuthService."""
    
    def test_login_creates_login_log(self, db, test_user):
        """Test that login creates a LoginLog entry."""
        from apps.audit.models import LoginLog
        
        auth_service = AuthService()
        
        # Successful login
        auth_service.login(
            username='testuser',
            password='testpass123',
            ip='127.0.0.1',
            user_agent='Test Agent'
        )
        
        # Check LoginLog was created
        log = LoginLog.objects.filter(username_attempted='testuser').first()
        assert log is not None
        assert log.success is True
        assert log.user == test_user
        assert log.ip == '127.0.0.1'
    
    def test_failed_login_creates_login_log(self, db, test_user):
        """Test that failed login creates a LoginLog entry."""
        from apps.audit.models import LoginLog
        from rest_framework.exceptions import AuthenticationFailed
        
        auth_service = AuthService()
        
        # Failed login
        with pytest.raises(AuthenticationFailed):
            auth_service.login(
                username='testuser',
                password='wrongpassword',
                ip='127.0.0.1',
                user_agent='Test Agent'
            )
        
        # Check LoginLog was created
        log = LoginLog.objects.filter(username_attempted='testuser').first()
        assert log is not None
        assert log.success is False
