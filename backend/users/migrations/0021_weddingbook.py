from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0020_add_media_similarity_position'),
    ]

    operations = [
        migrations.CreateModel(
            name='WeddingBook',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed')], db_index=True, default='pending', max_length=20)),
                ('progress', models.PositiveSmallIntegerField(default=0)),
                ('selected_media_ids', models.JSONField(default=list)),
                ('captions_data', models.JSONField(default=dict)),
                ('pdf_file', models.FileField(blank=True, null=True, upload_to='wedding_books/')),
                ('error_message', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
