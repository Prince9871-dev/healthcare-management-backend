import datetime
import uuid
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Patient

User = get_user_model()


class PatientAPITests(APITestCase):
    """
    Comprehensive test suite for Patient Management APIs and ownership isolation.
    Enforces PostgreSQL-first execution.
    """

    def setUp(self):
        # Create User A
        self.user_a = User.objects.create_user(
            email="doctor.alice@example.com",
            name="Dr. Alice",
            password="StrongPassword123!",
        )

        # Create User B
        self.user_b = User.objects.create_user(
            email="doctor.bob@example.com",
            name="Dr. Bob",
            password="StrongPassword123!",
        )

        # Create an existing patient owned by User A
        self.patient_a = Patient.objects.create(
            full_name="John Doe",
            email="john.doe@example.com",
            phone_number="+1-555-0199",
            date_of_birth=datetime.date(1990, 5, 15),
            gender="Male",
            address="123 Health Ave, Metropolis",
            medical_history="Hypertension",
            created_by=self.user_a,
        )

        # Create an existing patient owned by User B
        self.patient_b = Patient.objects.create(
            full_name="Jane Smith",
            email="jane.smith@example.com",
            phone_number="+1-555-0288",
            date_of_birth=datetime.date(1985, 8, 20),
            gender="Female",
            address="456 Care Blvd, Gotham",
            medical_history="Asthma",
            created_by=self.user_b,
        )

        self.list_create_url = reverse("patients:patient-list-create")
        self.detail_url_a = reverse(
            "patients:patient-detail", kwargs={"id": self.patient_a.id}
        )
        self.detail_url_b = reverse(
            "patients:patient-detail", kwargs={"id": self.patient_b.id}
        )

        self.valid_payload = {
            "full_name": "Charlie Brown",
            "email": "charlie@example.com",
            "phone_number": "+1-555-0377",
            "date_of_birth": "1995-10-10",
            "gender": "Other",
            "address": "789 Pine Rd, Smallville",
            "medical_history": "No known drug allergies.",
        }

    # -------------------------------------------------------------------------
    # 1. Successful Patient Creation
    # -------------------------------------------------------------------------
    def test_successful_patient_creation(self):
        self.client.force_authenticate(user=self.user_a)
        response = self.client.post(self.list_create_url, self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["full_name"], "Charlie Brown")
        self.assertEqual(response.data["email"], "charlie@example.com")
        self.assertEqual(response.data["gender"], "Other")
        self.assertIn("id", response.data)
        self.assertEqual(response.data["created_by"], self.user_a.id)

        # Verify DB record
        created_patient = Patient.objects.get(id=response.data["id"])
        self.assertEqual(created_patient.created_by, self.user_a)

    # -------------------------------------------------------------------------
    # 2. Unauthenticated Requests Rejected
    # -------------------------------------------------------------------------
    def test_unauthenticated_requests_rejected(self):
        # List endpoint
        res_list = self.client.get(self.list_create_url)
        self.assertEqual(res_list.status_code, status.HTTP_401_UNAUTHORIZED)

        # Create endpoint
        res_create = self.client.post(self.list_create_url, self.valid_payload, format="json")
        self.assertEqual(res_create.status_code, status.HTTP_401_UNAUTHORIZED)

        # Detail endpoint
        res_detail = self.client.get(self.detail_url_a)
        self.assertEqual(res_detail.status_code, status.HTTP_401_UNAUTHORIZED)

    # -------------------------------------------------------------------------
    # 3. Invalid Email Format Rejected
    # -------------------------------------------------------------------------
    def test_invalid_email_format(self):
        self.client.force_authenticate(user=self.user_a)
        payload = self.valid_payload.copy()
        payload["email"] = "not-a-valid-email-string"

        response = self.client.post(self.list_create_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    # -------------------------------------------------------------------------
    # 4. Invalid Phone Number Format Rejected
    # -------------------------------------------------------------------------
    def test_invalid_phone_number_format(self):
        self.client.force_authenticate(user=self.user_a)

        # Alphabetic string
        payload1 = self.valid_payload.copy()
        payload1["phone_number"] = "invalid-phone"
        res1 = self.client.post(self.list_create_url, payload1, format="json")
        self.assertEqual(res1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", res1.data)

        # Too short (fewer than 7 digits)
        payload2 = self.valid_payload.copy()
        payload2["phone_number"] = "12345"
        res2 = self.client.post(self.list_create_url, payload2, format="json")
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", res2.data)

    # -------------------------------------------------------------------------
    # 5. Future Date of Birth Rejected
    # -------------------------------------------------------------------------
    def test_future_date_of_birth_rejected(self):
        self.client.force_authenticate(user=self.user_a)
        tomorrow = (timezone.now().date() + datetime.timedelta(days=1)).isoformat()
        payload = self.valid_payload.copy()
        payload["date_of_birth"] = tomorrow

        response = self.client.post(self.list_create_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date_of_birth", response.data)
        self.assertIn("future", str(response.data["date_of_birth"]).lower())

    # -------------------------------------------------------------------------
    # 6. Missing Required Fields Rejected
    # -------------------------------------------------------------------------
    def test_missing_required_fields(self):
        self.client.force_authenticate(user=self.user_a)

        # Missing full_name
        p = self.valid_payload.copy()
        del p["full_name"]
        res = self.client.post(self.list_create_url, p, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("full_name", res.data)

        # Missing phone_number
        p = self.valid_payload.copy()
        del p["phone_number"]
        res = self.client.post(self.list_create_url, p, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", res.data)

        # Missing address
        p = self.valid_payload.copy()
        del p["address"]
        res = self.client.post(self.list_create_url, p, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("address", res.data)

        # Blank full_name
        p = self.valid_payload.copy()
        p["full_name"] = "   "
        res = self.client.post(self.list_create_url, p, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # -------------------------------------------------------------------------
    # 7. Client Cannot Assign Another User as created_by
    # -------------------------------------------------------------------------
    def test_client_cannot_assign_another_user_as_created_by(self):
        self.client.force_authenticate(user=self.user_a)
        payload = self.valid_payload.copy()
        # Attempt to spoof ownership to User B
        payload["created_by"] = str(self.user_b.id)

        response = self.client.post(self.list_create_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify ownership remains User A
        created_patient = Patient.objects.get(id=response.data["id"])
        self.assertEqual(created_patient.created_by, self.user_a)
        self.assertNotEqual(created_patient.created_by, self.user_b)

    # -------------------------------------------------------------------------
    # 8. Users Only See Their Own Patients (List Isolation)
    # -------------------------------------------------------------------------
    def test_users_only_see_their_own_patients(self):
        # User A should only see patient A
        self.client.force_authenticate(user=self.user_a)
        response_a = self.client.get(self.list_create_url)
        self.assertEqual(response_a.status_code, status.HTTP_200_OK)
        returned_ids_a = [p["id"] for p in response_a.data]
        self.assertIn(str(self.patient_a.id), returned_ids_a)
        self.assertNotIn(str(self.patient_b.id), returned_ids_a)

        # User B should only see patient B
        self.client.force_authenticate(user=self.user_b)
        response_b = self.client.get(self.list_create_url)
        self.assertEqual(response_b.status_code, status.HTTP_200_OK)
        returned_ids_b = [p["id"] for p in response_b.data]
        self.assertIn(str(self.patient_b.id), returned_ids_b)
        self.assertNotIn(str(self.patient_a.id), returned_ids_b)

    # -------------------------------------------------------------------------
    # 9. User Cannot Retrieve Another User's Patient (IDOR Protection)
    # -------------------------------------------------------------------------
    def test_user_cannot_retrieve_another_users_patient(self):
        # User A tries to retrieve User B's patient
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(self.detail_url_b)

        # Must return 404 (Not Found), not 403 (Forbidden), to conceal record existence
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # -------------------------------------------------------------------------
    # 10. User Cannot Update Another User's Patient
    # -------------------------------------------------------------------------
    def test_user_cannot_update_another_users_patient(self):
        self.client.force_authenticate(user=self.user_a)
        update_payload = self.valid_payload.copy()
        update_payload["full_name"] = "Hacked Name"

        # User A tries to PUT update User B's patient
        response = self.client.put(self.detail_url_b, update_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Confirm User B's patient remains unchanged in DB
        self.patient_b.refresh_from_db()
        self.assertEqual(self.patient_b.full_name, "Jane Smith")

    # -------------------------------------------------------------------------
    # 11. User Cannot Delete Another User's Patient
    # -------------------------------------------------------------------------
    def test_user_cannot_delete_another_users_patient(self):
        self.client.force_authenticate(user=self.user_a)

        # User A tries to DELETE User B's patient
        response = self.client.delete(self.detail_url_b)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Confirm patient still exists
        self.assertTrue(Patient.objects.filter(id=self.patient_b.id).exists())

    # -------------------------------------------------------------------------
    # 12. UUID Validation
    # -------------------------------------------------------------------------
    def test_uuid_validation(self):
        self.client.force_authenticate(user=self.user_a)

        # Non-existent UUID
        random_uuid = uuid.uuid4()
        non_existent_url = reverse("patients:patient-detail", kwargs={"id": random_uuid})
        res_non_existent = self.client.get(non_existent_url)
        self.assertEqual(res_non_existent.status_code, status.HTTP_404_NOT_FOUND)

        # Invalid UUID format in URL
        invalid_url = "/api/patients/not-a-valid-uuid-format/"
        res_invalid = self.client.get(invalid_url)
        self.assertEqual(res_invalid.status_code, status.HTTP_404_NOT_FOUND)

    # -------------------------------------------------------------------------
    # 13. Successful Patient Update (Owner)
    # -------------------------------------------------------------------------
    def test_successful_patient_update(self):
        self.client.force_authenticate(user=self.user_a)
        update_payload = {
            "full_name": "John Updated Doe",
            "email": "john.updated@example.com",
            "phone_number": "+1-555-9988",
            "date_of_birth": "1990-05-15",
            "gender": "Male",
            "address": "999 New St, Metropolis",
            "medical_history": "Hypertension controlled via medication.",
        }

        # PUT full update
        response = self.client.put(self.detail_url_a, update_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], "John Updated Doe")
        self.assertEqual(response.data["email"], "john.updated@example.com")
        self.assertEqual(response.data["phone_number"], "+1-555-9988")

        # PATCH partial update
        patch_res = self.client.patch(
            self.detail_url_a, {"address": "777 Patch Blvd"}, format="json"
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data["address"], "777 Patch Blvd")

    # -------------------------------------------------------------------------
    # 14. Successful Patient Deletion (Owner)
    # -------------------------------------------------------------------------
    def test_successful_patient_deletion(self):
        self.client.force_authenticate(user=self.user_a)
        response = self.client.delete(self.detail_url_a)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Patient.objects.filter(id=self.patient_a.id).exists())

        # Subsequent retrieval returns 404
        get_res = self.client.get(self.detail_url_a)
        self.assertEqual(get_res.status_code, status.HTTP_404_NOT_FOUND)

    # -------------------------------------------------------------------------
    # 15. Model String Representation
    # -------------------------------------------------------------------------
    def test_model_str_representation(self):
        self.assertEqual(
            str(self.patient_a),
            f"John Doe ({self.patient_a.id})",
        )
