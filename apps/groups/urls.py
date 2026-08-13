from django.urls import path
from . import web_views

urlpatterns = [
    path('', web_views.group_list, name='group_list'),
    path('create/', web_views.group_create, name='group_create'),
    path('<int:pk>/', web_views.group_detail, name='group_detail'),
    path('<int:pk>/join/', web_views.group_join, name='group_join'),
    path('<int:pk>/leave/', web_views.group_leave, name='group_leave'),
    path('<int:pk>/invite/', web_views.group_invite, name='group_invite'),
    path('<int:pk>/chat/', web_views.group_chat, name='group_chat'),
    path('<int:pk>/chat/messages/', web_views.group_chat_messages, name='group_chat_messages'),
    path('<int:pk>/content/<int:content_pk>/', web_views.group_content_detail, name='group_content_detail'),
    path('<int:pk>/content/<int:content_pk>/take/', web_views.group_content_take, name='group_content_take'),
    path('<int:pk>/content/<int:content_pk>/comment/', web_views.group_content_comment_add, name='group_content_comment_add'),
    path('invitations/<int:pk>/accept/', web_views.invitation_accept, name='invitation_accept'),
    path('invitations/<int:pk>/decline/', web_views.invitation_decline, name='invitation_decline'),
]
