# Generated migration to create FaceTag model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_add_media_original_filename'),
    ]

    operations = [
        migrations.CreateModel(
            name='FaceTag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='Unknown', max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('media', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='face_tags', to='users.media')),
            ],
            options={
                'unique_together': {('media', 'name')},
            },
        ),
    ]
