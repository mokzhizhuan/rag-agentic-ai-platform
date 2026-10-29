from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('chat', '0004_conversation_ai_memory')]

    operations = [
        migrations.CreateModel(
            name='MemoryPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('owner_sub', models.CharField(max_length=120, unique=True)),
                ('mode', models.CharField(max_length=8, default='manual', choices=[('manual','Manual'),('auto','Auto')])),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
