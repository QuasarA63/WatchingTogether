from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.users.views import UserViewSet
from apps.groups.views import GroupViewSet
from apps.content.views import CategoryViewSet, ContentItemViewSet, UserContentItemViewSet
from apps.reviews.views import ReviewViewSet

app_name = 'api'

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'groups', GroupViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'content', ContentItemViewSet)
router.register(r'my-content', UserContentItemViewSet, basename='my-content')
router.register(r'reviews', ReviewViewSet)

urlpatterns = [
    path('', include(router.urls)),

    # Authentication endpoints
    path('auth/', include('apps.users.urls')),
]
