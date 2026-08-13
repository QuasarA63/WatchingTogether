from django.urls import path
from . import web_views

urlpatterns = [
    path('', web_views.notification_list, name='notification_list'),
    path('mark-all-read/', web_views.notification_mark_all_read, name='notification_mark_all_read'),
    path('<int:pk>/open/', web_views.notification_open, name='notification_open'),
]
