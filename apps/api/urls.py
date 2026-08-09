from django.urls import path, include
from rest_framework.routers import DefaultRouter

app_name = 'api'

router = DefaultRouter()

# Здесь будут зарегистрированы ViewSets
# router.register(r'users', UserViewSet)
# router.register(r'groups', GroupViewSet)
# router.register(r'content', ContentItemViewSet)
# router.register(r'reviews', ReviewViewSet)

urlpatterns = [
    path('', include(router.urls)),
    
    # Authentication endpoints
    # path('auth/', include('apps.users.urls')),
]
