from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('chat', '0001_initial')]
    operations = [migrations.CreateModel(name='SavedAttachment', fields=[
        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
        ('owner_sub', models.CharField(db_index=True, max_length=120)),
        ('filename', models.CharField(max_length=150)),
        ('sha256', models.CharField(max_length=64)),
        ('byte_size', models.PositiveIntegerField()),
        ('content', models.FileField(upload_to='chat_private/')),
        ('extracted_text', models.TextField()),
        ('created_at', models.DateTimeField(auto_now_add=True)),
    ], options={'ordering':['-created_at']}),
    migrations.AddConstraint(model_name='savedattachment', constraint=models.UniqueConstraint(fields=('owner_sub','sha256'), name='chat_saved_attachment_owner_hash_uniq')),
    ]
