from django.contrib import admin
from .models import Doctor


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Doctor model.
    """

    list_display = (
        "full_name",
        "specialization",
        "email",
        "phone_number",
        "experience_years",
        "qualification",
        "created_by",
        "created_at",
    )
    search_fields = (
        "full_name",
        "email",
        "phone_number",
        "specialization",
        "qualification",
        "id",
    )
    list_filter = (
        "specialization",
        "created_at",
        "created_by",
    )
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )
