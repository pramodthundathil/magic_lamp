from django.shortcuts import render, redirect, get_object_or_404
import json
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils.decorators import method_decorator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import CustomUserSerializer, DeliveryAddressSerializer, UserProfileUpdateSerializer
from .models import CustomUser
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication

from django.shortcuts import get_object_or_404
from django.core.cache import cache
from rest_framework_simplejwt.tokens import RefreshToken
import random
from django.conf import settings
from django.core.mail import send_mail,EmailMessage
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site


from social_django.utils import load_strategy
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model


from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action


from .models import DeliveryAddress
from .serializers import DeliveryAddressSerializer

#swagger authentication

from rest_framework.permissions import BasePermission

class IsAuthenticatedForSwagger(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

# Create your views here.
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['id'] = user.id  # This should match 'id'
        token['first_name'] = user.first_name
        return token

    
class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


from rest_framework import permissions

class IsAdmin(permissions.BasePermission):
    """
    Custom permission to only allow admin users to access this view.
    """
    permission_classes = [IsAuthenticated]
    def has_permission(self, request, view):
        # Check if the user is authenticated and has the 'admin' role
        return request.user and request.user.role == 'admin'



# google login 

from django.shortcuts import redirect
from social_django.utils import psa

@csrf_exempt
@psa('social:complete')
def google_login(request):
    google_auth_url = request.backend.auth_url()
    return redirect(google_auth_url)

# google registration 


#google login 

from django.dispatch import receiver
# from social_django.signals import social_auth_registered
from django.contrib.auth.models import User

def create_user(backend, user, response, *args, **kwargs):
    """
    Custom user creation pipeline.
    Called if the user does not exist during authentication.
    """
    if not user:
        user_data = {
            'email': response.get('email'),
            'first_name': response.get('given_name'),
            'last_name': response.get('family_name'),
        }
        return {
            'is_new': True,
            'user': User.objects.create_user(**user_data)
        }




# Google Authentication callback class 
from google.auth.transport import requests
from google.oauth2 import id_token
from django.conf import settings

User = get_user_model()

class GoogleAuthView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"error": "Token is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Verify token with Google
            google_info = id_token.verify_oauth2_token(
                token, 
                requests.Request(), 
                settings.GOOGLE_CLIENT_ID
            )

            # Check if the token is expired
            if google_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                return Response({"error": "Wrong issuer"}, status=status.HTTP_400_BAD_REQUEST)

            if 'email' not in google_info:
                return Response({"error": "Invalid Google token"}, status=status.HTTP_400_BAD_REQUEST)

            email = google_info["email"]
            google_id = google_info["sub"]
            name = google_info.get("name", "")
            profile_picture = google_info.get("picture", "")

            user, created = User.objects.get_or_create(email=email, defaults={
                "email": email,
                'first_name':name,
                "google_id": google_id,
                "profile_picture_url": profile_picture,
                "is_google_authenticated": True,
            })

            if not created:
                user.google_id = google_id
                user.profile_picture_url = profile_picture
                user.is_google_authenticated = True
                user.save()

            # Generate JWT token
            if user.is_active:

                refresh = RefreshToken.for_user(user)
                return Response({
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.first_name,
                    "profile_picture": user.profile_picture_url
                    }
                }, status=status.HTTP_200_OK)
            
            else:
                return Response(
                    {"message": "User is inactive.", "is_active": False},
                    status=status.HTTP_403_FORBIDDEN
                )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def google_callback(request):
    strategy = load_strategy(request)
    auth_backend = 'google-oauth2'

    # Extract the authorization code from the query parameters
    code = request.GET.get('code')
    if not code:
        return Response({'error': 'Authorization code not provided.'}, status=400)

    # Exchange code for token
    try:
        backend = strategy.get_backend(auth_backend)
        user = backend.do_auth(code)

        if not user:
            return Response({'error': 'Authentication failed.'}, status=400)

        # Generate JWT token
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        })
    except Exception as e:
        return Response({'error': str(e)}, status=400)
    

from django.conf import settings
# OTP Generation
@api_view(['POST'])
@permission_classes([AllowAny])
def generate_otp(request):
    identifier = request.data.get('identifier')  # Email or phone number
    if not identifier:
        return Response(
            {'error': 'Email or phone number is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user = CustomUser.objects.get(email=identifier) if '@' in identifier else CustomUser.objects.get(phone_number=identifier)
        if not user.is_active:
            return Response(
            {'error': 'This user is in active contact administrator.',"is_active":False},
            status=status.HTTP_404_NOT_FOUND
        )

    except CustomUser.DoesNotExist:
        return Response(
            {'error': 'User does not exist.'},
            status=status.HTTP_404_NOT_FOUND
        )
    # Generate a 6-digit OTP
    otp = random.randint(100000, 999999)

    # Save OTP in cache for 5 minutes
    cache.set(f'otp_{identifier}', otp, timeout=300)  # 300 seconds = 5 minutes

    # Simulate sending OTP 
    print(f"OTP for {identifier}: {otp}")
    email = user.email

    if email:
        current_site = get_current_site(request)
        mail_subject = 'OTP for Account LOGIN -  Magic Lamp'
        path = "SignUp"
        message = render_to_string('emailbody_otp.html', {'user': user,
                                                            'domain': current_site.domain,
                                                            'path':path,
                                                            'token':otp,})

        email = EmailMessage(mail_subject, message, to=[email])
        email.content_subtype = "html"
        email.send(fail_silently=True)

    return Response(
        {'message': 'OTP sent successfully.',"OTP":otp},
        status=status.HTTP_200_OK
    )


# OTP Verification and Token Issuance
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp_and_login(request):
    identifier = request.data.get('identifier')
    otp = request.data.get('otp')

    if not identifier or not otp:
        return Response(
            {'error': 'Identifier and OTP are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Retrieve OTP from cache
    stored_otp = cache.get(f'otp_{identifier}')
    if stored_otp is None or str(stored_otp) != str(otp):
        return Response(
            {'error': 'Invalid or expired OTP.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check if user exists
    try:
        user = CustomUser.objects.get(email=identifier) if '@' in identifier else CustomUser.objects.get(phone_number=identifier)
    except CustomUser.DoesNotExist:
        return Response(
            {'error': 'User does not exist.'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Generate JWT tokens
    print(user,"-----------------")
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token

    is_admin = user.is_superuser,
    role = user.role
    # Remove OTP from cache after successful verification
    cache.delete(f'otp_{identifier}')
    print({
            'refresh': str(refresh),
            'access': str(access),
            'message': 'Token Creation successful.',
            'is_admin':is_admin,
            "role":role
        })

    return Response(
        {
            'refresh': str(refresh),
            'access': str(access),
            'message': 'Token Creation successful.',
            'is_admin':is_admin[0],
            "role":role
        },
        status=status.HTTP_200_OK
    )


# User Creation from api User model CustomUser serializer from home.serializer.py CustomUserSerializer


# Helper function to generate and send OTP
def generate_and_send_otp(identifier):
    # Generate a 6-digit OTP
    otp = random.randint(100000, 999999)
    
    # Store OTP in cache with 10 minutes expiry
    cache.set(f'otp_{identifier}', otp, timeout=600)
    
    # Determine if identifier is email or phone
    if '@' in identifier:
        # Send OTP via email
        subject = 'Your Registration OTP'
        message = f'Your OTP for registration is: {otp}. This OTP is valid for 10 minutes.'
        try:
            email = identifier
            mail_subject = 'OTP for Account Creation -  Magic Lamp'
            path = "SignUp"
            message = render_to_string('emailbody_otp.html', {'user': "Test User",
                                                
                                                        'token':otp,})

            email = EmailMessage(mail_subject, message, to=[email])
            email.content_subtype = "html"
            email.send(fail_silently=True)
            return True, f"OTP sent to your email successfully.OTP - {otp}"
        except Exception as e:
            return False, f"Failed to send OTP via email: {str(e)}"


# User Registration
@api_view(['POST'])
@permission_classes([AllowAny])
def user_registration(request):
    
    # Get user data
    email = request.data.get('email')
    phone_number = request.data.get('phone_number')
    
    # Check if required fields exist
    if not email and not phone_number:
        return Response(
            {"detail": "Email or phone number is required."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if user already exists
    if email and CustomUser.objects.filter(email=email).exists():
        return Response(
            {"detail": "A user with this email already exists."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if phone_number and CustomUser.objects.filter(phone_number=phone_number).exists():
        return Response(
            {"detail": "A user with this phone number already exists."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate data using serializer (without saving)
    serializer = CustomUserSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Store user data in cache for verification step
    registration_data = request.data.copy()
    identifier = email if email else phone_number
    cache.set(f'registration_data_{identifier}', registration_data, timeout=600)
    
    # Generate and send OTP
    success, message = generate_and_send_otp(identifier)
    
    if success:
        return Response(
            {
                "message": "Registration initiated successfully. Please verify with OTP.",
                "detail": message,
                "identifier": identifier
            },
            status=status.HTTP_200_OK
        )
    else:
        return Response(
            {"detail": message},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_registration_otp(request):
    """
    Step 2: Verify OTP and complete registration
    """
    identifier = request.data.get('identifier')
    otp = request.data.get('otp')
    
    if not identifier or not otp:
        return Response(
            {'error': 'Identifier and OTP are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Retrieve OTP from cache
    stored_otp = cache.get(f'otp_{identifier}')
    if stored_otp is None or str(stored_otp) != str(otp):
        return Response(
            {'error': 'Invalid or expired OTP.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Retrieve user data from cache
    registration_data = cache.get(f'registration_data_{identifier}')
    if not registration_data:
        return Response(
            {'error': 'Registration session expired. Please start again.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create the user with verified status
    serializer = CustomUserSerializer(data=registration_data)
    if serializer.is_valid():
        user = serializer.save(is_verified=True)
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        
        # Clean up cache
        cache.delete(f'otp_{identifier}')
        cache.delete(f'registration_data_{identifier}')
        
        return Response(
            {
                'refresh': str(refresh),
                'access': str(access),
                'message': 'Registration successful.',
                'is_admin': user.is_superuser,
                'role': user.role
            },
            status=status.HTTP_201_CREATED
        )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def resend_registration_otp(request):
    """
    Resend OTP for registration
    """
    identifier = request.data.get('identifier')
    
    if not identifier:
        return Response(
            {'error': 'Email or phone number is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if registration data exists in cache
    if not cache.get(f'registration_data_{identifier}'):
        return Response(
            {'error': 'No pending registration found for this identifier.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Generate and send new OTP
    success, message = generate_and_send_otp(identifier)
    
    if success:
        return Response(
            {"message": "OTP resent successfully.", "detail": message},
            status=status.HTTP_200_OK
        )
    else:
        return Response(
            {"detail": message},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    

from rest_framework_simplejwt.tokens import RefreshToken, AccessToken, TokenError
from django.core.cache import cache
from datetime import timedelta
from django.utils import timezone

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Logout a user by blacklisting both access and refresh tokens
    that are provided in the request
    Content-type: application/json
    """
    try:
        # Get both tokens from request
        refresh_token = request.data.get('refresh')
        access_token = request.data.get('access')
        
        if not refresh_token:
            return Response(
                {"error": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if not access_token:
            return Response(
                {"error": "Access token is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Blacklist refresh token
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError as e:
            return Response(
                {"error": f"Invalid refresh token: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Blacklist access token by storing it in cache
        # Use the token's expiry time (if you can extract it) or a default time
        # Default to 24 hours if you can't determine the expiry
        try:
            # Extract JTI (JWT ID) if possible
            # If that's not possible, use the whole token as key
            cache.set(
                f'blacklisted_access_{access_token}',
                'blacklisted',
                timeout=24*60*60  # 24 hours default
            )
        except Exception as e:
            # Log the error but continue with logout process
            print(f"Error blacklisting access token: {str(e)}")
        
        # You can also remove any user-specific cache data
        user_id = request.user.id
        try:
            # Not all cache backends support this
            cache.delete_pattern(f'user_session_{user_id}_*')
        except AttributeError:
            # Safe fallback for cache backends without delete_pattern
            pass
        
        return Response(
            {"message": "Logout successful. Tokens have been invalidated."},
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        return Response(
            {"error": f"Logout failed: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST
        )
# Get User Data by ID

from rest_framework.exceptions import AuthenticationFailed, PermissionDenied

import logging

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_data(request, pk):
    try:
        # Ensure the authenticated user can only access their own data
        if request.user.id != int(pk):
            return Response(
                {"detail": "You do not have permission to access this user's data."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Fetch and return the user data
        user = get_object_or_404(CustomUser, id=pk)
        serializer = CustomUserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response(
            {"detail": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

from rest_framework.parsers import MultiPartParser, FormParser

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class UserProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    @swagger_auto_schema(
        operation_summary="Get user profile",
        operation_description="Retrieves the current authenticated user's profile details",
        responses={
            200: UserProfileUpdateSerializer,
            401: "Authentication credentials were not provided."
        },
        tags=['User Profile']
    )
    def get(self, request):
        """Get current user profile details"""
        serializer = UserProfileUpdateSerializer(request.user)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_summary="Update user profile",
        operation_description="Updates the authenticated user's profile information. Supports partial updates.",
        request_body=UserProfileUpdateSerializer,
        responses={
            200: UserProfileUpdateSerializer,
            400: "Invalid input data",
            401: "Authentication credentials were not provided."
        },
        manual_parameters=[
            openapi.Parameter(
                'profile_picture',
                openapi.IN_FORM,
                description="User profile picture file",
                type=openapi.TYPE_FILE,
                required=False
            ),
        ],
        tags=['User Profile']
    )
    def patch(self, request):
        """Update user profile"""
        serializer = UserProfileUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    



# user management admin 


class ToggleUserActiveStatus(APIView):
    """
    Admin can block or unblock a user by toggling `is_active` status.
    """
    permission_classes = [IsAuthenticated,IsAdmin]

    @swagger_auto_schema(
        operation_description="Toggle the active status of a user (block/unblock).",
        responses={
            200: openapi.Response(
                description="Success message with updated user status.",
                examples={"application/json": {
                    "message": "User blocked successfully.",
                    "user_id": 12,
                    "is_active": False
                }}
            ),
            404: "User not found"
        }
    )
    def post(self, request, user_id):
        user = get_object_or_404(CustomUser, id=user_id)
        user.is_active = not user.is_active
        user.save()
        return Response({
            "message": f"User {'blocked' if not user.is_active else 'unblocked'} successfully.",
            "user_id": user.id,
            "is_active": user.is_active
        }, status=status.HTTP_200_OK)
    

class DeleteUserByAdmin(APIView):
    """
    Admin can delete any user's account using their user ID.
    """
    permission_classes = [IsAdmin]

    @swagger_auto_schema(
        operation_description="Delete a user account by ID. Only accessible to admin.",
        responses={
            204: openapi.Response(description="User deleted successfully."),
            404: "User not found"
        }
    )
    def delete(self, request, user_id):
        user = get_object_or_404(CustomUser, id=user_id)
        user.delete()
        return Response({"message": "User deleted successfully."}, status=status.HTTP_204_NO_CONTENT)



from rest_framework.permissions import IsAuthenticated

class DeleteOwnAccount(APIView):
    """
    Authenticated users can delete their own accounts.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Allows the currently logged-in user to delete their own account.",
        responses={
            204: openapi.Response(description="Account deleted successfully."),
            401: "Unauthorized"
        }
    )
    def delete(self, request):
        user = request.user
        user.delete()
        return Response({"message": "Your account has been deleted."}, status=status.HTTP_204_NO_CONTENT)
    


from rest_framework.generics import ListAPIView

class ListAllUsers(ListAPIView):
    """
    Admin can view the list of all registered users.
    """
    permission_classes = [IsAdmin]
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

    @swagger_auto_schema(
        operation_description="Retrieve a list of all users. Admin only.",
        responses={200: CustomUserSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    

@permission_classes([IsAuthenticated])
@csrf_exempt
@api_view(["GET"])
def demodata(request):
    data = {
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number":"+12345678901",
    "date_of_birth": "1990-01-01",
    "pin_code": 123456,
    "village": "Sample Village",
    "district": "Sample District",
    "state": "Sample State",
    "address": "123 Sample Street",
    "role": "user",
    "password": "securepassword"
    }

    return Response(data)


class DeliveryAddressViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing delivery addresses for authenticated users.
    """
    serializer_class = DeliveryAddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return only addresses belonging to the current user"""
        print("Get Current User...................")
        try:
            return DeliveryAddress.objects.filter(user=self.request.user)
        except Exception as e:
            return DeliveryAddress.objects.none()
            

    def perform_create(self, serializer):
        """Automatically assign the current user when creating an address"""
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def primary(self, request):
        """Get the user's primary delivery address"""
        primary_address = self.get_queryset().filter(is_primary=True).first()
        if primary_address:
            serializer = self.get_serializer(primary_address)
            return Response(serializer.data)
        return Response({"detail": "No primary address found."}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def set_primary(self, request, pk=None):
        """Set an address as the primary delivery address"""
        address = self.get_object()
        address.is_primary = True
        address.save()  # The save method will handle updating other addresses
        serializer = self.get_serializer(address)
        return Response(serializer.data)
    


  