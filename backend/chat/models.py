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
