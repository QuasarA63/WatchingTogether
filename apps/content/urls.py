from django.urls import path
from . import web_views

urlpatterns = [
    path('', web_views.content_list, name='content_list'),
    path('my/', web_views.my_content_list, name='my_content_list'),
    path('my/search/', web_views.my_content_search, name='my_content_search'),
    path('my/add/', web_views.my_content_add, name='my_content_add'),
    path('my/<int:pk>/comment/', web_views.my_content_edit_comment, name='my_content_edit_comment'),
    path('my/<int:pk>/remove/', web_views.my_content_remove, name='my_content_remove'),
    path('<int:pk>/', web_views.content_detail, name='content_detail'),
]
