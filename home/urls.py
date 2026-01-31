
from django.urls import path, include
from .import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
urlpatterns = [
    
    path("demodata",views.demodata, name="demodata"),
    path('user_registration/', views.user_registration, name='user_registration'),
    path('get_user_data/<int:pk>/', views.get_user_data, name='get_user_data'),
    path('profile/update/', views.UserProfileUpdateView.as_view(), name='profile-update'),
    path('generate_otp/', views.generate_otp, name='generate_otp'),
    path('register/verify-otp/', views.verify_registration_otp, name='verify_registration_otp'),
    path('register/resend-otp/', views.resend_registration_otp, name='resend_registration_otp'),

    path('verify_otp_and_login/', views.verify_otp_and_login, name='verify_otp_and_login'),

    # path('auth/google/', views.google_login, name='google_login'),
    path('auth/google/callback/', views.google_callback, name='google_callback'),
    path("auth/google/", views.GoogleAuthView.as_view(), name="google_auth"),
    path('logout/', views.logout, name='logout'),

    #user management

    path('admin/users/', views.ListAllUsers.as_view(), name='list-users'),
    path('admin/user/<int:user_id>/toggle-active/',  views.ToggleUserActiveStatus.as_view(), name='toggle-user-active'),
    path('admin/user/<int:user_id>/delete/',  views.DeleteUserByAdmin.as_view(), name='delete-user-by-admin'),
    path('user/delete/',  views.DeleteOwnAccount.as_view(), name='delete-own-account'),


    
]

router.register(r'admin-emails', views.AdminEmailsViewSet, basename='admin-emails')
router.register(r'delivery-addresses', views.DeliveryAddressViewSet, basename='delivery-address')

urlpatterns +=router.urls

