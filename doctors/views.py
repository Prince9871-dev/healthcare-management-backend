from rest_framework import generics, permissions
from rest_framework.permissions import IsAuthenticated

from .models import Doctor
from .serializers import DoctorSerializer


class IsDoctorOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission allowing any authenticated user to view doctor details (SAFE_METHODS),
    while strictly restricting update and delete actions to the user who registered the doctor.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        # Read-only permissions are allowed to any authenticated request
        if request.method in permissions.SAFE_METHODS:
            return True
        # Write permissions (PUT, PATCH, DELETE) are strictly restricted to the creator
        return obj.created_by == request.user


class DoctorListCreateView(generics.ListCreateAPIView):
    """
    API view to list and create doctors.
    - GET: Returns the full doctor directory accessible to any authenticated user.
    - POST: Creates a new doctor, automatically setting created_by=request.user.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DoctorSerializer

    def get_queryset(self):
        """
        Return the complete doctor directory to authenticated users.
        """
        return Doctor.objects.all().order_by("-created_at")

    def perform_create(self, serializer):
        """
        Securely assign the authenticated user as the creator.
        Ignores any client-supplied created_by field.
        """
        serializer.save(created_by=self.request.user)


class DoctorDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API view to retrieve, update, or delete an existing doctor.
    - GET: Retrieves doctor details (open to all authenticated users).
    - PUT: Fully updates the doctor record (creator only).
    - PATCH: Partially updates the doctor record (creator only).
    - DELETE: Deletes the doctor record (creator only).
    """

    permission_classes = [IsAuthenticated, IsDoctorOwnerOrReadOnly]
    serializer_class = DoctorSerializer
    lookup_field = "id"
    lookup_url_kwarg = "id"
    queryset = Doctor.objects.all()

    def perform_update(self, serializer):
        """
        Ensure ownership cannot be reassigned during updates.
        """
        serializer.save(created_by=self.request.user)
