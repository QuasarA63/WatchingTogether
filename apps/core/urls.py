from django.urls import path
from django.contrib.auth import views as auth_views
from apps.users.forms import LoginForm
from . import web_views

urlpatterns = [
    path('', web_views.home, name='home'),
    path('register/', web_views.register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(
        template_name='pages/login.html',
        authentication_form=LoginForm,
        redirect_authenticated_user=True
    ), name='login'),
    path('logout/', web_views.logout_view, name='logout'),
    path('profile/', web_views.profile_view, name='profile'),
    path('profile/edit/', web_views.profile_edit_view, name='profile_edit'),
]
