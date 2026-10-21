import os
import requests
from rest_framework.exceptions import ValidationError

# Embedding provider can be chosen independently of the future chat model.
def config():
    provider = os.getenv('EMBEDDING_PROVIDER', 'ollama').strip().lower()
    if provider == 'ollama':
        return provider, os.getenv('OLLAMA_EMBED_MODEL', 'nomic-embed-text')
    if provider == 'openai':
        return provider, os.getenv('OPENAI_EMBED_MODEL', 'text-embedding-3-small')
    raise ValidationError({'embedding': 'Invalid EMBEDDING_PROVIDER'})

def embed(texts):
    if not texts:
        return []
    provider, model = config()
    try:
        if provider == 'ollama':
            base = os.getenv('OLLAMA_BASE_URL','http://host.docker.internal:11434').rstrip('/')
            res = requests.post(base+'/api/embed', json={'model':model, 'input': texts}, timeout=180)
            res.raise_for_status()
            vectors = res.json()['embeddings']
        else:
            key = os.getenv('OPENAI_API_KEY', '')
            if not key: raise ValidationError({'embedding': 'OPENAI_API_KEY is not configured'})
            res = requests.post('https://api.openai.com/v1/embeddings',
                headers={'Authorization':f'Bearer {key}'},
                json={'model':model,'input':texts}, timeout=180)
            res.raise_for_status()
            result = res.json()['data']
            vectors = [item['embedding'] for item in sorted(result,key=lambda x:x['index'])]
    except (requests.RequestException, KeyError, TypeError, ValueError) as e:
        raise ValidationError({'embedding': 'Embedding request failed; check model availability and backend logs'}) from e
    if len(vectors) != len(texts) or any(not v for v in vectors):
        raise ValidationError({'embedding':'Embedding service returned unexpected vector count'})
    return vectors
