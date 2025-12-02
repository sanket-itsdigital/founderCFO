from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.base_user import BaseUserManager

from backend.enums import (
    NatureOfBusinessChoices,
    UserRoleChoices,
    VerificationStatusChoices,
)
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
    first_name = models.CharField(max_length=30, blank=True, null=True)
    middle_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)
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
    nature_of_business = models.CharField(
        max_length=100,
        choices=NatureOfBusinessChoices.choices,
        default=NatureOfBusinessChoices.SAAS,
    )

    # Capital Structure Fields
    face_value_per_share = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=Decimal("0"),
        help_text="Face value per share (used to calculate capital amounts)",
    )
    authorized_capital_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Authorized Capital in currency",
    )
    authorized_capital_shares = models.PositiveIntegerField(
        default=0, help_text="Number of authorized shares"
    )
    issued_capital_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Issued Capital in currency",
    )
    issued_capital_shares = models.PositiveIntegerField(
        default=0, help_text="Number of issued shares"
    )
    paid_up_capital_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Paid-up Capital in currency",
    )
    paid_up_capital_shares = models.PositiveIntegerField(
        default=0, help_text="Number of paid-up shares"
    )
    securities_premium = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Securities Premium (Share Premium Account)",
    )

    # ESOP Pool Configuration
    esop_pool_size = models.PositiveIntegerField(
        default=0, help_text="ESOP Pool size in number of shares"
    )
    esop_pool_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0"),
        help_text="ESOP Pool as percentage of authorized shares",
    )
    esop_pool_notes = models.TextField(
        blank=True, null=True, help_text="Notes about ESOP pool configuration"
    )

    def clean(self):
        """Validate capital structure relationships."""
        super().clean()

        # Validate: Authorized Capital > Issued Capital >= Paid-up Capital
        if self.authorized_capital_amount and self.issued_capital_amount:
            if self.authorized_capital_amount <= self.issued_capital_amount:
                raise ValidationError(
                    {
                        "authorized_capital_amount": "Authorized Capital must be greater than Issued Capital."
                    }
                )

        if self.issued_capital_amount and self.paid_up_capital_amount:
            if self.issued_capital_amount < self.paid_up_capital_amount:
                raise ValidationError(
                    {
                        "paid_up_capital_amount": "Paid-up Capital cannot exceed Issued Capital."
                    }
                )

        # Validate shares consistency
        if self.authorized_capital_shares and self.issued_capital_shares:
            if self.authorized_capital_shares <= self.issued_capital_shares:
                raise ValidationError(
                    {
                        "authorized_capital_shares": "Authorized shares must be greater than issued shares."
                    }
                )

        if self.issued_capital_shares and self.paid_up_capital_shares:
            if self.issued_capital_shares < self.paid_up_capital_shares:
                raise ValidationError(
                    {
                        "paid_up_capital_shares": "Paid-up shares cannot exceed issued shares."
                    }
                )

        # Validate ESOP pool doesn't exceed authorized shares
        if self.esop_pool_size and self.authorized_capital_shares:
            if self.esop_pool_size > self.authorized_capital_shares:
                raise ValidationError(
                    {
                        "esop_pool_size": "ESOP pool size cannot exceed authorized shares."
                    }
                )

    def _auto_calculate_capital_fields(self):
        """
        Automatically calculate capital structure fields based on available data.

        Calculation priority:
        1. If face_value_per_share + amount → calculate shares
        2. If face_value_per_share + shares → calculate amount
        3. If amount + shares → calculate face_value_per_share
        """
        if not self.face_value_per_share or self.face_value_per_share == 0:
            # Try to calculate face_value_per_share from existing data
            self._calculate_face_value_from_existing_data()

        # Now calculate missing fields using face_value_per_share
        if self.face_value_per_share and self.face_value_per_share > 0:
            self._calculate_missing_fields_from_face_value()

    def _calculate_face_value_from_existing_data(self):
        """
        Calculate face_value_per_share from any available amount/shares pair.
        Priority: authorized > issued > paid_up
        """
        # Try authorized capital first
        if (
            self.authorized_capital_amount
            and self.authorized_capital_amount > 0
            and self.authorized_capital_shares
            and self.authorized_capital_shares > 0
        ):
            self.face_value_per_share = (
                self.authorized_capital_amount / Decimal(self.authorized_capital_shares)
            ).quantize(Decimal("0.0001"))
            return

        # Try issued capital
        if (
            self.issued_capital_amount
            and self.issued_capital_amount > 0
            and self.issued_capital_shares
            and self.issued_capital_shares > 0
        ):
            self.face_value_per_share = (
                self.issued_capital_amount / Decimal(self.issued_capital_shares)
            ).quantize(Decimal("0.0001"))
            return

        # Try paid-up capital
        if (
            self.paid_up_capital_amount
            and self.paid_up_capital_amount > 0
            and self.paid_up_capital_shares
            and self.paid_up_capital_shares > 0
        ):
            self.face_value_per_share = (
                self.paid_up_capital_amount / Decimal(self.paid_up_capital_shares)
            ).quantize(Decimal("0.0001"))
            return

    def _calculate_missing_fields_from_face_value(self):
        """
        Calculate missing amounts/shares using face_value_per_share.
        """
        # Calculate authorized capital
        if (
            self.authorized_capital_amount
            and self.authorized_capital_amount > 0
            and not self.authorized_capital_shares
        ):
            # Amount provided, calculate shares
            self.authorized_capital_shares = int(
                (self.authorized_capital_amount / self.face_value_per_share).quantize(
                    Decimal("1")
                )
            )
        elif (
            self.authorized_capital_shares
            and self.authorized_capital_shares > 0
            and not self.authorized_capital_amount
        ):
            # Shares provided, calculate amount
            self.authorized_capital_amount = (
                Decimal(self.authorized_capital_shares) * self.face_value_per_share
            ).quantize(Decimal("0.01"))

        # Calculate issued capital
        if (
            self.issued_capital_amount
            and self.issued_capital_amount > 0
            and not self.issued_capital_shares
        ):
            self.issued_capital_shares = int(
                (self.issued_capital_amount / self.face_value_per_share).quantize(
                    Decimal("1")
                )
            )
        elif (
            self.issued_capital_shares
            and self.issued_capital_shares > 0
            and not self.issued_capital_amount
        ):
            self.issued_capital_amount = (
                Decimal(self.issued_capital_shares) * self.face_value_per_share
            ).quantize(Decimal("0.01"))

        # Calculate paid-up capital
        if (
            self.paid_up_capital_amount
            and self.paid_up_capital_amount > 0
            and not self.paid_up_capital_shares
        ):
            self.paid_up_capital_shares = int(
                (self.paid_up_capital_amount / self.face_value_per_share).quantize(
                    Decimal("1")
                )
            )
        elif (
            self.paid_up_capital_shares
            and self.paid_up_capital_shares > 0
            and not self.paid_up_capital_amount
        ):
            self.paid_up_capital_amount = (
                Decimal(self.paid_up_capital_shares) * self.face_value_per_share
            ).quantize(Decimal("0.01"))

    def save(self, *args, **kwargs):
        """
        Override save to run validation and auto-calculate capital fields.

        Automatically calculates missing capital structure fields based on:
        - face_value_per_share + amount → shares
        - face_value_per_share + shares → amount
        - amount + shares → face_value_per_share
        """
        # Auto-calculate capital structure fields
        self._auto_calculate_capital_fields()

        # Run validation
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def total_shareholders_funds(self):
        """Calculate total shareholders' funds: Paid-up Capital + Securities Premium"""
        return (self.paid_up_capital_amount or Decimal("0")) + (
            self.securities_premium or Decimal("0")
        )

    @property
    def capital_utilization_percentage(self):
        """Calculate capital utilization: (Issued / Authorized) * 100"""
        if not self.authorized_capital_amount or self.authorized_capital_amount == 0:
            return Decimal("0")
        issued = self.issued_capital_amount or Decimal("0")
        return (issued / self.authorized_capital_amount) * Decimal("100")

    @property
    def available_capital(self):
        """Calculate available capital: Authorized - Issued"""
        authorized = self.authorized_capital_amount or Decimal("0")
        issued = self.issued_capital_amount or Decimal("0")
        return authorized - issued

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
