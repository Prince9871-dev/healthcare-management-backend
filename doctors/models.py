import uuid
from django.conf import settings
from django.db import models


class Doctor(models.Model):
    """
    Doctor model representing healthcare providers and specialists.
    Scoped to the user account that created the record.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique UUID identifier for this doctor.",
    )
    full_name = models.CharField(
        max_length=255,
        help_text="Full legal name of the doctor.",
    )
    email = models.EmailField(
        max_length=255,
        help_text="Professional email address of the doctor.",
    )
    phone_number = models.CharField(
        max_length=20,
        help_text="Contact telephone number.",
    )
    specialization = models.CharField(
        max_length=255,
        help_text="Medical specialization (e.g. Cardiology, Neurology, Pediatrics).",
    )
    experience_years = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=0,
        help_text="Years of clinical medical practice experience.",
    )
    qualification = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Medical degrees or qualifications (e.g. MBBS, MD, MS).",
    )
    address = models.TextField(
        blank=True,
        default="",
        help_text="Clinic or hospital practice address.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctors",
        help_text="Healthcare user/account who created and owns this doctor record.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the doctor record was created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the doctor record was last updated.",
    )

    class Meta:
        verbose_name = "Doctor"
        verbose_name_plural = "Doctors"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Dr. {self.full_name} ({self.specialization}) [{self.id}]"
