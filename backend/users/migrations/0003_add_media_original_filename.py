# Generated migration to add original_filename to Media

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_add_sitesettings_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='media',
            name='original_filename',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
