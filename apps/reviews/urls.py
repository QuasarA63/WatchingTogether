from django.urls import path
from . import web_views

urlpatterns = [
    path('<int:pk>/', web_views.review_detail, name='review_detail'),
    path('create/<int:content_pk>/', web_views.review_create, name='review_create'),
    path('<int:pk>/edit/', web_views.review_edit, name='review_edit'),
    path('<int:pk>/delete/', web_views.review_delete, name='review_delete'),
    path('<int:review_pk>/comment/', web_views.comment_create, name='comment_create'),
]
