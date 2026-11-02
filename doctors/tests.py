import uuid
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Doctor

User = get_user_model()


class DoctorAPITests(APITestCase):
    """
    Comprehensive test suite for Doctor Management APIs and ownership isolation.
    Enforces PostgreSQL-first execution and IDOR defenses.
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

        # Create an existing doctor owned by User A
        self.doctor_a = Doctor.objects.create(
            full_name="Gregory House",
            email="dr.house@diagnostics.org",
            phone_number="+1-555-0101",
            specialization="Diagnostic Medicine",
            experience_years=20,
            qualification="MD, Board Certified",
            address="Princeton-Plainsboro Teaching Hospital",
            created_by=self.user_a,
        )

        # Create an existing doctor owned by User B
        self.doctor_b = Doctor.objects.create(
            full_name="James Wilson",
            email="dr.wilson@oncology.org",
            phone_number="+1-555-0102",
            specialization="Oncology",
            experience_years=18,
            qualification="MD, Chief of Oncology",
            address="Princeton-Plainsboro Teaching Hospital",
            created_by=self.user_b,
        )

        self.list_create_url = reverse("doctors:doctor-list-create")
        self.detail_url_a = reverse(
            "doctors:doctor-detail", kwargs={"id": self.doctor_a.id}
        )
        self.detail_url_b = reverse(
            "doctors:doctor-detail", kwargs={"id": self.doctor_b.id}
        )

        self.valid_payload = {
            "full_name": "Allison Cameron",
            "email": "dr.cameron@example.com",
            "phone_number": "+1-555-0103",
            "specialization": "Immunology",
            "experience_years": 8,
            "qualification": "MD, Immunology Fellow",
            "address": "456 Research Way, Princeton, NJ",
        }

    # -------------------------------------------------------------------------
    # 1. Successful Doctor Creation
    # -------------------------------------------------------------------------
    def test_successful_doctor_creation(self):
        self.client.force_authenticate(user=self.user_a)
        response = self.client.post(self.list_create_url, self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["full_name"], "Allison Cameron")
        self.assertEqual(response.data["email"], "dr.cameron@example.com")
        self.assertEqual(response.data["specialization"], "Immunology")
        self.assertEqual(response.data["experience_years"], 8)
        self.assertEqual(response.data["created_by"], self.user_a.id)
        self.assertIn("id", response.data)

        # Verify DB record
        created_doctor = Doctor.objects.get(id=response.data["id"])
        self.assertEqual(created_doctor.created_by, self.user_a)

    # -------------------------------------------------------------------------
    # 2. Unauthenticated Access Rejected
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
    # 5. Missing Required Fields Rejected
    # -------------------------------------------------------------------------
    def test_missing_required_fields(self):
        self.client.force_authenticate(user=self.user_a)

        # Missing full_name
        p1 = self.valid_payload.copy()
        del p1["full_name"]
        res1 = self.client.post(self.list_create_url, p1, format="json")
        self.assertEqual(res1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("full_name", res1.data)

        # Missing email
        p2 = self.valid_payload.copy()
        del p2["email"]
        res2 = self.client.post(self.list_create_url, p2, format="json")
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", res2.data)

        # Missing phone_number
        p3 = self.valid_payload.copy()
        del p3["phone_number"]
        res3 = self.client.post(self.list_create_url, p3, format="json")
        self.assertEqual(res3.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", res3.data)

        # Missing specialization
        p4 = self.valid_payload.copy()
        del p4["specialization"]
        res4 = self.client.post(self.list_create_url, p4, format="json")
        self.assertEqual(res4.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("specialization", res4.data)

        # Blank full_name
        p5 = self.valid_payload.copy()
        p5["full_name"] = "   "
        res5 = self.client.post(self.list_create_url, p5, format="json")
        self.assertEqual(res5.status_code, status.HTTP_400_BAD_REQUEST)

    # -------------------------------------------------------------------------
    # 6. Negative Experience Years Rejected
    # -------------------------------------------------------------------------
    def test_negative_experience_years_rejected(self):
        self.client.force_authenticate(user=self.user_a)
        payload = self.valid_payload.copy()
        payload["experience_years"] = -3

        response = self.client.post(self.list_create_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("experience_years", response.data)
        self.assertIn("negative", str(response.data["experience_years"]).lower())

    # -------------------------------------------------------------------------
    # 7. Client Cannot Spoof created_by
    # -------------------------------------------------------------------------
    def test_client_cannot_assign_another_user_as_created_by(self):
        self.client.force_authenticate(user=self.user_a)
        payload = self.valid_payload.copy()
        # Attempt to spoof ownership to User B
        payload["created_by"] = str(self.user_b.id)

        response = self.client.post(self.list_create_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify ownership remains User A
        created_doctor = Doctor.objects.get(id=response.data["id"])
        self.assertEqual(created_doctor.created_by, self.user_a)
        self.assertNotEqual(created_doctor.created_by, self.user_b)

    # -------------------------------------------------------------------------
    # 8. All Authenticated Users Can Retrieve Doctor Directory
    # -------------------------------------------------------------------------
    def test_authenticated_users_can_retrieve_all_doctors(self):
        # User A can retrieve all doctors in the directory
        self.client.force_authenticate(user=self.user_a)
        response_a = self.client.get(self.list_create_url)
        self.assertEqual(response_a.status_code, status.HTTP_200_OK)
        returned_ids_a = [d["id"] for d in response_a.data]
        self.assertIn(str(self.doctor_a.id), returned_ids_a)
        self.assertIn(str(self.doctor_b.id), returned_ids_a)

        # User B can also retrieve all doctors in the directory
        self.client.force_authenticate(user=self.user_b)
        response_b = self.client.get(self.list_create_url)
        self.assertEqual(response_b.status_code, status.HTTP_200_OK)
        returned_ids_b = [d["id"] for d in response_b.data]
        self.assertIn(str(self.doctor_a.id), returned_ids_b)
        self.assertIn(str(self.doctor_b.id), returned_ids_b)

    # -------------------------------------------------------------------------
    # 9. Authenticated User Can Retrieve Any Doctor Detail
    # -------------------------------------------------------------------------
    def test_authenticated_user_can_retrieve_any_doctor_detail(self):
        # User A can retrieve User B's doctor detail from the directory
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(self.detail_url_b)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], "James Wilson")
        self.assertEqual(response.data["specialization"], "Oncology")

    # -------------------------------------------------------------------------
    # 10. Cross-User Update Protection (Creator Only)
    # -------------------------------------------------------------------------
    def test_user_cannot_update_another_users_doctor(self):
        self.client.force_authenticate(user=self.user_a)
        update_payload = self.valid_payload.copy()
        update_payload["full_name"] = "Hacked Doctor"

        # User A tries to PUT update User B's doctor -> 403 Forbidden
        response = self.client.put(self.detail_url_b, update_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Confirm User B's doctor remains unchanged in database
        self.doctor_b.refresh_from_db()
        self.assertEqual(self.doctor_b.full_name, "James Wilson")

    # -------------------------------------------------------------------------
    # 11. Cross-User Delete Protection (Creator Only)
    # -------------------------------------------------------------------------
    def test_user_cannot_delete_another_users_doctor(self):
        self.client.force_authenticate(user=self.user_a)

        # User A tries to DELETE User B's doctor -> 403 Forbidden
        response = self.client.delete(self.detail_url_b)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Confirm doctor still exists in database
        self.assertTrue(Doctor.objects.filter(id=self.doctor_b.id).exists())

    # -------------------------------------------------------------------------
    # 12. Successful Doctor Update (Owner)
    # -------------------------------------------------------------------------
    def test_successful_doctor_update(self):
        self.client.force_authenticate(user=self.user_a)
        update_payload = {
            "full_name": "Gregory House, MD",
            "email": "house.head@diagnostics.org",
            "phone_number": "+1-555-9900",
            "specialization": "Nephrology & Infectious Diseases",
            "experience_years": 25,
            "qualification": "MD, Double Board Certified",
            "address": "Floor 4, Diagnostic Wing",
        }

        # PUT full update
        response = self.client.put(self.detail_url_a, update_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], "Gregory House, MD")
        self.assertEqual(response.data["experience_years"], 25)

        # PATCH partial update
        patch_res = self.client.patch(
            self.detail_url_a, {"qualification": "MD, Fellow"}, format="json"
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data["qualification"], "MD, Fellow")

    # -------------------------------------------------------------------------
    # 13. Successful Doctor Deletion (Owner)
    # -------------------------------------------------------------------------
    def test_successful_doctor_deletion(self):
        self.client.force_authenticate(user=self.user_a)
        response = self.client.delete(self.detail_url_a)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Doctor.objects.filter(id=self.doctor_a.id).exists())

        # Subsequent retrieval returns 404
        get_res = self.client.get(self.detail_url_a)
        self.assertEqual(get_res.status_code, status.HTTP_404_NOT_FOUND)

    # -------------------------------------------------------------------------
    # 14. Invalid UUID Handling
    # -------------------------------------------------------------------------
    def test_invalid_uuid_handling(self):
        self.client.force_authenticate(user=self.user_a)

        # Non-existent UUID
        random_uuid = uuid.uuid4()
        non_existent_url = reverse("doctors:doctor-detail", kwargs={"id": random_uuid})
        res_non_existent = self.client.get(non_existent_url)
        self.assertEqual(res_non_existent.status_code, status.HTTP_404_NOT_FOUND)

        # Invalid UUID format string
        invalid_url = "/api/doctors/not-a-valid-uuid/"
        res_invalid = self.client.get(invalid_url)
        self.assertEqual(res_invalid.status_code, status.HTTP_404_NOT_FOUND)

    # -------------------------------------------------------------------------
    # 15. Correct HTTP Status Codes
    # -------------------------------------------------------------------------
    def test_correct_http_status_codes(self):
        self.client.force_authenticate(user=self.user_a)

        # GET list -> 200
        res = self.client.get(self.list_create_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # POST valid -> 201
        res = self.client.post(self.list_create_url, self.valid_payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # POST invalid -> 400
        res = self.client.post(self.list_create_url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # GET detail -> 200
        res = self.client.get(self.detail_url_a)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # DELETE -> 204
        res = self.client.delete(self.detail_url_a)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    # -------------------------------------------------------------------------
    # 16. Model String Representation
    # -------------------------------------------------------------------------
    def test_model_str_representation(self):
        self.assertEqual(
            str(self.doctor_a),
            f"Dr. Gregory House (Diagnostic Medicine) [{self.doctor_a.id}]",
        )
