import uuid
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.utils import timezone
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class UserModelTests(APITestCase):
    """
    Unit tests for the custom User model and UserManager.
    """

    def test_create_user_successful(self):
        email = "test@example.com"
        name = "Test User"
        password = "SecurePassword123!"
        user = User.objects.create_user(email=email, name=name, password=password)

        self.assertEqual(user.email, email)
        self.assertEqual(user.name, name)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password(password))
        self.assertNotEqual(user.password, password)  # Securely hashed
        self.assertIsInstance(user.id, uuid.UUID)

    def test_create_user_email_normalized(self):
        email = "User.Name@Example.COM"
        user = User.objects.create_user(email=email, name="Case Test", password="Password123!")
        self.assertEqual(user.email, "user.name@example.com")

    def test_create_user_missing_email_raises_error(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", name="No Email", password="Password123!")

    def test_create_user_missing_name_raises_error(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="user@example.com", name="", password="Password123!")

    def test_create_superuser_successful(self):
        superuser = User.objects.create_superuser(
            email="admin@example.com",
            name="Admin User",
            password="AdminPassword123!",
        )
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_active)

    def test_create_superuser_invalid_staff_flag(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="admin2@example.com",
                name="Admin 2",
                password="Password123!",
                is_staff=False,
            )

    def test_create_superuser_invalid_superuser_flag(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="admin3@example.com",
                name="Admin 3",
                password="Password123!",
                is_superuser=False,
            )

    def test_user_string_representation(self):
        user = User.objects.create_user(
            email="string@example.com",
            name="String User",
            password="Password123!",
        )
        self.assertEqual(str(user), "String User (string@example.com)")


class DatabaseConstraintAndIntegrityTests(APITestCase):
    """
    Tests for database-level case-insensitive unique constraints and email normalization.
    """

    def test_email_normalized_in_model_save(self):
        """
        Ensure User.save() strips whitespace and normalizes email to lowercase.
        """
        user = User(name="Save Test", email="  Doctor.Who@Tardis.COM  ")
        user.set_password("SecurePassword123!")
        user.save()

        self.assertEqual(user.email, "doctor.who@tardis.com")
        refreshed = User.objects.get(id=user.id)
        self.assertEqual(refreshed.email, "doctor.who@tardis.com")

    def test_three_casing_variants_cannot_coexist(self):
        """
        Ensure Prince@example.com, prince@example.com, and PRINCE@example.com
        cannot coexist in the database.
        """
        # Create first variant
        User.objects.create_user(
            email="Prince@example.com",
            name="Prince Variant 1",
            password="Password123!",
        )

        # Attempting second variant via create_user raises IntegrityError
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    email="prince@example.com",
                    name="Prince Variant 2",
                    password="Password123!",
                )

        # Attempting third uppercase variant raises IntegrityError
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    email="PRINCE@example.com",
                    name="Prince Variant 3",
                    password="Password123!",
                )

    def test_database_level_constraint_enforcement_bypassing_python_normalization(self):
        """
        Bypass User.save() normalization using bulk_create (which does not call save())
        to verify that the database itself (PostgreSQL or SQLite functional index) rejects
        case-insensitive duplicates.
        """
        # Insert initial record with mixed casing without calling save()
        User.objects.bulk_create([
            User(
                id=uuid.uuid4(),
                email="Bypass.Case@example.com",
                name="Bypass User 1",
                is_active=True,
                is_staff=False,
                password="fakehashedpassword",
            )
        ])

        # Attempt bulk_create with lowercase duplicate:
        # Must be rejected directly by the database unique_case_insensitive_email constraint!
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.bulk_create([
                    User(
                        id=uuid.uuid4(),
                        email="bypass.case@example.com",
                        name="Bypass User 2",
                        is_active=True,
                        is_staff=False,
                        password="fakehashedpassword",
                    )
                ])


class RegistrationAPITests(APITestCase):
    """
    Integration tests for POST /api/auth/register/
    """

    def setUp(self):
        self.register_url = reverse("accounts:register")
        self.valid_payload = {
            "name": "Prince Jha",
            "email": "prince@example.com",
            "password": "StrongPassword123",
        }

    def test_successful_registration(self):
        response = self.client.post(self.register_url, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("message", response.data)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["email"], "prince@example.com")
        self.assertEqual(response.data["user"]["name"], "Prince Jha")
        self.assertIn("id", response.data["user"])

        # Confirm user exists in DB and password is not plain text
        user = User.objects.get(email="prince@example.com")
        self.assertTrue(user.check_password("StrongPassword123"))
        self.assertNotEqual(user.password, "StrongPassword123")
        self.assertNotIn("password", response.data["user"])

    def test_duplicate_email_rejection(self):
        # Create user first
        self.client.post(self.register_url, self.valid_payload, format="json")

        # Attempt to register with duplicate email (different casing)
        duplicate_payload = {
            "name": "Another Prince",
            "email": "PRINCE@example.com",
            "password": "AnotherPassword123",
        }
        response = self.client.post(self.register_url, duplicate_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_missing_required_fields(self):
        # Missing name
        res1 = self.client.post(
            self.register_url,
            {"email": "test@example.com", "password": "Password123"},
            format="json",
        )
        self.assertEqual(res1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", res1.data)

        # Missing email
        res2 = self.client.post(
            self.register_url,
            {"name": "No Email", "password": "Password123"},
            format="json",
        )
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", res2.data)

        # Missing password
        res3 = self.client.post(
            self.register_url,
            {"name": "No Pass", "email": "nopass@example.com"},
            format="json",
        )
        self.assertEqual(res3.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", res3.data)

    def test_invalid_email_format(self):
        invalid_payload = {
            "name": "Invalid Email",
            "email": "not-an-email",
            "password": "StrongPassword123",
        }
        response = self.client.post(self.register_url, invalid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_weak_password_rejected(self):
        weak_payload = {
            "name": "Weak Pass User",
            "email": "weak@example.com",
            "password": "123",  # Too short and entirely numeric
        }
        response = self.client.post(self.register_url, weak_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)


class LoginAPITests(APITestCase):
    """
    Integration tests for POST /api/auth/login/ and JWT tokens
    """

    def setUp(self):
        self.login_url = reverse("accounts:login")
        self.user_password = "CorrectPassword123!"
        self.user = User.objects.create_user(
            email="loginuser@example.com",
            name="Login User",
            password=self.user_password,
        )

    def test_successful_login(self):
        payload = {
            "email": "loginuser@example.com",
            "password": self.user_password,
        }
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["email"], "loginuser@example.com")
        self.assertEqual(response.data["user"]["name"], "Login User")
        self.assertEqual(response.data["user"]["id"], str(self.user.id))

    def test_login_incorrect_password(self):
        payload = {
            "email": "loginuser@example.com",
            "password": "WrongPassword!",
        }
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("access", response.data)
        self.assertNotIn("password", response.data)

    def test_login_unknown_email(self):
        payload = {
            "email": "unknown@example.com",
            "password": self.user_password,
        }
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_inactive_user(self):
        self.user.is_active = False
        self.user.save()

        payload = {
            "email": "loginuser@example.com",
            "password": self.user_password,
        }
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_case_insensitive_email(self):
        payload = {
            "email": "LOGINUSER@EXAMPLE.COM",
            "password": self.user_password,
        }
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)


class TokenRefreshAndPermissionsTests(APITestCase):
    """
    Integration tests for POST /api/auth/token/refresh/ and protected endpoint permissions
    """

    def setUp(self):
        self.login_url = reverse("accounts:login")
        self.refresh_url = reverse("accounts:token_refresh")
        self.profile_url = reverse("accounts:profile")

        self.user_password = "Password123!"
        self.user = User.objects.create_user(
            email="permuser@example.com",
            name="Permission User",
            password=self.user_password,
        )

        # Login to get tokens
        login_res = self.client.post(
            self.login_url,
            {"email": "permuser@example.com", "password": self.user_password},
            format="json",
        )
        self.access_token = login_res.data["access"]
        self.refresh_token = login_res.data["refresh"]

    def test_token_refresh_successful(self):
        response = self.client.post(
            self.refresh_url,
            {"refresh": self.refresh_token},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_token_refresh_invalid_token(self):
        response = self.client.post(
            self.refresh_url,
            {"refresh": "invalid-token-string"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_protected_endpoint_without_token_denied(self):
        # Global default is IsAuthenticated
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_protected_endpoint_with_valid_token_allowed(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "permuser@example.com")
        self.assertEqual(response.data["name"], "Permission User")
        self.assertEqual(response.data["id"], str(self.user.id))
