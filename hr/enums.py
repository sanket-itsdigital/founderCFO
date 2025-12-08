from django.db.models import TextChoices


class Gender(TextChoices):
    MALE = "Male", "Male"
    FEMALE = "Female", "Female"


class EmploymentType(TextChoices):
    FULL_TIME = "Full-time", "Full-time"
    PART_TIME = "Part-time", "Part-time"
    CONTRACTOR = "Contractor", "Contractor"
    INTERN = "Intern", "Intern"


class EmploymentStatus(TextChoices):
    ACTIVE = "Active", "Active"
    RESIGNED = "Resigned", "Resigned"
    INACTIVE = "Inactive", "Inactive"


class Level(TextChoices):
    VP = "VP", "VP"
    DIRECTOR = "Director", "Director"
    MANAGER = "Manager", "Manager"
    LEAD = "Lead", "Lead"
    SENIOR = "Senior", "Senior"
    MID = "Mid", "Mid"
    JUNIOR = "Junior", "Junior"
