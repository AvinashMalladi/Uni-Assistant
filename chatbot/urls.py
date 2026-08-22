from django.urls import path
from . import views

urlpatterns = [
    path('message/', views.chat_message, name='chat_message'),
    path('widget-message/', views.widget_chat_message, name='widget_chat_message'),
]
