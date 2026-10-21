from django.db import migrations, models
import django.db.models.deletion
class Migration(migrations.Migration):
    initial=True
    dependencies=[]
    operations=[
        migrations.CreateModel(name='Conversation',fields=[
            ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
            ('owner_sub',models.CharField(db_index=True,max_length=120)),
            ('title',models.CharField(max_length=160)),
            ('created_at',models.DateTimeField(auto_now_add=True)),
            ('updated_at',models.DateTimeField(auto_now=True)),
        ]),
        migrations.CreateModel(name='ChatMessage',fields=[
            ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
            ('role',models.CharField(choices=[('user','User'),('assistant','Assistant')],max_length=12)),
            ('content',models.TextField()),
            ('sources',models.JSONField(blank=True,default=list)),
            ('model',models.CharField(blank=True,max_length=120)),
            ('created_at',models.DateTimeField(auto_now_add=True)),
            ('conversation',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='messages',to='chat.conversation')),
        ]),
    ]
