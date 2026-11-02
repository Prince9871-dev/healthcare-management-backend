from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Patient
from .serializers import PatientSerializer


class PatientListCreateView(generics.ListCreateAPIView):
    """
    API view to list and create patients.
    - GET: Returns patients created by the authenticated user.
    - POST: Creates a new patient, automatically associating created_by=request.user.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = PatientSerializer

    def get_queryset(self):
        """
        Enforce user-level data isolation at the database query level.
        Users can only list patients they personally created.
        """
        return Patient.objects.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        """
        Securely assign the authenticated user as the creator.
        Ignores any client-supplied created_by field.
        """
        serializer.save(created_by=self.request.user)


class PatientDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API view to retrieve, update, or delete an existing patient.
    - GET: Retrieves patient details.
    - PUT: Fully updates the patient record.
    - PATCH: Partially updates the patient record.
    - DELETE: Deletes the patient record.

    Protected against IDOR: Accessing a patient owned by another user returns HTTP 404.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = PatientSerializer
    lookup_field = "id"
    lookup_url_kwarg = "id"

    def get_queryset(self):
        """
        Enforce ownership isolation at the query level.
        Querying another user's patient returns 404 instead of exposing record existence.
        """
        return Patient.objects.filter(created_by=self.request.user)

    def perform_update(self, serializer):
        """
        Ensure ownership cannot be reassigned during updates.
        """
        serializer.save(created_by=self.request.user)
