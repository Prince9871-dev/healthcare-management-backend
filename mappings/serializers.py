from rest_framework import serializers

from doctors.models import Doctor
from doctors.serializers import DoctorSerializer
from patients.models import Patient
from .models import PatientDoctorMapping


class PatientDoctorMappingSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and listing patient-doctor mappings.
    Validates ownership of both patient and doctor records, and prevents duplicates.
    """

    patient = serializers.PrimaryKeyRelatedField(
        queryset=Patient.objects.all(),
        help_text="UUID of the patient.",
    )
    doctor = serializers.PrimaryKeyRelatedField(
        queryset=Doctor.objects.all(),
        help_text="UUID of the doctor.",
    )

    # Descriptive read-only fields for convenient client consumption
    patient_id = serializers.UUIDField(source="patient.id", read_only=True)
    doctor_id = serializers.UUIDField(source="doctor.id", read_only=True)
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)
    doctor_name = serializers.CharField(source="doctor.full_name", read_only=True)
    specialization = serializers.CharField(source="doctor.specialization", read_only=True)

    class Meta:
        model = PatientDoctorMapping
        fields = (
            "id",
            "patient",
            "doctor",
            "patient_id",
            "doctor_id",
            "patient_name",
            "doctor_name",
            "specialization",
            "assigned_at",
        )
        read_only_fields = (
            "id",
            "patient_id",
            "doctor_id",
            "patient_name",
            "doctor_name",
            "specialization",
            "assigned_at",
        )
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=PatientDoctorMapping.objects.all(),
                fields=("patient", "doctor"),
                message="This doctor is already assigned to this patient.",
            )
        ]

    def to_internal_value(self, data):
        """
        Support both 'patient'/'doctor' and 'patient_id'/'doctor_id' in incoming payloads.
        """
        payload = data.copy() if hasattr(data, "copy") else dict(data)
        if "patient_id" in payload and "patient" not in payload:
            payload["patient"] = payload["patient_id"]
        if "doctor_id" in payload and "doctor" not in payload:
            payload["doctor"] = payload["doctor_id"]
        return super().to_internal_value(payload)

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        patient = attrs.get("patient")
        doctor = attrs.get("doctor")

        # Authorization checks: authenticated user must own both records
        if user and user.is_authenticated:
            if patient.created_by != user:
                raise serializers.ValidationError({
                    "patient": "Patient does not exist or you do not have permission to access this record."
                })
            if doctor.created_by != user:
                raise serializers.ValidationError({
                    "doctor": "Doctor does not exist or you do not have permission to access this record."
                })

        # Duplicate check at serializer level
        if PatientDoctorMapping.objects.filter(patient=patient, doctor=doctor).exists():
            raise serializers.ValidationError(
                "This doctor is already assigned to this patient."
            )

        return attrs


class DoctorDetailMappingSerializer(serializers.ModelSerializer):
    """
    Serializer used when returning doctors assigned to a patient.
    Includes full doctor details and mapping metadata.
    """

    mapping_id = serializers.UUIDField(source="id", read_only=True)
    doctor_id = serializers.UUIDField(source="doctor.id", read_only=True)
    doctor_name = serializers.CharField(source="doctor.full_name", read_only=True)
    full_name = serializers.CharField(source="doctor.full_name", read_only=True)
    email = serializers.EmailField(source="doctor.email", read_only=True)
    phone_number = serializers.CharField(source="doctor.phone_number", read_only=True)
    specialization = serializers.CharField(source="doctor.specialization", read_only=True)
    experience_years = serializers.IntegerField(source="doctor.experience_years", read_only=True)
    qualification = serializers.CharField(source="doctor.qualification", read_only=True)
    address = serializers.CharField(source="doctor.address", read_only=True)
    doctor = DoctorSerializer(read_only=True)

    class Meta:
        model = PatientDoctorMapping
        fields = (
            "id",
            "mapping_id",
            "assigned_at",
            "doctor_id",
            "doctor_name",
            "full_name",
            "email",
            "phone_number",
            "specialization",
            "experience_years",
            "qualification",
            "address",
            "doctor",
        )
        read_only_fields = fields
