from django.db import IntegrityError
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    UserSerializer,
)


class RegisterView(generics.CreateAPIView):
    """
    API endpoint for new user registration.
    Accessible to unauthenticated clients (AllowAny).
    Returns HTTP 201 with created user details upon success.
    """

    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = serializer.save()
        except IntegrityError:
            return Response(
                {"email": ["A user with this email address already exists."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "message": "User registered successfully.",
                "user": UserSerializer(user, context=self.get_serializer_context()).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """
    API endpoint for user login using email and password.
    Accessible to unauthenticated clients (AllowAny).
    Returns access token, refresh token, and user profile data.
    """

    permission_classes = [AllowAny]
    serializer_class = CustomTokenObtainPairSerializer


class CustomTokenRefreshView(TokenRefreshView):
    """
    API endpoint to obtain a new JWT access token using a valid refresh token.
    Accessible to unauthenticated clients (AllowAny).
    """

    permission_classes = [AllowAny]


class UserProfileView(generics.RetrieveAPIView):
    """
    Protected API endpoint to verify JWT bearer authentication and retrieve current user profile.
    Inherits global default IsAuthenticated permission.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
