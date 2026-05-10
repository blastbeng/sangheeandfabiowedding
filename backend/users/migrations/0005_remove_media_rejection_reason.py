# Generated migration to remove rejection_reason from Media

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_create_facetag'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='media',
            name='rejection_reason',
        ),
    ]
