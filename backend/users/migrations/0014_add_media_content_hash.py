# Generated migration to add content_hash to Media

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0013_add_facegroup_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='media',
            name='content_hash',
            field=models.CharField(blank=True, db_index=True, max_length=64, null=True),
        ),
    ]
