from django.db import migrations


def reset_face_detection_attempted(apps, schema_editor):
    Media = apps.get_model('users', 'Media')
    # Reset flag for approved images that have no face tags
    Media.objects.filter(
        status='approved',
        media_type='image',
        face_detection_attempted=True,
        face_tags__isnull=True
    ).update(face_detection_attempted=False)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_add_media_face_detection_attempted'),
    ]

    operations = [
        migrations.RunPython(reset_face_detection_attempted, migrations.RunPython.noop),
    ]
