from django.urls import include, path
from core.views import health, me, provider_info

from knowledge.views import documents, document_detail, semantic_search
urlpatterns = [
    path('api/health/', health),
    path('api/auth/me/', me),
    path('api/ai/provider/', provider_info),
    path('api/knowledge/documents/', documents),
    path('api/knowledge/documents/<int:pk>/', document_detail),
    path('api/knowledge/search/', semantic_search),
    
]

from chat.views import conversations, conversation_detail, ask , memories, memory_detail
urlpatterns += [
    path('api/chat/', include("chat.urls")),
    path('api/chat/conversations/', conversations),
    path('api/chat/conversations/<int:pk>/', conversation_detail),
    path('api/chat/ask/', ask),
    path("api/chat/memories/", memories),
    path("api/chat/memories/<int:pk>/", memory_detail),
    path("api/artifacts/", include("artifacts.urls")),
]
