from django import forms
from django.contrib.auth import get_user_model
from .models import Group

User = get_user_model()


class GroupForm(forms.ModelForm):
    """
    Форма создания/редактирования группы.
    """
    class Meta:
        model = Group
        fields = ['name', 'description', 'avatar', 'is_private']
        labels = {
            'name': 'Название группы',
            'description': 'Описание',
            'avatar': 'Аватар группы',
            'is_private': 'Приватная группа',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название группы'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Описание группы'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
            'is_private': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class GroupInviteForm(forms.Form):
    """
    Форма приглашения пользователя в группу.
    """
    user = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label='Пользователь',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    message = forms.CharField(
        required=False,
        label='Сообщение',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Необязательное сообщение к приглашению'
        }),
    )

    def __init__(self, *args, **kwargs):
        users_queryset = kwargs.pop('users_queryset', User.objects.none())
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = users_queryset


class GroupMessageForm(forms.Form):
    """
    Форма сообщения в групповой чат.
    """
    text = forms.CharField(
        label='Сообщение',
        max_length=2000,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Введите сообщение...'
        }),
    )
