from django.db import models
from pgvector.django import VectorField

class KnowledgeDocument(models.Model):
    owner_sub = models.CharField(max_length=120, db_index=True)
    filename = models.CharField(max_length=255)
    file = models.FileField(upload_to='knowledge/%Y/%m/%d/')
    byte_size = models.PositiveIntegerField()
    status = models.CharField(max_length=20, default='processing', db_index=True)
    error = models.TextField(blank=True)
    chunk_count = models.PositiveIntegerField(default=0)
    embedding_provider = models.CharField(max_length=20, blank=True)
    embedding_model = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class KnowledgeChunk(models.Model):
    document = models.ForeignKey(KnowledgeDocument, related_name='chunks', on_delete=models.CASCADE)
    index = models.PositiveIntegerField()
    page = models.PositiveIntegerField(null=True, blank=True)
    text = models.TextField()
    embedding = VectorField()  # variable dimensions: provider models may differ
    class Meta:
        constraints = [models.UniqueConstraint(fields=['document','index'], name='unique_document_chunk')]
