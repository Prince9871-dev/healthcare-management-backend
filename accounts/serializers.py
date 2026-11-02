from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for viewing User profile data safely without password exposure.
    """

    class Meta:
        model = User
        fields = ("id", "name", "email", "date_joined")
        read_only_fields = ("id", "date_joined")


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration. Validates required fields, email uniqueness,
    and password strength via Django's password validators.
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        help_text="Password must meet standard security complexity criteria.",
    )

    class Meta:
        model = User
        fields = ("id", "name", "email", "password", "date_joined")
        read_only_fields = ("id", "date_joined")

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Name field cannot be blank.")
        return value.strip()

    def validate_email(self, value):
        normalized_email = value.strip().lower()
        if User.objects.filter(email__iexact=normalized_email).exists():
            raise serializers.ValidationError("A user with this email address already exists.")
        return normalized_email

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        try:
            return User.objects.create_user(
                email=validated_data["email"],
                name=validated_data["name"],
                password=validated_data["password"],
            )
        except IntegrityError:
            raise serializers.ValidationError(
                {"email": ["A user with this email address already exists."]}
            )


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom SimpleJWT serializer that authenticates via email and password,
    returning JWT tokens along with essential user profile data.
    """

    def validate(self, attrs):
        username_field = self.username_field
        if username_field in attrs and isinstance(attrs[username_field], str):
            attrs[username_field] = attrs[username_field].strip().lower()

        data = super().validate(attrs)
        data["user"] = {
            "id": str(self.user.id),
            "name": self.user.name,
            "email": self.user.email,
        }
        return data
