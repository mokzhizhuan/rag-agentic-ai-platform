"""Authenticated, opt-in ZIP validation: static checks only, no extraction/execution."""
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import GeneratedArtifact
from .project_validation import inspect_zip_bytes, markdown_report, MAX_ZIP_SIZE


@api_view(['POST', 'GET'])
@permission_classes([IsAuthenticated])
def validate_zip_artifact(request, pk):
    artifact = get_object_or_404(GeneratedArtifact, pk=pk, owner_sub=request.user.sub)
    if artifact.format != 'zip' and not artifact.filename.lower().endswith('.zip'):
        return Response({'detail': 'Only ZIP projects can be validated.'}, status=400)
    if artifact.byte_size > MAX_ZIP_SIZE:
        return Response({'detail': 'ZIP exceeds 12 MB validation limit.'}, status=413)
    try:
        with artifact.content.open('rb') as fh:
            # Enforce a strict byte cap even if stored metadata is inaccurate.
            blob = fh.read(MAX_ZIP_SIZE + 1)
        if len(blob) > MAX_ZIP_SIZE:
            return Response({'detail': 'ZIP exceeds 12 MB validation limit.'}, status=413)
        report = inspect_zip_bytes(blob)
    except (ValueError, OSError) as exc:
        return Response({'detail': str(exc)[:240]}, status=400)
    if request.method == 'GET':
        response = HttpResponse(markdown_report(report), content_type='text/markdown; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="project-{pk}.validation.md"'
        response['Cache-Control'] = 'private, no-store'
        return response
    response = Response({'artifact_id': artifact.pk, 'filename': artifact.filename, 'report': report})
    response['Cache-Control'] = 'private, no-store'
    return response
