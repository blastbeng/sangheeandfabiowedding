from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('users', '0017_media_unique_user_content_hash'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='facetag',
            constraint=models.UniqueConstraint(
                fields=['media', 'face_group'],
                name='unique_media_face_group'
            ),
        ),
    ]
