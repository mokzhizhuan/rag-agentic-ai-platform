from django.db import models
class Conversation(models.Model):
    owner_sub = models.CharField(max_length=120, db_index=True)
    title = models.CharField(max_length=160)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class ChatMessage(models.Model):
    conversation = models.ForeignKey(Conversation,on_delete=models.CASCADE,related_name='messages')
    role = models.CharField(max_length=12,choices=[('user','User'),('assistant','Assistant')])
    content = models.TextField()
    sources = models.JSONField(default=list,blank=True)
    model = models.CharField(max_length=120,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=['id']

# Phase 6: original bytes in persistent private MEDIA_ROOT, metadata in PostgreSQL.
class SavedAttachment(models.Model):
    owner_sub = models.CharField(max_length=120, db_index=True)
    filename = models.CharField(max_length=150)
    sha256 = models.CharField(max_length=64)
    byte_size = models.PositiveIntegerField()
    content = models.FileField(upload_to='chat_private/')
    extracted_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['owner_sub', 'sha256'], name='chat_saved_attachment_owner_hash_uniq')]
        ordering = ['-created_at']


class ConversationSummary(models.Model):
    conversation = models.OneToOneField(Conversation, related_name='memory_summary', on_delete=models.CASCADE)
    content = models.TextField(default='')
    through_message_id = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)


class UserMemory(models.Model):
    owner_sub = models.CharField(max_length=120, db_index=True)
    content = models.TextField(max_length=1200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class MemoryPreference(models.Model):
    """A private, persisted per-user choice; defaults to manual (opt-in)."""
    owner_sub = models.CharField(max_length=120, unique=True)
    mode = models.CharField(max_length=8, default='manual', choices=[('manual','Manual'),('auto','Auto')])
    updated_at = models.DateTimeField(auto_now=True)

