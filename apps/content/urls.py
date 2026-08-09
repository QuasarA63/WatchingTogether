from django.urls import path
from . import web_views

urlpatterns = [
    path('', web_views.content_list, name='content_list'),
    path('<int:pk>/', web_views.content_detail, name='content_detail'),
]
