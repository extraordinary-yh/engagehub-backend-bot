# Manual migration for RedemptionNotification model
# Generated to avoid field rename conflicts

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0019_partnermetrics_remove_eventsubmission_description_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="RedemptionNotification",
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
                ("discord_id", models.CharField(max_length=50)),
                ("reward_name", models.CharField(max_length=255)),
                ("points_spent", models.IntegerField()),
                ("remaining_points", models.IntegerField()),
                ("redemption_id", models.IntegerField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("sent", "Sent"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
            ],
            options={
                "db_table": "redemption_notifications",
                "ordering": ["-created_at"],
            },
        ),
    ]
