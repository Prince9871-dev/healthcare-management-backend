from django.contrib import admin
from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Patient model.
    """

    list_display = (
        "full_name",
        "email",
        "phone_number",
        "gender",
        "date_of_birth",
        "created_by",
        "created_at",
    )
    search_fields = (
        "full_name",
        "email",
        "phone_number",
        "id",
    )
    list_filter = (
        "gender",
        "created_at",
        "created_by",
    )
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )
