"""
URL configuration for users app.
"""
from django.urls import path

from .security_views import InviteCodeDetailView, LogoutView
from .views import (
    LoginView,
    RefreshView,
    UserMeView,
    UserListView,
    UserDisableView,
    UserResetPasswordView,
    UserCreateView,
    ChangePasswordView,
    AdminSetPasswordView,
    UserEnableView,
    UserUpdateRoleView,
    InviteCodeListCreateView,
    WechatAuthorizeView,
    WechatCallbackView,
    RegisterView,
    SimpleRegisterView,
)

app_name = 'users'

# Auth endpoints
auth_urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('refresh/', RefreshView.as_view(), name='refresh'),
    path('wechat/authorize/', WechatAuthorizeView.as_view(), name='wechat-authorize'),
    path('wechat/callback/', WechatCallbackView.as_view(), name='wechat-callback'),
    path('register/', SimpleRegisterView.as_view(), name='register'),
    path('register/wechat/', RegisterView.as_view(), name='register-wechat'),
]

# User endpoints
user_urlpatterns = [
    path('', UserListView.as_view(), name='user-list'),
    path('me/', UserMeView.as_view(), name='me'),
    path('me/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('create/', UserCreateView.as_view(), name='user-create'),
    path('<int:pk>/disable/', UserDisableView.as_view(), name='user-disable'),
    path('<int:pk>/enable/', UserEnableView.as_view(), name='user-enable'),
    path('<int:pk>/reset-password/', UserResetPasswordView.as_view(), name='user-reset-password'),
    path('<int:pk>/set-password/', AdminSetPasswordView.as_view(), name='user-set-password'),
    path('<int:pk>/update-role/', UserUpdateRoleView.as_view(), name='user-update-role'),
]

# Invite code endpoints
invite_code_urlpatterns = [
    path('', InviteCodeListCreateView.as_view(), name='invite-code-list-create'),
    path('<int:pk>/', InviteCodeDetailView.as_view(), name='invite-code-detail'),
]

urlpatterns = []
