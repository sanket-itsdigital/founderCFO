from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.base_user import BaseUserManager

from backend.enums import UserRoleChoices, VerificationStatusChoices
from backend.models import BaseModel


# Create your models here.
class UserManager(BaseUserManager):
    """Custom user manager that uses email as the unique identifier."""

    use_in_migrations = True

    def get_by_natural_key(self, username):
        """Allow authentication to look up by the model's USERNAME_FIELD."""
        return self.get(**{self.model.USERNAME_FIELD: username})

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    first_name = models.CharField(max_length=30)
    middle_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    mobile_number = models.CharField(
        max_length=15,
        unique=True,
        blank=True,
        null=True,
    )
    profile_image = models.ImageField(
        upload_to="users/profile_images/",
        blank=True,
        null=True,
    )
    role = models.CharField(
        choices=UserRoleChoices.choices,
        default=UserRoleChoices.FOUNDER,
        max_length=20,
    )
    status = models.CharField(
        choices=VerificationStatusChoices.choices,
        default=VerificationStatusChoices.PENDING,
        max_length=20,
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join(part for part in parts if part).strip()

    class Meta:
        db_table = "user"
        verbose_name = "User"
        verbose_name_plural = "Users"


class Company(BaseModel):
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="companies",
    )
    name = models.CharField(max_length=100)
    GST_number = models.CharField(max_length=15, unique=True)
    address = models.TextField()
    no_of_employees = models.PositiveIntegerField()
    nature_of_business = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "company"
        verbose_name = "Company"
        verbose_name_plural = "Companies"


class TeamMember(BaseModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="team_members",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="team_memberships",
    )
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invited_team_members",
    )
    role = models.CharField(
        choices=UserRoleChoices.choices,
        max_length=20,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "team_member"
        verbose_name = "Team Member"
        verbose_name_plural = "Team Members"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "user"],
                name="unique_company_user_membership",
            )
        ]

    def __str__(self):
        return f"{self.company.name} - {self.user.email}"
