import uuid
from django.conf import settings
from django.db import models


class Patient(models.Model):
    """
    Patient model representing individuals receiving medical care.
    Scoped to the user account that created the record.
    """

    class Gender(models.TextChoices):
        MALE = "Male", "Male"
        FEMALE = "Female", "Female"
        OTHER = "Other", "Other"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique UUID identifier for this patient.",
    )
    full_name = models.CharField(
        max_length=255,
        help_text="Full legal name of the patient.",
    )
    email = models.EmailField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Optional contact email address for the patient.",
    )
    phone_number = models.CharField(
        max_length=20,
        help_text="Contact telephone number.",
    )
    date_of_birth = models.DateField(
        help_text="Patient date of birth (cannot be in the future).",
    )
    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        help_text="Patient gender identity.",
    )
    address = models.TextField(
        help_text="Physical or postal residential address.",
    )
    medical_history = models.TextField(
        blank=True,
        default="",
        help_text="Optional medical history, past diagnoses, or allergies.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patients",
        help_text="Healthcare user/provider who created and owns this patient record.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the patient record was created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the patient record was last updated.",
    )

    class Meta:
        verbose_name = "Patient"
        verbose_name_plural = "Patients"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} ({self.id})"
