import re
from django.utils import timezone
from rest_framework import serializers

from .models import Patient

# Allows optional leading '+', digits, dashes, spaces, and parentheses (between 7 and 20 chars, min 7 digits)
PHONE_REGEX = re.compile(r"^\+?[0-9\s\-()]{7,20}$")


class PatientSerializer(serializers.ModelSerializer):
    """
    Serializer for the Patient model.
    Validates patient data and ensures created_by ownership is read-only.
    """

    email = serializers.EmailField(
        required=False,
        allow_blank=True,
        allow_null=True,
        default="",
        help_text="Optional contact email address.",
    )

    class Meta:
        model = Patient
        fields = (
            "id",
            "full_name",
            "email",
            "phone_number",
            "date_of_birth",
            "gender",
            "address",
            "medical_history",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_by",
            "created_at",
            "updated_at",
        )

    def validate_full_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Full name is required and cannot be blank.")
        return value.strip()

    def validate_email(self, value):
        if value:
            return value.strip().lower()
        return None

    def validate_phone_number(self, value):
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError("Phone number is required and cannot be blank.")
        if not PHONE_REGEX.match(stripped):
            raise serializers.ValidationError(
                "Enter a valid phone number (e.g. +1234567890 or 9876543210)."
            )
        # Ensure at least 7 digits are present
        digits_only = re.sub(r"\D", "", stripped)
        if len(digits_only) < 7 or len(digits_only) > 15:
            raise serializers.ValidationError(
                "Phone number must contain between 7 and 15 digits."
            )
        return stripped

    def validate_date_of_birth(self, value):
        today = timezone.now().date()
        if value > today:
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        return value

    def validate_address(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Address is required and cannot be blank.")
        return value.strip()
