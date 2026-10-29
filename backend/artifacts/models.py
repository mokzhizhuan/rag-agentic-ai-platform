from django.db import models
from .jobs import GenerationJob, GenerationJobInput

class GeneratedArtifact(models.Model):
    owner_sub = models.CharField(max_length=120, db_index=True)
    conversation = models.ForeignKey('chat.Conversation', null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name='generated_artifacts')
    prompt = models.TextField(max_length=2500)
    filename = models.CharField(max_length=180)
    format = models.CharField(max_length=12)
    provider = models.CharField(max_length=24)
    content = models.FileField(upload_to='artifacts_private/%Y/%m/')
    byte_size = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

class CharacterProfile(models.Model):
    owner_sub = models.CharField(max_length=120, db_index=True)
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=1800, blank=True)
    image = models.FileField(upload_to='character_anchors_private/%Y/%m/')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
