import datetime
import uuid
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from doctors.models import Doctor
from patients.models import Patient
from .models import PatientDoctorMapping

User = get_user_model()


class MappingAPITests(APITestCase):
    """
    Comprehensive test suite for Patient-Doctor Mapping APIs and IDOR protection.
    Enforces PostgreSQL-first execution and verifies database-level constraints.
    """

    def setUp(self):
        # Create User A
        self.user_a = User.objects.create_user(
            email="admin.alice@example.com",
            name="Alice Smith",
            password="StrongPassword123!",
        )

        # Create User B
        self.user_b = User.objects.create_user(
            email="admin.bob@example.com",
            name="Bob Jones",
            password="StrongPassword123!",
        )

        # Patients owned by User A
        self.patient_a1 = Patient.objects.create(
            full_name="John Doe",
            email="john@example.com",
            phone_number="+1-555-0101",
            date_of_birth=datetime.date(1990, 1, 1),
            gender="Male",
            address="100 First St",
            created_by=self.user_a,
        )
        self.patient_a2 = Patient.objects.create(
            full_name="Jane Doe",
            email="jane@example.com",
            phone_number="+1-555-0102",
            date_of_birth=datetime.date(1992, 2, 2),
            gender="Female",
            address="102 First St",
            created_by=self.user_a,
        )

        # Doctors owned by User A
        self.doctor_a1 = Doctor.objects.create(
            full_name="Gregory House",
            email="house@diagnostics.org",
            phone_number="+1-555-0201",
            specialization="Diagnostic Medicine",
            experience_years=20,
            qualification="MD",
            address="Diagnostics Wing",
            created_by=self.user_a,
        )
        self.doctor_a2 = Doctor.objects.create(
            full_name="James Wilson",
            email="wilson@oncology.org",
            phone_number="+1-555-0202",
            specialization="Oncology",
            experience_years=18,
            qualification="MD",
            address="Oncology Wing",
            created_by=self.user_a,
        )

        # Patient & Doctor owned by User B
        self.patient_b = Patient.objects.create(
            full_name="Bob Patient",
            email="bobpatient@example.com",
            phone_number="+1-555-0301",
            date_of_birth=datetime.date(1980, 5, 5),
            gender="Male",
            address="200 Second St",
            created_by=self.user_b,
        )
        self.doctor_b = Doctor.objects.create(
            full_name="Lisa Cuddy",
            email="cuddy@admin.org",
            phone_number="+1-555-0401",
            specialization="Endocrinology & Administration",
            experience_years=22,
            qualification="MD",
            address="Admin Suite",
            created_by=self.user_b,
        )

        # Existing mapping owned by User A
        self.mapping_a = PatientDoctorMapping.objects.create(
            patient=self.patient_a1,
            doctor=self.doctor_a1,
        )

        # Existing mapping owned by User B
        self.mapping_b = PatientDoctorMapping.objects.create(
            patient=self.patient_b,
            doctor=self.doctor_b,
        )

        self.list_create_url = reverse("mappings:mapping-list-create")
        self.patient_a1_detail_url = reverse(
            "mappings:mapping-detail", kwargs={"id": self.patient_a1.id}
        )
        self.patient_b_detail_url = reverse(
            "mappings:mapping-detail", kwargs={"id": self.patient_b.id}
        )
        self.mapping_a_delete_url = reverse(
            "mappings:mapping-detail", kwargs={"id": self.mapping_a.id}
        )
        self.mapping_b_delete_url = reverse(
            "mappings:mapping-detail", kwargs={"id": self.mapping_b.id}
        )

    # -------------------------------------------------------------------------
    # 1. Successful Patient-Doctor Assignment
    # -------------------------------------------------------------------------
    def test_successful_mapping_creation(self):
        self.client.force_authenticate(user=self.user_a)
        payload = {
            "patient": str(self.patient_a2.id),
            "doctor": str(self.doctor_a2.id),
        }
        response = self.client.post(self.list_create_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["patient"], self.patient_a2.id)
        self.assertEqual(response.data["doctor"], self.doctor_a2.id)
        self.assertEqual(response.data["patient_name"], "Jane Doe")
        self.assertEqual(response.data["doctor_name"], "James Wilson")
        self.assertEqual(response.data["specialization"], "Oncology")
        self.assertIn("id", response.data)
        self.assertIn("assigned_at", response.data)

        # Also verify alternative payload format (patient_id, doctor_id)
        payload_alt = {
            "patient_id": str(self.patient_a1.id),
            "doctor_id": str(self.doctor_a2.id),
        }
        res_alt = self.client.post(self.list_create_url, payload_alt, format="json")
        self.assertEqual(res_alt.status_code, status.HTTP_201_CREATED)

    # -------------------------------------------------------------------------
    # 2. Unauthenticated Requests Rejected
    # -------------------------------------------------------------------------
    def test_unauthenticated_requests_rejected(self):
        # List
        res_list = self.client.get(self.list_create_url)
        self.assertEqual(res_list.status_code, status.HTTP_401_UNAUTHORIZED)

        # Create
        res_create = self.client.post(
            self.list_create_url,
            {"patient": str(self.patient_a1.id), "doctor": str(self.doctor_a2.id)},
            format="json",
        )
        self.assertEqual(res_create.status_code, status.HTTP_401_UNAUTHORIZED)

        # Get by patient
        res_detail = self.client.get(self.patient_a1_detail_url)
        self.assertEqual(res_detail.status_code, status.HTTP_401_UNAUTHORIZED)

        # Delete
        res_del = self.client.delete(self.mapping_a_delete_url)
        self.assertEqual(res_del.status_code, status.HTTP_401_UNAUTHORIZED)

    # -------------------------------------------------------------------------
    # 3. Invalid Patient ID Rejected
    # -------------------------------------------------------------------------
    def test_invalid_patient_id(self):
        self.client.force_authenticate(user=self.user_a)
        payload = {
            "patient": str(uuid.uuid4()),  # Non-existent patient
            "doctor": str(self.doctor_a1.id),
        }
        response = self.client.post(self.list_create_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("patient", response.data)

    # -------------------------------------------------------------------------
    # 4. Invalid Doctor ID Rejected
    # -------------------------------------------------------------------------
    def test_invalid_doctor_id(self):
        self.client.force_authenticate(user=self.user_a)
        payload = {
            "patient": str(self.patient_a1.id),
            "doctor": str(uuid.uuid4()),  # Non-existent doctor
        }
        response = self.client.post(self.list_create_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("doctor", response.data)

    # -------------------------------------------------------------------------
    # 5. Duplicate Mapping Rejected
    # -------------------------------------------------------------------------
    def test_duplicate_mapping_rejected(self):
        self.client.force_authenticate(user=self.user_a)
        # Attempt to map patient_a1 to doctor_a1 again (already mapped in setUp)
        payload = {
            "patient": str(self.patient_a1.id),
            "doctor": str(self.doctor_a1.id),
        }
        response = self.client.post(self.list_create_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already assigned", str(response.data).lower())

    # -------------------------------------------------------------------------
    # 6. User Cannot Map Another User's Patient
    # -------------------------------------------------------------------------
    def test_user_cannot_map_another_users_patient(self):
        self.client.force_authenticate(user=self.user_a)
        # User A attempts to map User B's patient with User A's doctor
        payload = {
            "patient": str(self.patient_b.id),
            "doctor": str(self.doctor_a1.id),
        }
        response = self.client.post(self.list_create_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("patient", response.data)

    # -------------------------------------------------------------------------
    # 7. User Cannot Map Another User's Doctor
    # -------------------------------------------------------------------------
    def test_user_cannot_map_another_users_doctor(self):
        self.client.force_authenticate(user=self.user_a)
        # User A attempts to map User A's patient with User B's doctor
        payload = {
            "patient": str(self.patient_a1.id),
            "doctor": str(self.doctor_b.id),
        }
        response = self.client.post(self.list_create_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("doctor", response.data)

    # -------------------------------------------------------------------------
    # 8. User Cannot List Unauthorized Mappings (List Isolation)
    # -------------------------------------------------------------------------
    def test_users_only_see_their_own_mappings(self):
        # User A should only see mapping A
        self.client.force_authenticate(user=self.user_a)
        response_a = self.client.get(self.list_create_url)
        self.assertEqual(response_a.status_code, status.HTTP_200_OK)
        returned_ids_a = [m["id"] for m in response_a.data]
        self.assertIn(str(self.mapping_a.id), returned_ids_a)
        self.assertNotIn(str(self.mapping_b.id), returned_ids_a)

        # User B should only see mapping B
        self.client.force_authenticate(user=self.user_b)
        response_b = self.client.get(self.list_create_url)
        self.assertEqual(response_b.status_code, status.HTTP_200_OK)
        returned_ids_b = [m["id"] for m in response_b.data]
        self.assertIn(str(self.mapping_b.id), returned_ids_b)
        self.assertNotIn(str(self.mapping_a.id), returned_ids_b)

    # -------------------------------------------------------------------------
    # 9. User Cannot Retrieve Mappings for Another User's Patient (IDOR Defense)
    # -------------------------------------------------------------------------
    def test_user_cannot_retrieve_another_users_patient_mappings(self):
        # User A attempts to retrieve doctors assigned to User B's patient
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(self.patient_b_detail_url)

        # Must return 404 (Not Found) to conceal patient existence
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # -------------------------------------------------------------------------
    # 10. User Cannot Delete Another User's Mapping
    # -------------------------------------------------------------------------
    def test_user_cannot_delete_another_users_mapping(self):
        # User A attempts to delete User B's mapping
        self.client.force_authenticate(user=self.user_a)
        response = self.client.delete(self.mapping_b_delete_url)

        # Must return 404 (Not Found)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Verify mapping still exists in DB
        self.assertTrue(PatientDoctorMapping.objects.filter(id=self.mapping_b.id).exists())

    # -------------------------------------------------------------------------
    # 11. Successful Mapping Deletion
    # -------------------------------------------------------------------------
    def test_successful_mapping_deletion(self):
        self.client.force_authenticate(user=self.user_a)
        response = self.client.delete(self.mapping_a_delete_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(PatientDoctorMapping.objects.filter(id=self.mapping_a.id).exists())

    # -------------------------------------------------------------------------
    # 12. Retrieve Doctors Assigned to Patient (GET /api/mappings/<patient_id>/)
    # -------------------------------------------------------------------------
    def test_get_doctors_assigned_to_patient(self):
        self.client.force_authenticate(user=self.user_a)
        # Assign a second doctor to patient_a1
        PatientDoctorMapping.objects.create(
            patient=self.patient_a1,
            doctor=self.doctor_a2,
        )

        response = self.client.get(self.patient_a1_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        # Verify doctor details are included, not just raw mapping IDs
        first_doc = response.data[0]
        self.assertIn("doctor_id", first_doc)
        self.assertIn("doctor_name", first_doc)
        self.assertIn("specialization", first_doc)
        self.assertIn("email", first_doc)
        self.assertIn("doctor", first_doc)
        self.assertIn("qualification", first_doc)

    # -------------------------------------------------------------------------
    # 13. UUID Validation
    # -------------------------------------------------------------------------
    def test_invalid_uuid_handling(self):
        self.client.force_authenticate(user=self.user_a)

        # Non-existent UUID
        random_uuid = uuid.uuid4()
        non_existent_url = reverse("mappings:mapping-detail", kwargs={"id": random_uuid})
        res_non_existent = self.client.get(non_existent_url)
        self.assertEqual(res_non_existent.status_code, status.HTTP_404_NOT_FOUND)

        # Malformed UUID string in URL
        res_invalid = self.client.get("/api/mappings/not-a-valid-uuid/")
        self.assertEqual(res_invalid.status_code, status.HTTP_404_NOT_FOUND)

    # -------------------------------------------------------------------------
    # 14. Database-Level Unique Constraint
    # -------------------------------------------------------------------------
    def test_database_level_duplicate_constraint(self):
        # Direct DB attempt to duplicate mapping
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PatientDoctorMapping.objects.create(
                    patient=self.patient_a1,
                    doctor=self.doctor_a1,
                )

    # -------------------------------------------------------------------------
    # 15. Model String Representation
    # -------------------------------------------------------------------------
    def test_model_str_representation(self):
        self.assertEqual(
            str(self.mapping_a),
            f"Mapping: John Doe -> Dr. Gregory House [{self.mapping_a.id}]",
        )
