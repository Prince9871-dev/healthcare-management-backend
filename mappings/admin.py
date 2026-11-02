from django.contrib import admin
from .models import PatientDoctorMapping


@admin.register(PatientDoctorMapping)
class PatientDoctorMappingAdmin(admin.ModelAdmin):
    """
    Admin configuration for the PatientDoctorMapping model.
    """

    list_display = (
        "patient",
        "doctor",
        "assigned_at",
    )
    search_fields = (
        "patient__full_name",
        "patient__email",
        "doctor__full_name",
        "doctor__specialization",
        "id",
    )
    list_filter = (
        "assigned_at",
        "doctor__specialization",
    )
    ordering = ("-assigned_at",)
    readonly_fields = (
        "id",
        "assigned_at",
    )
