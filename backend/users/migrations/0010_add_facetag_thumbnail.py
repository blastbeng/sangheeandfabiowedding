# Generated migration to add thumbnail field to FaceTag

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_add_facegroup_and_facetag_face_group'),
    ]

    operations = [
        migrations.AddField(
            model_name='facetag',
            name='thumbnail',
            field=models.ImageField(blank=True, null=True, upload_to='facetags/'),
        ),
    ]
