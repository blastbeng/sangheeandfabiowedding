from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_add_facetag_thumbnail'),
    ]

    operations = [
        migrations.AddField(
            model_name='media',
            name='face_detection_attempted',
            field=models.BooleanField(default=False),
        ),
    ]
