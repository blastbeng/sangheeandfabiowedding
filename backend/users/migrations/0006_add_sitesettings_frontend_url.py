# Generated migration to add frontend_url to SiteSettings

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_remove_media_rejection_reason'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='frontend_url',
            field=models.URLField(blank=True, max_length=255, null=True),
        ),
    ]
