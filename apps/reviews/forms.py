from django import forms
from .models import Review, Comment


class ReviewForm(forms.ModelForm):
    """
    Форма создания/редактирования отзыва.
    """
    class Meta:
        model = Review
        fields = ['rating', 'title', 'text', 'is_spoiler']
        labels = {
            'rating': 'Оценка (1-10)',
            'title': 'Заголовок отзыва',
            'text': 'Текст отзыва (необязательно)',
            'is_spoiler': 'Содержит спойлеры',
        }
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Заголовок (необязательно)'}),
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Ваш отзыв... (необязательно)'}),
            'is_spoiler': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CommentForm(forms.ModelForm):
    """
    Форма добавления комментария к отзыву.
    """
    class Meta:
        model = Comment
        fields = ['text']
        labels = {
            'text': 'Комментарий',
        }
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Написать комментарий...'
            }),
        }
