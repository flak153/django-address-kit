from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Address",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("raw", models.CharField(blank=True, max_length=255)),
                ("address1", models.CharField(blank=True, max_length=255)),
                ("address2", models.CharField(blank=True, max_length=255)),
                ("locality", models.CharField(blank=True, max_length=128)),
                ("state", models.CharField(blank=True, max_length=64)),
                ("postal_code", models.CharField(blank=True, max_length=20)),
                ("country", models.CharField(blank=True, max_length=128)),
            ],
            options={
                "verbose_name": "Legacy Address",
                "verbose_name_plural": "Legacy Addresses",
            },
        ),
    ]
