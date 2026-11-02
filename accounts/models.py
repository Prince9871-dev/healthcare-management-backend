import uuid
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.db.models import UniqueConstraint
from django.db.models.functions import Lower
from django.utils import timezone


class UserManager(BaseUserManager):
    """
    Custom user manager where email is the unique identifier
    for authentication instead of usernames.
    """

    def create_user(self, email, name, password=None, **extra_fields):
        """
        Create and return a regular User with an email, name, and hashed password.
        """
        if not email:
            raise ValueError("The Email field must be set.")
        if not name or not name.strip():
            raise ValueError("The Name field must be set.")

        email = self.normalize_email(email).lower()
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        user = self.model(email=email, name=name.strip(), **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        """
        Create and return a superuser with an email, name, and hashed password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, name, password, **extra_fields)

    def get_by_natural_key(self, email):
        """
        Allow case-insensitive natural key lookup for email logins.
        """
        return self.get(**{f"{self.model.USERNAME_FIELD}__iexact": email})


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model for the Healthcare Management Backend.
    Uses UUID primary key and case-insensitive unique email constraint.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique UUID identifier for this user.",
    )
    email = models.EmailField(
        unique=True,
        max_length=255,
        db_index=True,
        help_text="Unique email address used for login.",
    )
    name = models.CharField(
        max_length=255,
        help_text="Full name of the user.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Designates whether this user account is active.",
    )
    is_staff = models.BooleanField(
        default=False,
        help_text="Designates whether the user can log into the Django admin site.",
    )
    date_joined = models.DateTimeField(
        default=timezone.now,
        help_text="Timestamp when the user account was created.",
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]
        constraints = [
            UniqueConstraint(
                Lower("email"),
                name="unique_case_insensitive_email",
            ),
        ]

    def clean(self):
        super().clean()
        if self.email:
            self.email = self.email.strip().lower()

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.email})"
