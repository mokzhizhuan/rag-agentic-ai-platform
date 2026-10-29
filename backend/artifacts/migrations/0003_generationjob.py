from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('artifacts', '0002_characterprofile')]
    operations = [
        migrations.CreateModel(name='GenerationJob', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('owner_sub', models.CharField(max_length=120, db_index=True)),
            ('status', models.CharField(max_length=16, default='queued', db_index=True)),
            ('stage', models.CharField(max_length=140, default='Queued')),
            ('percent', models.PositiveSmallIntegerField(default=0)),
            ('prompt', models.TextField(max_length=2500)),
            ('provider', models.CharField(max_length=24)),
            ('output_format', models.CharField(max_length=24)),
            ('parameters', models.JSONField(default=dict)),
            ('artifact_id', models.PositiveIntegerField(null=True, blank=True)),
            ('error', models.TextField(blank=True)),
            ('cancel_requested', models.BooleanField(default=False)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('started_at', models.DateTimeField(null=True, blank=True)),
            ('finished_at', models.DateTimeField(null=True, blank=True)),
        ], options={'ordering': ['-created_at']}),
        migrations.CreateModel(name='GenerationJobInput', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('filename', models.CharField(max_length=240)),
            ('file', models.FileField(upload_to='job_inputs_private/%Y/%m/')),
            ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='uploads', to='artifacts.generationjob')),
        ]),
    ]
