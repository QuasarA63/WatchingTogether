from django import forms
from .models import Review, Comment


class ReviewForm(forms.ModelForm):
    """
    Форма создания/редактирования отзыва.
    """
    class Meta:
        model = Review
        fields = ['rating', 'title', 'text', 'is_spoiler', 'group']
        labels = {
            'rating': 'Оценка (1-10)',
            'title': 'Заголовок отзыва',
            'text': 'Текст отзыва',
            'is_spoiler': 'Содержит спойлеры',
            'group': 'Группа (необязательно)',
        }
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Заголовок (необязательно)'}),
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Ваш отзыв...'}),
            'is_spoiler': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'group': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['group'].required = False
        self.fields['group'].empty_label = '— Без группы —'
        if user is not None:
            self.fields['group'].queryset = user.member_groups.all()


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
