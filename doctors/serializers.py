import re
from rest_framework import serializers

from .models import Doctor

# Allows optional leading '+', digits, dashes, spaces, and parentheses (between 7 and 20 chars, min 7 digits)
PHONE_REGEX = re.compile(r"^\+?[0-9\s\-()]{7,20}$")


class DoctorSerializer(serializers.ModelSerializer):
    """
    Serializer for the Doctor model.
    Validates doctor profile data and enforces read-only ownership attributes.
    """

    email = serializers.EmailField(
        required=True,
        help_text="Professional email address of the doctor.",
    )
    experience_years = serializers.IntegerField(
        required=False,
        allow_null=True,
        default=0,
        min_value=0,
        error_messages={
            "min_value": "Years of experience cannot be negative.",
        },
        help_text="Years of clinical medical practice experience.",
    )
    qualification = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Medical degrees or qualifications (e.g. MBBS, MD, MS).",
    )
    address = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Clinic or hospital practice address.",
    )

    class Meta:
        model = Doctor
        fields = (
            "id",
            "full_name",
            "email",
            "phone_number",
            "specialization",
            "experience_years",
            "qualification",
            "address",
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
        if not value or not value.strip():
            raise serializers.ValidationError("Email is required and cannot be blank.")
        return value.strip().lower()

    def validate_phone_number(self, value):
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError("Phone number is required and cannot be blank.")
        if not PHONE_REGEX.match(stripped):
            raise serializers.ValidationError(
                "Enter a valid phone number (e.g. +1234567890 or 9876543210)."
            )
        digits_only = re.sub(r"\D", "", stripped)
        if len(digits_only) < 7 or len(digits_only) > 15:
            raise serializers.ValidationError(
                "Phone number must contain between 7 and 15 digits."
            )
        return stripped

    def validate_specialization(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Specialization is required and cannot be blank.")
        return value.strip()

    def validate_experience_years(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Years of experience cannot be negative.")
        return value

    def validate_qualification(self, value):
        return value.strip() if value else ""

    def validate_address(self, value):
        return value.strip() if value else ""
