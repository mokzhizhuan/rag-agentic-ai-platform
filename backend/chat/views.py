from django.db import transaction
from rest_framework.renderers import BaseRenderer, JSONRenderer

class EventStreamRenderer(BaseRenderer):
    media_type = 'text/event-stream'
    format = 'event-stream'
    charset = 'utf-8'
    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data

from django.shortcuts import get_object_or_404
from pgvector.django import CosineDistance
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from knowledge.models import KnowledgeChunk
from knowledge.embeddings import embed,config
from .models import Conversation,ChatMessage
from .providers import generate,chat_settings,ChatProviderError


def serialize_conversation(c):
    return {'id':c.pk,'title':c.title,'created_at':c.created_at.isoformat(),'updated_at':c.updated_at.isoformat()}
def serialize_message(m):
    return {'id':m.pk,'role':m.role,'content':m.content,'sources':m.sources,'model':m.model,'created_at':m.created_at.isoformat()}

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conversations(request):
    items=Conversation.objects.filter(owner_sub=request.user.sub).order_by('-updated_at')[:100]
    return Response({'conversations':[serialize_conversation(c) for c in items]})

@api_view(['GET','DELETE'])
@permission_classes([IsAuthenticated])
def conversation_detail(request,pk):
    c=get_object_or_404(Conversation,pk=pk,owner_sub=request.user.sub)
    if request.method=='DELETE':
        c.delete()
        return Response(status=204)
    return Response({'conversation':serialize_conversation(c),'messages':[serialize_message(m) for m in c.messages.all()[:200]]})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ask(request):
    question=request.data.get('question','')
    if not isinstance(question,str) or not (2 <= len(question.strip()) <= 1500):
        return Response({'detail':'Question must contain 2–1500 characters'},status=400)
    question=question.strip()
    cid=request.data.get('conversation_id')
    if cid is not None and (isinstance(cid,bool) or not isinstance(cid,int)):
        return Response({'detail':'conversation_id must be an integer'},status=400)
    c=None
    if cid is not None:
        c=get_object_or_404(Conversation,pk=cid,owner_sub=request.user.sub)
    try:
        ep,em=config()
        cp,cm=chat_settings()
        base=KnowledgeChunk.objects.filter(document__owner_sub=request.user.sub,
            document__status='ready',document__embedding_provider=ep,document__embedding_model=em)
        if not base.exists():
            return Response({'detail':'No indexed documents for the configured embedding model. Upload a document before chatting.'},status=400)
        vector=embed([question])[0]
        chunks=list(base.select_related('document').annotate(distance=CosineDistance('embedding',vector)).order_by('distance','pk')[:4])
        threshold=float(__import__('os').getenv('RAG_MIN_SIMILARITY','0.15'))
        passages=[]
        for ch in chunks:
            similarity=1-float(ch.distance)
            if similarity < threshold:continue
            passages.append({'document_id':ch.document_id,'filename':ch.document.filename,
                'page':ch.page,'chunk_index':ch.index,'text':ch.text,'similarity':round(similarity,4)})
        history=list(c.messages.order_by('-id')[:6])[::-1] if c else []
        if not passages:
            answer='I could not find enough information in your uploaded documents to answer that.'
            model='retrieval-only';sources=[]
        else:
            answer,_,model=generate(question,passages,history)
            sources=[{**{k:p[k] for k in ('document_id','filename','page','chunk_index','similarity')},'excerpt':p['text'][:700]} for p in passages]
    except ChatProviderError as exc:
        return Response({'detail':str(exc)},status=503)
    except Exception as exc:
        # Embedding errors are DRF exceptions with a safe structured detail.
        from rest_framework.exceptions import APIException
        if isinstance(exc,APIException):
            return Response({'detail':exc.detail},status=503)
        raise
    # Save only after successful generation, avoiding empty turns on model failure.
    with transaction.atomic():
        if c is None:
            c=Conversation.objects.create(owner_sub=request.user.sub,title=question[:120])
        user_msg=ChatMessage.objects.create(conversation=c,role='user',content=question)
        assistant_msg=ChatMessage.objects.create(conversation=c,role='assistant',content=answer,sources=sources,model=model)
        c.save(update_fields=['updated_at'])
    return Response({'conversation':serialize_conversation(c),'user_message':serialize_message(user_msg),'assistant_message':serialize_message(assistant_msg)})


# Restricted arithmetic parser: no names, calls, attributes or arbitrary evaluation.
import ast
import operator
_CALC = {ast.Add:operator.add, ast.Sub:operator.sub, ast.Mult:operator.mul,
         ast.Div:operator.truediv, ast.Mod:operator.mod, ast.Pow:operator.pow}
def safe_calculate(expression):
    expression = expression.strip()
    if len(expression) > 80:
        raise ValueError('Expression too long')
    def visit(node, depth=0):
        if depth > 12: raise ValueError('Expression too complex')
        if isinstance(node, ast.Expression): return visit(node.body, depth+1)
        if isinstance(node, ast.Constant) and type(node.value) in (int,float):
            if abs(node.value)>1e9: raise ValueError('Number too large')
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op,(ast.USub,ast.UAdd)):
            val=visit(node.operand,depth+1)
            return -val if isinstance(node.op,ast.USub) else val
        if isinstance(node, ast.BinOp) and type(node.op) in _CALC:
            a=visit(node.left,depth+1);b=visit(node.right,depth+1)
            if isinstance(node.op,ast.Pow) and abs(b)>8: raise ValueError('Exponent too large')
            result=_CALC[type(node.op)](a,b)
            if abs(result)>1e12: raise ValueError('Result too large')
            return result
        raise ValueError('Only arithmetic expressions are allowed')
    return visit(ast.parse(expression,mode='eval'))

# Streamed alternative to ask() — original endpoint retained for compatibility.
import json
import logging
import os
from django.http import StreamingHttpResponse
from .providers import stream_generate, plan_tool, plan_auto, GENERAL_PROMPT

stream_log = logging.getLogger(__name__)

def _sse(event, payload):
    return f'event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n'

@api_view(['POST'])
@renderer_classes([EventStreamRenderer, JSONRenderer])
@permission_classes([IsAuthenticated])
def ask_stream(request):
    question = request.data.get('question', '')
    if not isinstance(question, str) or not (2 <= len(question.strip()) <= 1500):
        return Response({'detail': 'Question must contain 2–1500 characters'}, status=400)
    question = question.strip()
    mode = request.data.get('mode', 'rag')
    if mode not in ('rag', 'agent', 'auto'):
        return Response({'detail': 'Unsupported chat mode'}, status=400)
    selected_provider = request.data.get('provider', 'ollama')
    if selected_provider not in ('ollama', 'openai'):
        return Response({'detail': 'Unsupported AI provider'}, status=400)
    if selected_provider == 'openai' and not os.getenv('OPENAI_API_KEY'):
        return Response({'detail': 'OpenAI is not configured on the backend'}, status=400)
    cid = request.data.get('conversation_id')
    if cid is not None and (isinstance(cid, bool) or not isinstance(cid, int)):
        return Response({'detail': 'conversation_id must be an integer'}, status=400)

    owner_sub = request.user.sub  # Evaluate authentication BEFORE leaving DRF wrapper.
    conversation_id = None
    if cid is not None:
        conversation_id = get_object_or_404(Conversation, pk=cid, owner_sub=owner_sub).pk

    # Do not use request inside the lazy generator; it runs after the view returns.
    def events():
        try:
            chosen_tool = 'knowledge_search'
            if mode == 'auto':
                yield _sse('status', {'stage': 'routing', 'message': 'Choosing the best answer source...'})
                chosen_tool = plan_auto(question, selected_provider)
                yield _sse('tool', {'name':chosen_tool, 'status':'selected'})
            elif mode == 'rag':
                yield _sse('status', {'stage': 'searching', 'message': 'Searching knowledge base...'})
            if mode == 'agent':
                yield _sse('status', {'stage':'planning','message':'Selecting an agent tool...'})
                chosen_tool = plan_tool(question, selected_provider)
                yield _sse('tool', {'name':chosen_tool,'status':'started'})
            calc_result = None
            provider, model = chat_settings(selected_provider)
            passages = []
            if mode == 'agent' and chosen_tool == 'calculator':
                import re
                expression = re.sub(r'^\s*(calculate|compute|what is|evaluate)\s*:?\s*', '', question, flags=re.I).rstrip(' ?.')
                try:
                    calc_result = safe_calculate(expression)
                except (ValueError, SyntaxError, ZeroDivisionError, OverflowError) as exc:
                    yield _sse('error', {'detail':'Calculator accepts arithmetic expressions only (example: Calculate 12 * 7).'})
                    return
            elif chosen_tool == 'knowledge_search':
                yield _sse('status', {'stage': 'searching', 'message': 'Searching knowledge base...'})
                ep, em = config()
                provider, model = chat_settings(selected_provider)
                base = KnowledgeChunk.objects.filter(
                    document__owner_sub=owner_sub, document__status='ready',
                    document__embedding_provider=ep, document__embedding_model=em,
                )
                if not base.exists():
                    if mode == 'auto':
                        chosen_tool = 'general'
                        yield _sse('status', {'stage': 'routing', 'message': 'No indexed documents; using general AI knowledge.'})
                    else:
                        yield _sse('error', {'detail': 'No indexed documents for the configured embedding model. Upload a document first.'})
                        return
                if chosen_tool == 'knowledge_search':
                    vector = embed([question])[0]
                    chunks = list(base.select_related('document').annotate(
                        distance=CosineDistance('embedding', vector)
                    ).order_by('distance', 'pk')[:int(os.getenv('RAG_TOP_K', '2'))])
                    threshold = float(os.getenv('RAG_MIN_SIMILARITY', '0.15'))
                    passages = []
                    for ch in chunks:
                        similarity = 1 - float(ch.distance)
                        if similarity >= threshold:
                            passages.append({
                                'document_id': ch.document_id, 'filename': ch.document.filename,
                                'page': ch.page, 'chunk_index': ch.index, 'text': ch.text,
                                'similarity': round(similarity, 4),
                            })
            if mode == 'auto' and chosen_tool == 'knowledge_search' and not passages:
                chosen_tool = 'general'
                yield _sse('status', {'stage':'routing','message':'No relevant passages; answering from general AI knowledge.'})
            if mode == 'agent':
                yield _sse('tool', {'name':chosen_tool,'status':'completed'})
            sources = [{**{k: p[k] for k in ('document_id', 'filename', 'page', 'chunk_index', 'similarity')},
                        'excerpt': p['text'][:700]} for p in passages]
            yield _sse('sources', {'sources': sources})
            c = Conversation.objects.filter(pk=conversation_id, owner_sub=owner_sub).first() if conversation_id else None
            history = list(c.messages.order_by('-id')[:6])[::-1] if c else []
            answer = ''
            if calc_result is not None:
                answer = f'{calc_result:g}' if isinstance(calc_result, float) else str(calc_result)
                model = 'calculator'
                yield _sse('token', {'text':answer})
            elif passages:
                yield _sse('status', {'stage': 'generating', 'message': 'Generating answer...'})
                for token in stream_generate(question, passages, history, selected_provider):
                    answer += token
                    yield _sse('token', {'text': token})
                answer = answer.strip()
                if not answer:
                    yield _sse('error', {'detail': 'AI provider returned an empty answer'})
                    return
            elif mode == 'auto' and chosen_tool == 'general':
                yield _sse('status', {'stage':'generating','message':'Answering from model general knowledge (no web search)...'})
                for token in stream_generate(question, [], history, selected_provider, system_override=GENERAL_PROMPT):
                    answer += token
                    yield _sse('token', {'text': token})
                answer = answer.strip()
                if not answer:
                    yield _sse('error', {'detail': 'AI provider returned an empty answer'})
                    return
            else:
                answer = 'I could not find enough information in your uploaded documents to answer that.'
                model = 'retrieval-only'
                yield _sse('token', {'text': answer})
            # Save only after complete generation.
            with transaction.atomic():
                if c is None:
                    c = Conversation.objects.create(owner_sub=owner_sub, title=question[:120])
                user_msg = ChatMessage.objects.create(conversation=c, role='user', content=question)
                assistant_msg = ChatMessage.objects.create(
                    conversation=c, role='assistant', content=answer, sources=sources, model=model,
                )
                c.save(update_fields=['updated_at'])
            yield _sse('done', {
                'conversation': serialize_conversation(c),
                'user_message': serialize_message(user_msg),
                'assistant_message': serialize_message(assistant_msg),
            })
        except GeneratorExit:
            raise
        except Exception:
            stream_log.exception('RAG stream failed')
            yield _sse('error', {'detail': 'Streaming failed. Check Django logs and Ollama connectivity.'})

    result = StreamingHttpResponse(events(), content_type='text/event-stream; charset=utf-8')
    result['Cache-Control'] = 'no-cache, no-transform'
    result['X-Accel-Buffering'] = 'no'
    return result
