from django.urls import path
from django.contrib.auth import views as auth_views
from . import web_views

urlpatterns = [
    path('', web_views.home, name='home'),
    path('register/', web_views.register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(
        template_name='pages/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', web_views.profile_view, name='profile'),
]
