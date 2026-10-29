from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [('chat', '0005_memory_preference')]
    operations = [
        migrations.CreateModel(name='GeneratedArtifact', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('owner_sub', models.CharField(db_index=True, max_length=120)),
            ('prompt', models.TextField(max_length=2500)),
            ('filename', models.CharField(max_length=180)),
            ('format', models.CharField(max_length=12)),
            ('provider', models.CharField(max_length=24)),
            ('content', models.FileField(upload_to='artifacts_private/%Y/%m/')),
            ('byte_size', models.PositiveBigIntegerField(default=0)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('conversation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='generated_artifacts', to='chat.conversation')),
        ], options={'ordering': ['-created_at']}),
    ]
