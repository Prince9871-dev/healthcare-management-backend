import uuid
from django.db import models


class PatientDoctorMapping(models.Model):
    """
    Model representing the assignment of a Doctor to a Patient.
    Establishes a many-to-many relationship with an explicit intermediary table.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique UUID identifier for this mapping record.",
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="doctor_mappings",
        help_text="The patient associated with this mapping.",
    )
    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.CASCADE,
        related_name="patient_mappings",
        help_text="The doctor assigned to the patient.",
    )
    assigned_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the doctor was assigned to the patient.",
    )

    class Meta:
        verbose_name = "Patient Doctor Mapping"
        verbose_name_plural = "Patient Doctor Mappings"
        ordering = ["-assigned_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["patient", "doctor"],
                name="unique_patient_doctor_mapping",
            ),
        ]

    def __str__(self):
        return f"Mapping: {self.patient.full_name} -> Dr. {self.doctor.full_name} [{self.id}]"
