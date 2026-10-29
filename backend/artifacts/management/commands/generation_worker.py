"""DB-backed job worker. Run separately from the Django web server.

A single worker is appropriate for first deployment. Do NOT use multiple workers
without distributed job leases and idempotency controls.
"""
import logging
import os
import time
from types import SimpleNamespace
from django.core.management.base import BaseCommand
from django.db import close_old_connections, transaction
from django.utils import timezone
from django.test.client import RequestFactory
from rest_framework.test import APIRequestFactory, force_authenticate
from artifacts.jobs import GenerationJob
from artifacts.progress import bind_progress, reset_progress  # PHASE77_SECTION_PROGRESS_V1
from artifacts.views import artifacts as create_artifact_endpoint

log = logging.getLogger(__name__)


def _cleanup(job):
    for attached in list(job.uploads.all()):
        attached.file.delete(save=False)
        attached.delete()


def _update(job_id, **values):
    GenerationJob.objects.filter(pk=job_id).update(**values)


def process_job(job_id):
    job = GenerationJob.objects.get(pk=job_id)
    if job.cancel_requested:
        _update(job_id, status='cancelled',stage='Cancelled',finished_at=timezone.now());_cleanup(job);return
    # Real measured phase: validation/persistence completes only AFTER synchronous generator returns.
    _update(job_id,status='running',stage='Generating with '+job.provider+' (progress unavailable from model)',percent=10)
    try:
        params={'prompt':job.prompt,'provider':job.provider,'format':job.output_format,**job.parameters}
        from django.core.files.uploadedfile import SimpleUploadedFile
        files=[]
        for attachment in job.uploads.all():
            with attachment.file.open('rb') as handle:
                content=handle.read(20*1024*1024+1)
            if len(content)>20*1024*1024:
                raise ValueError('Uploaded reference too large')
            files.append(SimpleUploadedFile(attachment.filename,content))
        if files:
            params['files']=files
        factory=APIRequestFactory()
        req=factory.post('/api/artifacts/', data=params, format='multipart')
        identity=SimpleNamespace(sub=job.owner_sub,is_authenticated=True,is_active=True)
        force_authenticate(req,user=identity)
        def on_progress(stage, percent):
            # Save actual milestones, never mark complete until artifact persistence.
            GenerationJob.objects.filter(pk=job_id, status='running').update(
                stage=stage, percent=percent
            )
            log.info('Job #%s [%s%%] %s', job_id, percent, stage)
        progress_token = bind_progress(on_progress)
        try:
            result=create_artifact_endpoint(req)
        finally:
            reset_progress(progress_token)
        # Existing authenticated API owns all generation, formats, references, and save logic.
        if result.status_code != 201:
            message=str(result.data.get('detail', result.data)) if hasattr(result,'data') else 'Generation error'
            _update(job_id,status='failed',stage='Failed',error=message[:4000],finished_at=timezone.now());return
        artifact_id=result.data['artifact']['id']
        _update(job_id,status='completed',stage='Completed — file saved',percent=100,artifact_id=artifact_id,finished_at=timezone.now())
    except Exception as exc:
        log.exception('Generation job %s failed',job_id)
        _update(job_id,status='failed',stage='Failed',error=(str(exc) or type(exc).__name__)[:4000],finished_at=timezone.now())
    finally:
        job.refresh_from_db()
        if job.cancel_requested and job.status == 'completed':
            # Generation cannot interrupt in-flight provider requests.
            # A completed file is retained; cancellation is best effort.
            pass
        _cleanup(job)


"""DB-backed job worker. Run separately from the Django web server.

A single worker is appropriate for first deployment. Do NOT use multiple workers
without distributed job leases and idempotency controls.
"""
import logging
import os
import time
from types import SimpleNamespace
from django.core.management.base import BaseCommand
from django.db import close_old_connections, transaction
from django.utils import timezone
from django.test.client import RequestFactory
from rest_framework.test import APIRequestFactory, force_authenticate
from artifacts.jobs import GenerationJob
from artifacts.views import artifacts as create_artifact_endpoint

log = logging.getLogger(__name__)


def _cleanup(job):
    for attached in list(job.uploads.all()):
        attached.file.delete(save=False)
        attached.delete()


def _update(job_id, **values):
    GenerationJob.objects.filter(pk=job_id).update(**values)


def process_job(job_id):
    job = GenerationJob.objects.get(pk=job_id)
    if job.cancel_requested:
        _update(job_id, status='cancelled',stage='Cancelled',finished_at=timezone.now());_cleanup(job);return
    # Real measured phase: validation/persistence completes only AFTER synchronous generator returns.
    _update(
        job_id,
        stage=f"Generating with {job.provider}...",
        percent=10,
    )
    try:
        params={'prompt':job.prompt,'provider':job.provider,'format':job.output_format,**job.parameters}
        from django.core.files.uploadedfile import SimpleUploadedFile
        files=[]
        for attachment in job.uploads.all():
            with attachment.file.open('rb') as handle:
                content=handle.read(20*1024*1024+1)
            if len(content)>20*1024*1024:
                raise ValueError('Uploaded reference too large')
            files.append(SimpleUploadedFile(attachment.filename,content))
        if files:
            params['files']=files
        factory=APIRequestFactory()
        req=factory.post('/api/artifacts/', data=params, format='multipart')
        identity=SimpleNamespace(sub=job.owner_sub,is_authenticated=True,is_active=True)
        force_authenticate(req,user=identity)
        def on_progress(stage, percent):
            # Save actual milestones, never mark complete until artifact persistence.
            GenerationJob.objects.filter(pk=job_id, status='running').update(
                stage=stage, percent=percent
            )
            log.info('Job #%s [%s%%] %s', job_id, percent, stage)
        progress_token = bind_progress(on_progress)
        try:
            result=create_artifact_endpoint(req)
        finally:
            reset_progress(progress_token)
        # Existing authenticated API owns all generation, formats, references, and save logic.
        if result.status_code != 201:
            message=str(result.data.get('detail', result.data)) if hasattr(result,'data') else 'Generation error'
            _update(job_id,status='failed',stage='Failed',error=message[:4000],finished_at=timezone.now());return
        artifact_id=result.data['artifact']['id']
        _update(job_id,status='completed',stage='Completed — file saved',percent=100,artifact_id=artifact_id,finished_at=timezone.now())
    except Exception as exc:
        log.exception('Generation job %s failed',job_id)
        _update(job_id,status='failed',stage='Failed',error=(str(exc) or type(exc).__name__)[:4000],finished_at=timezone.now())
    finally:
        job.refresh_from_db()
        if job.cancel_requested and job.status == 'completed':
            # Generation cannot interrupt in-flight provider requests.
            # A completed file is retained; cancellation is best effort.
            pass
        _cleanup(job)


class Command(BaseCommand):
    help='Run a single, DB-backed artifact generation worker (separate service)'

    def handle(self,*args,**kwargs):
        self.stdout.write('Artifact generation worker started')
        # After an unclean container stop, don't leave jobs claiming to run forever.
        # Their state is uncertain; do not retry automatically (provider may have billed).
        GenerationJob.objects.filter(status='running').update(status='failed', stage='Interrupted by worker restart',error='Worker restarted before this generation completed.',finished_at=timezone.now())
        while True:
            close_old_connections()
            with transaction.atomic():
                job=GenerationJob.objects.select_for_update(skip_locked=True).filter(status='queued',cancel_requested=False).order_by('id').first()
                job_id=job.id if job else None
                if job:
                    job.status='running';job.stage='Preparing request';job.percent=5;job.started_at=timezone.now();job.save(update_fields=['status','stage','percent','started_at'])
            if job_id is not None:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[Worker] Picked up job #{job_id}"
                    )
                )
            if job_id is None:
                time.sleep(2)
                continue
            process_job(job_id)
            log.warning(
                "Job #%s: starting artifact generation",
                job_id,
            )
