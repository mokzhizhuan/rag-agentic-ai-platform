"""Phase 7.7 job API; uses the existing artifact generator unchanged."""
import os
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .generator import FORMAT_EXT
# Phase 7.7 queued generation (separate worker; existing synchronous API kept intact)
from django.core.files.base import ContentFile
from django.db import transaction
from .jobs import GenerationJob, GenerationJobInput

def _job_record(job):
    return {'id': job.id, 'status': job.status, 'stage': job.stage,
            'percent': job.percent if job.status in ('queued','completed','failed','cancelled') else None,
            'artifact_id': job.artifact_id, 'error': job.error,
            'cancel_requested': job.cancel_requested,
            'created_at': job.created_at.isoformat(),
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'finished_at': job.finished_at.isoformat() if job.finished_at else None}

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def generation_jobs(request):
    owner = request.user.sub
    if request.method == 'GET':
        return Response({'jobs': [_job_record(x) for x in GenerationJob.objects.filter(owner_sub=owner)[:30]]})
    prompt = str(request.data.get('prompt','')).strip()
    provider = request.data.get('provider','')
    output_format = request.data.get('format','auto')
    if not 5 <= len(prompt) <= 2500 or provider not in ('openai','ollama') or output_format not in set(FORMAT_EXT)|{'auto','video','video_clip','video_reel'}:
        return Response({'detail':'Invalid prompt, provider or format.'},status=400)
    uploaded = request.FILES.getlist('files')
    if len(uploaded)>3 or any(f.size>20*1024*1024 for f in uploaded) or sum(f.size for f in uploaded)>45*1024*1024:
        return Response({'detail':'Attachments exceed the 3-file / 20 MiB each / 45 MiB total limit.'},status=413)
    params = {}
    for field in ('reference_handling','reference_controls','character_lock','character_id','duration','conversation_id'):
        value = request.data.get(field)
        if value is not None:
            params[field] = str(value)[:12000]
    # Record and inputs persist across refresh/restarts. Keep file bytes in the private MEDIA_ROOT volume.
    with transaction.atomic():
        job = GenerationJob.objects.create(owner_sub=owner,prompt=prompt,provider=provider,
                                           output_format=output_format,parameters=params)
        for f in uploaded:
            safe_name = os.path.basename(f.name.replace('\\','/'))[:240]
            inp = GenerationJobInput(job=job, filename=safe_name)
            inp.file.save(safe_name, f, save=True)
    return Response({'job': _job_record(job)},status=202)

@api_view(['GET','DELETE'])
@permission_classes([IsAuthenticated])
def generation_job_detail(request, pk):
    job = get_object_or_404(GenerationJob, pk=pk, owner_sub=request.user.sub)
    if request.method == 'DELETE':
        if job.status in ('queued','running'):
            job.cancel_requested=True
            if job.status == 'queued':
                job.status='cancelled';job.stage='Cancelled';job.finished_at=timezone.now()
            job.save(update_fields=['cancel_requested','status','stage','finished_at'])
            if job.status == 'cancelled':
                for upload in list(job.uploads.all()):
                    upload.file.delete(save=False)
                    upload.delete()
        return Response({'job':_job_record(job)})
    return Response({'job':_job_record(job)})


# PHASE8_4_FAILED_JOB_CLEANUP_V1: cleanup is distinct from cancellation.
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_failed_generation_job(request, pk):
    """Remove only the current user's failed job, never a live or successful job."""
    with transaction.atomic():
        job = get_object_or_404(
            GenerationJob.objects.select_for_update(), pk=pk, owner_sub=request.user.sub
        )
        if job.status != 'failed' or job.artifact_id is not None:
            return Response({'detail': 'Only failed jobs without an artifact can be removed.'}, status=409)
        paths = [upload.file.name for upload in job.uploads.all() if upload.file.name]
        storage = GenerationJobInput._meta.get_field('file').storage
        job.delete()
        # Delete private uploaded-input files only after DB commit succeeds.
        transaction.on_commit(lambda: _delete_job_uploads(storage, paths))
    return Response({'deleted': 1, 'job_id': pk})


def _delete_job_uploads(storage, paths):
    for path in paths:
        try:
            storage.delete(path)
        except Exception:
            import logging
            logging.getLogger(__name__).exception('Unable to clean up failed-job input %s', path)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_all_failed_generation_jobs(request):
    """Remove all failed jobs owned by this account; no dependency on a 30-job listing."""
    with transaction.atomic():
        queryset = GenerationJob.objects.select_for_update().filter(
            owner_sub=request.user.sub, status='failed', artifact_id__isnull=True
        )
        job_ids = list(queryset.values_list('id', flat=True))
        uploads = GenerationJobInput.objects.filter(job_id__in=job_ids)
        paths = [upload.file.name for upload in uploads if upload.file.name]
        storage = GenerationJobInput._meta.get_field('file').storage
        GenerationJob.objects.filter(id__in=job_ids).delete()
        transaction.on_commit(lambda: _delete_job_uploads(storage, paths))
    return Response({'deleted': len(job_ids)})
