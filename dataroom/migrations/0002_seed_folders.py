from django.db import migrations

DEFAULT_FOLDERS = [
    "Company & Legal Documents",
    "Shareholders Details",
    "Previous Funding (SAFE/NOTEs)",
    "Pitchdeck, Financial Model & Valuation",
    "Master Agreements",
    "Financial Information (Actual)",
    "Business & Operational Metrics",
    "Competitive Landscape",
    "Product & Technology",
    "Legal & Compliance",
    "Team & HR",
    "Market & Strategic Information",
    "Media Kit",
]


def seed_default_folders(apps, schema_editor):
    Folder = apps.get_model("dataroom", "Folder")
    Company = apps.get_model("accounts", "Company")
    for company in Company.objects.all():
        existing = set(
            Folder.objects.filter(company=company).values_list("name", flat=True)
        )
        for name in DEFAULT_FOLDERS:
            if name not in existing:
                Folder.objects.create(company=company, name=name)


def unseed_default_folders(apps, schema_editor):
    Folder = apps.get_model("dataroom", "Folder")
    Folder.objects.filter(name__in=DEFAULT_FOLDERS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("dataroom", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_default_folders, reverse_code=unseed_default_folders),
    ]
