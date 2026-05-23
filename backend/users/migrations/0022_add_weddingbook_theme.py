from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0021_weddingbook'),
    ]

    operations = [
        migrations.AddField(
            model_name='weddingbook',
            name='theme',
            field=models.CharField(
                choices=[
                    ('elegant', 'Elegant'),
                    ('classic', 'Classic'),
                    ('modern', 'Modern'),
                    ('vintage', 'Vintage'),
                    ('romantic', 'Romantic'),
                ],
                default='elegant',
                max_length=20,
            ),
        ),
    ]
