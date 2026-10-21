from django.urls import path
from . import views
urlpatterns = [
    path('conversations/', views.conversations),
    path('conversations/<int:pk>/', views.conversation_detail),
    path('ask/', views.ask),
    path('ask-stream/', views.ask_stream),
]
