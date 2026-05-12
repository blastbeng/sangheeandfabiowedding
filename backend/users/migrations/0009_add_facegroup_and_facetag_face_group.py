# Generated migration to add FaceGroup model and face_group field to FaceTag

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_create_failedattempt'),
    ]

    operations = [
        migrations.CreateModel(
            name='FaceGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='', max_length=100)),
                ('thumbnail', models.ImageField(blank=True, null=True, upload_to='facetags/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'users_facegroup',
            },
        ),
        migrations.AddField(
            model_name='facetag',
            name='face_group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='face_tags', to='users.facegroup'),
        ),
        migrations.AddField(
            model_name='facetag',
            name='encoding',
            field=models.BinaryField(blank=True, null=True),
        ),
        migrations.AlterUniqueTogether(
            name='facetag',
            unique_together=set(),
        ),
    ]
