"""Queued artifact jobs. Must run with a separate `generation_worker` process."""
from django.db import models


class GenerationJob(models.Model):
    owner_sub = models.CharField(max_length=120, db_index=True)
    status = models.CharField(max_length=16, default='queued', db_index=True)
    stage = models.CharField(max_length=140, default='Queued')
    percent = models.PositiveSmallIntegerField(default=0)
    prompt = models.TextField(max_length=2500)
    provider = models.CharField(max_length=24)
    output_format = models.CharField(max_length=24)
    parameters = models.JSONField(default=dict)
    artifact_id = models.PositiveIntegerField(null=True, blank=True)
    error = models.TextField(blank=True)
    cancel_requested = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']


class GenerationJobInput(models.Model):
    job = models.ForeignKey(GenerationJob, related_name='uploads', on_delete=models.CASCADE)
    filename = models.CharField(max_length=240)
    file = models.FileField(upload_to='job_inputs_private/%Y/%m/')
