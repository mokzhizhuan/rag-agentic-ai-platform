"""Owner-scoped reusable character anchor images and reference prompt rules."""
import io
from PIL import Image, ImageOps, UnidentifiedImageError
from django.core.files.base import ContentFile
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import CharacterProfile

ROLES = {'identity', 'style', 'composition', 'scene'}
ROLE_PROMPTS = {
 'identity': 'The reference is a CHARACTER IDENTITY ANCHOR. Preserve the recognizable facial structure, eye design and color, hairstyle and hair color, outfit, accessories, proportions and distinguishing features of the original character. Do not reinterpret or redesign the character. Change only requested pose, setting, lighting and camera framing.',
 'style': 'Use the uploaded reference for visual style, technique, palette and rendering qualities only. Do not copy its characters or scene unless the user explicitly requests them.',
 'composition': 'Use the uploaded reference for framing, camera angle, placement and composition only. Respect the requested subject identity separately.',
 'scene': 'Use the uploaded reference for environment, atmosphere, architecture and background, without treating people in it as the character identity.'
}
LOCK_PROMPT = 'IDENTITY CONSISTENCY ON: Treat the primary character reference as the source of truth. Retain the same face, silhouette, hair, costume, colors, accessories and distinguishing features between generations. Do not create a look-alike, substitute a new character, or change the outfit unless explicitly asked.'

def _normalized_png(data):
    try:
        with Image.open(io.BytesIO(data)) as src:
            if src.format not in {'JPEG','PNG','WEBP'} or src.width*src.height > 25_000_000:
                raise ValueError('Unsupported image encoding or dimensions.')
            img = ImageOps.exif_transpose(src)
            img.thumbnail((2048,2048))
            buf=io.BytesIO(); img.convert('RGBA').save(buf,'PNG'); return buf.getvalue()
    except (OSError,UnidentifiedImageError,ValueError) as exc:
        raise ValueError('Character anchor must be a valid PNG, JPG or WebP image.') from exc

def serialize(p):
    return {'id':p.id,'name':p.name,'description':p.description,'created_at':p.created_at.isoformat(), 'has_image':bool(p.image)}

@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
def character_profiles(request):
    owner=request.user.sub
    if request.method=='GET':
        return Response({'profiles':[serialize(x) for x in CharacterProfile.objects.filter(owner_sub=owner)[:100]]})
    name=str(request.data.get('name','')).strip()[:100]
    description=str(request.data.get('description','')).strip()[:1800]
    upload=request.FILES.get('image')
    if not name or not upload:
        return Response({'detail':'A character name and reference image are required.'},status=400)
    if upload.size > 8*1024*1024:
        return Response({'detail':'Character reference exceeds 8 MB.'},status=400)
    try:
        png=_normalized_png(upload.read(8*1024*1024+1))
    except ValueError as exc:
        return Response({'detail':str(exc)},status=400)
    p=CharacterProfile(owner_sub=owner,name=name,description=description)
    p.image.save('anchor.png',ContentFile(png),save=True)
    return Response({'profile':serialize(p)},status=201)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def character_profile_detail(request,pk):
    p=get_object_or_404(CharacterProfile,pk=pk,owner_sub=request.user.sub)
    p.image.delete(save=False)
    p.delete()
    return Response(status=204)
