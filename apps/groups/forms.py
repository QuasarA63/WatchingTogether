from django import forms
from .models import Group


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
