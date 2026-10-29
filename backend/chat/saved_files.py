"""Private persistent attachment storage. No raw-file serving route is exposed."""
import hashlib
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from .attachments import extract_chat_files, AttachmentError, MAX_FILES
from .models import SavedAttachment

def serialize_saved(item):
    return {'id': item.pk, 'filename':item.filename, 'byte_size':item.byte_size, 'created_at':item.created_at.isoformat()}

def save_uploaded(owner_sub, uploaded_files):
    if not uploaded_files:
        return []
    extracted = extract_chat_files(uploaded_files)
    persisted = []
    for upload, entry in zip(uploaded_files, extracted):
        upload.seek(0)
        payload = upload.read()
        digest = hashlib.sha256(payload).hexdigest()
        existing = SavedAttachment.objects.filter(owner_sub=owner_sub, sha256=digest).first()
        if existing:
            persisted.append(existing)
            continue
        item = SavedAttachment(owner_sub=owner_sub, sha256=digest, filename=entry['filename'],
                               byte_size=len(payload), extracted_text=entry['text'])
        # Uses Django's configured private MEDIA_ROOT, mounted as a persistent Docker volume.
        item.content.save(digest + '_' + entry['filename'], ContentFile(payload), save=False)
        try:
            with transaction.atomic():
                item.save()
        except IntegrityError:
            item.content.delete(save=False)
            item = SavedAttachment.objects.get(owner_sub=owner_sub, sha256=digest)
        persisted.append(item)
    return persisted

def as_passages(items):
    return [{'filename': a.filename, 'text': a.extracted_text, 'saved_file_id': a.pk} for a in items]
