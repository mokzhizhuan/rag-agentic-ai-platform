import logging
from pathlib import Path
from django.db.models import Q
from pgvector.django import CosineDistance
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import KnowledgeDocument, KnowledgeChunk
from .embeddings import embed, config
from .ingest import ingest_document

log=logging.getLogger(__name__)
ALLOWED={'.pdf','.docx','.txt','.md'}
MAX_UPLOAD=10*1024*1024

def serialize(d):
    return {'id':d.pk,'filename':d.filename,'byte_size':d.byte_size,'status':d.status,
            'error':d.error,'chunk_count':d.chunk_count,'embedding_provider':d.embedding_provider,
            'embedding_model':d.embedding_model,'created_at':d.created_at.isoformat()}


# Upload preflight checks run BEFORE a document row or stored file is created.
# Files from different users are intentionally not compared.
def _validate_uploaded_binary(filename, binary):
    from io import BytesIO
    from zipfile import ZipFile, BadZipFile

    extension = Path(filename).suffix.lower()
    if not binary:
        return 'The uploaded file is empty.'
    if extension == '.pdf':
        if not binary.startswith(b'%PDF-'):
            return 'Invalid PDF: the file is not a PDF document.'
        try:
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(binary), strict=False)
            if not reader.pages:
                return 'Invalid PDF: no pages were found.'
            # Check that the PDF page tree is readable before storing the file.
            for page in reader.pages:
                _ = page.mediabox
        except Exception:
            return 'Invalid or damaged PDF document.'
    elif extension == '.docx':
        if not binary.startswith(b'PK\x03\x04'):
            return 'Invalid DOCX: the file is not a Word document.'
        try:
            with ZipFile(BytesIO(binary)) as archive:
                names = set(archive.namelist())
                if '[Content_Types].xml' not in names or 'word/document.xml' not in names:
                    return 'Invalid DOCX: required Word document parts are missing.'
                # Avoid feeding obviously malformed or extremely inflated archives to
                # python-docx. Valid Word files may include embedded media.
                if len(names) > 2000 or sum(x.file_size for x in archive.infolist()) > 100 * 1024 * 1024:
                    return 'Invalid DOCX: archive exceeds document safety limits.'
                if archive.testzip() is not None:
                    return 'Invalid DOCX: archive contains corrupt data.'
            from docx import Document
            Document(BytesIO(binary))
        except Exception:
            return 'Invalid or damaged DOCX document.'
    return None


def _matching_document(owner_sub, binary):
    """Find an existing identical, readable user document (no schema migration).

    Compare SHA-256 digests, not names. Read existing storage in bounded chunks;
    avoid exposing any other user's documents. The input is capped at 10 MB.
    """
    import hashlib
    digest = hashlib.sha256(binary).digest()
    candidates = KnowledgeDocument.objects.filter(
        owner_sub=owner_sub, byte_size=len(binary), status='ready'
    ).only('id', 'file', 'filename').order_by('id')
    for existing in candidates.iterator():
        if not existing.file:
            continue
        try:
            stored_hash = hashlib.sha256()
            with existing.file.open('rb') as stored:
                for chunk in iter(lambda: stored.read(65536), b''):
                    stored_hash.update(chunk)
            if stored_hash.digest() == digest:
                return existing
        except (OSError, ValueError):
            # An unavailable old storage object cannot be compared; don't prevent
            # the new upload simply because an old file has gone missing.
            log.warning('Could not check existing document %s for duplicate upload', existing.pk)
    return None

@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
def documents(request):
    sub=request.user.sub
    if request.method=='GET':
        qs=KnowledgeDocument.objects.filter(owner_sub=sub).order_by('-created_at')
        return Response({'documents':[serialize(d) for d in qs[:100]]})
    upload=request.FILES.get('file')
    if not upload: return Response({'detail':'Choose a file'},status=400)
    filename=Path(upload.name).name[:255]
    if Path(filename).suffix.lower() not in ALLOWED:
        return Response({'detail':'Allowed: PDF, DOCX, TXT, MD'},status=400)
    if upload.size>MAX_UPLOAD:
        return Response({'detail':'10 MB upload limit'},status=400)
    binary=upload.read(MAX_UPLOAD+1)
    if len(binary)>MAX_UPLOAD:return Response({'detail':'10 MB upload limit'},status=400)
    invalid = _validate_uploaded_binary(filename, binary)
    if invalid:
        return Response({'detail': invalid}, status=status.HTTP_400_BAD_REQUEST)
    existing = _matching_document(sub, binary)
    if existing is not None:
        return Response({
            'detail': 'This document already exists in your Knowledge Base.',
            'existing_document_id': existing.pk,
            'existing_filename': existing.filename,
        }, status=status.HTTP_409_CONFLICT)
    doc=KnowledgeDocument(owner_sub=sub, filename=filename, byte_size=len(binary))
    from django.core.files.base import ContentFile
    doc.file.save(filename,ContentFile(binary),save=True)
    try:
        ingest_document(doc,binary)
    except Exception as exc:
        log.exception('Knowledge ingestion failed for document %s',doc.pk)
        doc.chunks.all().delete()
        doc.status='failed';doc.error=str(exc) if isinstance(exc,ValueError) else 'Indexing failed; check backend logs and embedding model configuration'
        doc.chunk_count=0;doc.save(update_fields=['status','error','chunk_count'])
    return Response(serialize(doc),status=status.HTTP_201_CREATED)

@api_view(['GET','DELETE'])
@permission_classes([IsAuthenticated])
def document_detail(request,pk):
    doc=KnowledgeDocument.objects.filter(pk=pk,owner_sub=request.user.sub).first()
    if doc is None: return Response({'detail':'Not found'},status=404)
    if request.method=='GET': return Response(serialize(doc))
    storage=doc.file.storage; name=doc.file.name
    doc.delete()
    if name:storage.delete(name)
    return Response(status=204)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def semantic_search(request):
    query=request.data.get('query','')
    if not isinstance(query,str) or not (2<=len(query.strip())<=1000):
        return Response({'detail':'Query must have 2-1000 characters'},status=400)
    provider,model=config()
    base=KnowledgeChunk.objects.filter(document__owner_sub=request.user.sub,
        document__status='ready',document__embedding_provider=provider,
        document__embedding_model=model)
    if not base.exists():return Response({'results':[],'model':model})
    from rest_framework.exceptions import ValidationError
    try: vector=embed([query.strip()])[0]
    except ValidationError as exc:return Response(exc.detail,status=503)
    # Models with different vector lengths cannot be compared: only same model above.
    matches=base.annotate(distance=CosineDistance('embedding',vector)).order_by('distance','pk')[:5]
    return Response({'model':model,'results':[
        {'document_id':c.document_id,'filename':c.document.filename,'page':c.page,
         'text':c.text,'similarity':round(1-float(c.distance),4)} for c in matches]})
