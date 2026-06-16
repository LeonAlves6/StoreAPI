from django.urls import path
from .views import UpdateUserRoleView, RegisterView, LoginView, ForgotPasswordView, ResetPasswordView, AddressListView, AddressCreateView

urlpatterns = [
    path('users/<uuid:user_id>/role/', UpdateUserRoleView.as_view(), name='update-role'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('addresses/', AddressListView.as_view()),
    path('addresses/create/', AddressCreateView.as_view()),
]