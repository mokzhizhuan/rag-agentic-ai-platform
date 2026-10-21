import os
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    return Response({'status': 'ok', 'service': 'rag-django-api'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    return Response({'sub': request.user.sub, 'username': request.user.username,
                     'email': request.user.email, 'roles': request.user.roles})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def provider_info(request):
    provider = os.getenv('AI_PROVIDER', 'ollama').lower()
    if provider not in ('ollama', 'openai'):
        return Response({'error': 'Invalid AI_PROVIDER configuration'}, status=500)
    model = os.getenv('OLLAMA_CHAT_MODEL', 'llama3.2') if provider == 'ollama' else os.getenv('OPENAI_CHAT_MODEL', 'gpt-4.1-mini')
    return Response({'provider': provider, 'model': model, 'status': 'configured_not_connected'})
