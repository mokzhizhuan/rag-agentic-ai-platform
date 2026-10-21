from django.db import migrations, models
import django.db.models.deletion
from pgvector.django import VectorField

class Migration(migrations.Migration):
    initial=True
    dependencies=[]
    operations=[
        migrations.RunSQL('CREATE EXTENSION IF NOT EXISTS vector',reverse_sql=migrations.RunSQL.noop),
        migrations.CreateModel(name='KnowledgeDocument',fields=[
            ('id',models.BigAutoField(primary_key=True,serialize=False)),
            ('owner_sub',models.CharField(db_index=True,max_length=120)),
            ('filename',models.CharField(max_length=255)),
            ('file',models.FileField(upload_to='knowledge/%Y/%m/%d/')),
            ('byte_size',models.PositiveIntegerField()),
            ('status',models.CharField(db_index=True,default='processing',max_length=20)),
            ('error',models.TextField(blank=True)),
            ('chunk_count',models.PositiveIntegerField(default=0)),
            ('embedding_provider',models.CharField(blank=True,max_length=20)),
            ('embedding_model',models.CharField(blank=True,max_length=100)),
            ('created_at',models.DateTimeField(auto_now_add=True)),
        ]),
        migrations.CreateModel(name='KnowledgeChunk',fields=[
            ('id',models.BigAutoField(primary_key=True,serialize=False)),
            ('index',models.PositiveIntegerField()),
            ('page',models.PositiveIntegerField(blank=True,null=True)),
            ('text',models.TextField()),
            ('embedding',VectorField()),
            ('document',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='chunks',to='knowledge.knowledgedocument')),
        ]),
        migrations.AddConstraint(model_name='knowledgechunk',constraint=models.UniqueConstraint(fields=('document','index'),name='unique_document_chunk')),
    ]
