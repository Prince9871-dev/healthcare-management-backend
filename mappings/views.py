from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from patients.models import Patient
from .models import PatientDoctorMapping
from .serializers import DoctorDetailMappingSerializer, PatientDoctorMappingSerializer


class MappingListCreateView(generics.ListCreateAPIView):
    """
    API view to list and create patient-doctor mappings.
    - GET: Lists all mappings accessible to the authenticated user.
    - POST: Assigns a doctor to a patient with ownership verification.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = PatientDoctorMappingSerializer

    def get_queryset(self):
        """
        Enforce user-level data isolation.
        Users can only view mappings for patients they personally created.
        """
        return (
            PatientDoctorMapping.objects.filter(patient__created_by=self.request.user)
            .select_related("patient", "doctor")
            .order_by("-assigned_at")
        )

    def perform_create(self, serializer):
        """
        Save the mapping with IntegrityError safety catch.
        """
        try:
            serializer.save()
        except IntegrityError:
            raise ValidationError(
                "This doctor is already assigned to this patient."
            )


class MappingDetailView(APIView):
    """
    API view handling patient-specific mappings retrieval and mapping deletion.
    - GET: Returns the doctors assigned to the specified patient (or single mapping if mapping ID provided).
    - DELETE: Deletes the specified mapping by mapping ID.

    Protected against IDOR: Unowned records return HTTP 404.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        """
        Return the doctors assigned to the specified patient.
        Includes relevant doctor details in the response.
        Verifies patient access before returning results.
        """
        # First check if 'id' matches a patient owned by the authenticated user
        patient = Patient.objects.filter(id=id, created_by=request.user).first()
        if patient is not None:
            mappings = (
                PatientDoctorMapping.objects.filter(patient=patient)
                .select_related("doctor")
                .order_by("-assigned_at")
            )
            serializer = DoctorDetailMappingSerializer(mappings, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Fallback check if 'id' matches a specific mapping owned by the authenticated user
        mapping = (
            PatientDoctorMapping.objects.filter(id=id, patient__created_by=request.user)
            .select_related("doctor")
            .first()
        )
        if mapping is not None:
            serializer = DoctorDetailMappingSerializer(mapping)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # If neither matches within user's permitted scope, return 404 to conceal record existence
        return Response(
            {"detail": "No Patient or Mapping matches the given query."},
            status=status.HTTP_404_NOT_FOUND,
        )

    def delete(self, request, id):
        """
        Delete the specified mapping by mapping ID.
        Verifies user authorization before deletion.
        """
        mapping = get_object_or_404(
            PatientDoctorMapping.objects.filter(patient__created_by=request.user),
            id=id,
        )
        mapping.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
