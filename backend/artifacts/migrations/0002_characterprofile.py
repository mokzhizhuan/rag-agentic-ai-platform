from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('artifacts', '0001_initial')]
    operations = [migrations.CreateModel(name='CharacterProfile', fields=[
        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
        ('owner_sub', models.CharField(db_index=True, max_length=120)),
        ('name', models.CharField(max_length=100)),
        ('description', models.TextField(blank=True, max_length=1800)),
        ('image', models.FileField(upload_to='character_anchors_private/%Y/%m/')),
        ('created_at', models.DateTimeField(auto_now_add=True)),
    ], options={'ordering':['-created_at']})]
