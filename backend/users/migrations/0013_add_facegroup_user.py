# Generated migration to add user field to FaceGroup

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_reset_face_detection_attempted'),
    ]

    operations = [
        migrations.AddField(
            model_name='facegroup',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='face_groups', to='users.customuser'),
        ),
    ]
