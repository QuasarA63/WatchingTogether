from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from .models import User
from .serializers import UserSerializer, UserUpdateSerializer, RegisterSerializer, AccountUpdateSerializer


class RegisterView(generics.CreateAPIView):
    """
    Регистрация нового пользователя.
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class MeView(APIView):
    """
    Получение данных текущего пользователя.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet для просмотра и редактирования пользователей.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_serializer_class(self):
        if self.action == 'partial_update':
            return UserUpdateSerializer
        if self.action == 'account':
            return AccountUpdateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ['partial_update', 'account']:
            return [IsAuthenticated()]
        return super().get_permissions()

    def partial_update(self, request, *args, **kwargs):
        """Только владелец профиля может его редактировать."""
        user = self.get_object()
        if user != request.user:
            return Response(
                {'detail': 'Вы можете редактировать только свой профиль.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().partial_update(request, *args, **kwargs)

    @action(detail=True, methods=['patch'])
    def account(self, request, pk=None):
        """Обновление учётных данных (логин, email, пароль)."""
        user = self.get_object()
        if user != request.user:
            return Response(
                {'detail': 'Вы можете редактировать только свой профиль.'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(user).data)

    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        """Отзывы пользователя."""
        user = self.get_object()
        reviews = user.reviews.all()
        from apps.reviews.serializers import ReviewSerializer
        page = self.paginate_queryset(reviews)
        if page is not None:
            serializer = ReviewSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)
