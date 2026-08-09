from django.urls import path
from . import web_views

urlpatterns = [
    path('', web_views.group_list, name='group_list'),
    path('create/', web_views.group_create, name='group_create'),
    path('<int:pk>/', web_views.group_detail, name='group_detail'),
    path('<int:pk>/join/', web_views.group_join, name='group_join'),
    path('<int:pk>/leave/', web_views.group_leave, name='group_leave'),
]
