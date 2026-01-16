"""
Tests for invite code and registration module.
"""
import pytest
from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import User, UserRole, InviteCode, InviteCodeStatus, WechatSession
from apps.users.services import InviteCodeService, RegistrationService


@pytest.fixture
def api_client():
    """Return an API client."""
    return APIClient()


@pytest.fixture
def super_admin(db):
    """Create a super admin user."""
    return User.objects.create_superuser(
        username='admin',
        password='adminpass123',
        email='admin@example.com'
    )


@pytest.fixture
def item_manager(db):
    """Create an item manager user."""
    return User.objects.create_user(
        username='manager',
        password='managerpass123',
        email='manager@example.com',
        role=UserRole.ITEM_MANAGER
    )


@pytest.fixture
def invite_code_service():
    """Return an InviteCodeService instance."""
    return InviteCodeService()


@pytest.fixture
def registration_service():
    """Return a RegistrationService instance."""
    return RegistrationService()


@pytest.fixture
def valid_invite_code(db, super_admin, invite_code_service):
    """Create a valid invite code."""
    return invite_code_service.create(
        max_uses=10,
        default_role=UserRole.ITEM_MANAGER,
        created_by=super_admin
    )


class TestInviteCodeModel:
    """Tests for InviteCode model."""
    
    def test_status_active(self, db, super_admin, invite_code_service):
        """Test invite code status is active when usable."""
        code = invite_code_service.create(
            max_uses=5,
            default_role=UserRole.READ_ONLY_USER,
            created_by=super_admin
        )
        
        assert code.status == InviteCodeStatus.ACTIVE
        assert code.is_usable is True
    
    def test_status_exhausted(self, db, super_admin, invite_code_service):
        """Test invite code status is exhausted when max uses reached."""
        code = invite_code_service.create(
            max_uses=1,
            default_role=UserRole.READ_ONLY_USER,
            created_by=super_admin
        )
        code.current_uses = 1
        code.save()
        
        assert code.status == InviteCodeStatus.EXHAUSTED
        assert code.is_usable is False
    
    def test_status_expired(self, db, super_admin, invite_code_service):
        """Test invite code status is expired when past expiration."""
        code = invite_code_service.create(
            max_uses=5,
            default_role=UserRole.READ_ONLY_USER,
            created_by=super_admin,
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        assert code.status == InviteCodeStatus.EXPIRED
        assert code.is_usable is False
    
    def test_status_disabled(self, db, super_admin, invite_code_service):
        """Test invite code status is disabled when is_active=False."""
        code = invite_code_service.create(
            max_uses=5,
            default_role=UserRole.READ_ONLY_USER,
            created_by=super_admin,
            is_active=False
        )
        
        assert code.status == InviteCodeStatus.DISABLED
        assert code.is_usable is False
    
    def test_remaining_uses(self, db, super_admin, invite_code_service):
        """Test remaining uses calculation."""
        code = invite_code_service.create(
            max_uses=10,
            default_role=UserRole.READ_ONLY_USER,
            created_by=super_admin
        )
        code.current_uses = 3
        code.save()
        
        assert code.remaining_uses == 7


class TestInviteCodeService:
    """Tests for InviteCodeService."""
    
    def test_create_generates_unique_code(self, db, super_admin, invite_code_service):
        """Test that create generates a unique code in INV-XXXXXX format."""
        code = invite_code_service.create(
            max_uses=5,
            default_role=UserRole.ITEM_MANAGER,
            created_by=super_admin
        )
        
        assert code.code.startswith('INV-')
        assert len(code.code) == 10  # INV- + 6 chars
        assert code.max_uses == 5
        assert code.default_role == UserRole.ITEM_MANAGER
        assert code.created_by == super_admin
    
    def test_validate_and_use_success(self, db, valid_invite_code, invite_code_service):
        """Test successful validation and use of invite code."""
        initial_uses = valid_invite_code.current_uses
        
        result = invite_code_service.validate_and_use(valid_invite_code.code)
        
        assert result.id == valid_invite_code.id
        assert result.current_uses == initial_uses + 1
    
    def test_validate_and_use_invalid_code(self, db, invite_code_service):
        """Test validation fails for non-existent code."""
        from rest_framework.exceptions import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            invite_code_service.validate_and_use('INVALID-CODE')
        
        assert 'invite_code' in exc_info.value.detail
    
    def test_validate_and_use_exhausted_code(self, db, valid_invite_code, invite_code_service):
        """Test validation fails for exhausted code."""
        from rest_framework.exceptions import ValidationError
        
        valid_invite_code.current_uses = valid_invite_code.max_uses
        valid_invite_code.save()
        
        with pytest.raises(ValidationError) as exc_info:
            invite_code_service.validate_and_use(valid_invite_code.code)
        
        assert 'maximum uses' in str(exc_info.value.detail)
    
    def test_validate_and_use_expired_code(self, db, super_admin, invite_code_service):
        """Test validation fails for expired code."""
        from rest_framework.exceptions import ValidationError
        
        code = invite_code_service.create(
            max_uses=5,
            default_role=UserRole.READ_ONLY_USER,
            created_by=super_admin,
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        with pytest.raises(ValidationError) as exc_info:
            invite_code_service.validate_and_use(code.code)
        
        assert 'expired' in str(exc_info.value.detail)
    
    def test_validate_and_use_disabled_code(self, db, valid_invite_code, invite_code_service):
        """Test validation fails for disabled code."""
        from rest_framework.exceptions import ValidationError
        
        valid_invite_code.is_active = False
        valid_invite_code.save()
        
        with pytest.raises(ValidationError) as exc_info:
            invite_code_service.validate_and_use(valid_invite_code.code)
        
        assert 'disabled' in str(exc_info.value.detail)
    
    def test_disable(self, db, valid_invite_code, invite_code_service, super_admin):
        """Test disabling an invite code."""
        result = invite_code_service.disable(valid_invite_code.id, super_admin)
        
        assert result.is_active is False
        assert result.status == InviteCodeStatus.DISABLED


class TestInviteCodeAPI:
    """Tests for invite code API endpoints."""
    
    def test_list_invite_codes_super_admin(self, api_client, super_admin, valid_invite_code):
        """Test super admin can list invite codes."""
        # Login as super admin
        login_response = api_client.post('/api/v1/auth/login/', {
            'username': 'admin',
            'password': 'adminpass123'
        })
        access_token = login_response.data['access']
        
        # List invite codes
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = api_client.get('/api/v1/invite-codes/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
    
    def test_list_invite_codes_non_admin_forbidden(self, api_client, item_manager, valid_invite_code):
        """Test non-admin cannot list invite codes."""
        # Login as item manager
        login_response = api_client.post('/api/v1/auth/login/', {
            'username': 'manager',
            'password': 'managerpass123'
        })
        access_token = login_response.data['access']
        
        # Try to list invite codes
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = api_client.get('/api/v1/invite-codes/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_create_invite_code_super_admin(self, api_client, super_admin):
        """Test super admin can create invite codes."""
        # Login as super admin
        login_response = api_client.post('/api/v1/auth/login/', {
            'username': 'admin',
            'password': 'adminpass123'
        })
        access_token = login_response.data['access']
        
        # Create invite code
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = api_client.post('/api/v1/invite-codes/', {
            'max_uses': 5,
            'default_role': UserRole.ITEM_MANAGER
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['code'].startswith('INV-')
        assert response.data['max_uses'] == 5
        assert response.data['default_role'] == UserRole.ITEM_MANAGER
    
    def test_update_invite_code_super_admin(self, api_client, super_admin, valid_invite_code):
        """Test super admin can update invite codes."""
        # Login as super admin
        login_response = api_client.post('/api/v1/auth/login/', {
            'username': 'admin',
            'password': 'adminpass123'
        })
        access_token = login_response.data['access']
        
        # Update invite code
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = api_client.patch(f'/api/v1/invite-codes/{valid_invite_code.id}/', {
            'max_uses': 20,
            'is_active': False
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['max_uses'] == 20
        assert response.data['is_active'] is False


class TestRegistrationService:
    """Tests for RegistrationService."""
    
    def test_initiate_wechat_oauth(self, registration_service):
        """Test WeChat OAuth URL generation."""
        url = registration_service.initiate_wechat_oauth()
        
        assert 'open.weixin.qq.com' in url
        assert 'appid=' in url
        assert 'redirect_uri=' in url
    
    def test_handle_wechat_callback(self, db, registration_service):
        """Test WeChat callback creates session."""
        result = registration_service.handle_wechat_callback(
            code='test_code_123',
            state='test_state'
        )
        
        assert result.session_id is not None
        assert result.openid.startswith('mock_openid_')
        
        # Verify session was created in database
        session = WechatSession.objects.get(session_id=result.session_id)
        assert session.openid == result.openid
    
    def test_register_success(self, db, valid_invite_code, registration_service):
        """Test successful user registration."""
        # Create WeChat session
        callback_result = registration_service.handle_wechat_callback(
            code='test_code',
            state='test_state'
        )
        
        # Register user
        user = registration_service.register(
            wechat_session_id=callback_result.session_id,
            invite_code=valid_invite_code.code,
            username='newuser',
            password='newpassword123',
            phone='13800138000',
            email='newuser@example.com',
            department='Engineering'
        )
        
        assert user.username == 'newuser'
        assert user.role == valid_invite_code.default_role
        assert user.wechat_openid == callback_result.openid
        assert user.phone == '13800138000'
        
        # Verify invite code usage was incremented
        valid_invite_code.refresh_from_db()
        assert valid_invite_code.current_uses == 1
        
        # Verify session was deleted
        assert not WechatSession.objects.filter(session_id=callback_result.session_id).exists()
    
    def test_register_invalid_session(self, db, valid_invite_code, registration_service):
        """Test registration fails with invalid session."""
        from rest_framework.exceptions import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            registration_service.register(
                wechat_session_id='invalid_session',
                invite_code=valid_invite_code.code,
                username='newuser',
                password='newpassword123'
            )
        
        assert 'wechat_session_id' in exc_info.value.detail
    
    def test_register_invalid_invite_code(self, db, registration_service):
        """Test registration fails with invalid invite code."""
        from rest_framework.exceptions import ValidationError
        
        # Create valid session
        callback_result = registration_service.handle_wechat_callback(
            code='test_code',
            state='test_state'
        )
        
        with pytest.raises(ValidationError) as exc_info:
            registration_service.register(
                wechat_session_id=callback_result.session_id,
                invite_code='INVALID-CODE',
                username='newuser',
                password='newpassword123'
            )
        
        assert 'invite_code' in exc_info.value.detail
    
    def test_register_duplicate_username(self, db, valid_invite_code, registration_service, item_manager):
        """Test registration fails with duplicate username."""
        from rest_framework.exceptions import ValidationError
        
        # Create valid session
        callback_result = registration_service.handle_wechat_callback(
            code='test_code',
            state='test_state'
        )
        
        with pytest.raises(ValidationError) as exc_info:
            registration_service.register(
                wechat_session_id=callback_result.session_id,
                invite_code=valid_invite_code.code,
                username='manager',  # Already exists
                password='newpassword123'
            )
        
        assert 'username' in exc_info.value.detail


class TestRegistrationAPI:
    """Tests for registration API endpoints."""
    
    def test_wechat_authorize(self, api_client, db):
        """Test WeChat authorize endpoint."""
        response = api_client.get('/api/v1/auth/wechat/authorize/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'authorize_url' in response.data
        assert 'open.weixin.qq.com' in response.data['authorize_url']
    
    def test_wechat_callback(self, api_client, db):
        """Test WeChat callback endpoint."""
        response = api_client.post('/api/v1/auth/wechat/callback/', {
            'code': 'test_auth_code',
            'state': 'test_state'
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert 'session_id' in response.data
        assert 'nickname' in response.data
    
    def test_register_endpoint(self, api_client, valid_invite_code):
        """Test registration endpoint."""
        # First get a WeChat session
        callback_response = api_client.post('/api/v1/auth/wechat/callback/', {
            'code': 'test_auth_code',
            'state': 'test_state'
        })
        session_id = callback_response.data['session_id']
        
        # Register
        response = api_client.post('/api/v1/auth/register/', {
            'wechat_session_id': session_id,
            'invite_code': valid_invite_code.code,
            'username': 'apiuser',
            'password': 'apipassword123',
            'phone': '13900139000',
            'email': 'apiuser@example.com'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['username'] == 'apiuser'
        assert response.data['role'] == valid_invite_code.default_role
        assert 'message' in response.data
