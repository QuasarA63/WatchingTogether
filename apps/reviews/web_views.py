from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.content.models import ContentItem
from .models import Review
from .forms import ReviewForm, CommentForm


def review_detail(request, pk):
    """
    Детальная страница отзыва с комментариями.
    """
    review = get_object_or_404(
        Review.objects.select_related('user', 'content_item', 'group'),
        pk=pk
    )
    comments = review.comments.select_related('user').filter(parent=None)

    comment_form = None
    if request.user.is_authenticated:
        comment_form = CommentForm()

    context = {
        'review': review,
        'comments': comments,
        'comment_form': comment_form,
    }
    return render(request, 'pages/review_detail.html', context)


@login_required
def review_create(request, content_pk):
    """
    Создание отзыва на контент.
    """
    content_item = get_object_or_404(ContentItem, pk=content_pk)

    existing = Review.objects.filter(user=request.user, content_item=content_item).first()
    if existing:
        messages.warning(request, 'Вы уже оставили отзыв на этот контент.')
        return redirect('review_detail', pk=existing.pk)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.content_item = content_item
            review.save()
            messages.success(request, 'Отзыв опубликован!')
            return redirect('content_detail', pk=content_item.pk)
    else:
        form = ReviewForm()

    context = {
        'form': form,
        'content_item': content_item,
        'title': f'Отзыв на «{content_item.title}»',
    }
    return render(request, 'pages/review_form.html', context)


@login_required
def review_edit(request, pk):
    """
    Редактирование своего отзыва.
    """
    review = get_object_or_404(Review, pk=pk, user=request.user)

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, 'Отзыв обновлён!')
            return redirect('review_detail', pk=review.pk)
    else:
        form = ReviewForm(instance=review)

    context = {
        'form': form,
        'content_item': review.content_item,
        'title': f'Редактирование отзыва на «{review.content_item.title}»',
    }
    return render(request, 'pages/review_form.html', context)


@login_required
def review_delete(request, pk):
    """
    Удаление своего отзыва.
    """
    review = get_object_or_404(Review, pk=pk, user=request.user)
    content_pk = review.content_item.pk
    if request.method == 'POST':
        review.delete()
        messages.info(request, 'Отзыв удалён.')
        return redirect('content_detail', pk=content_pk)
    return render(request, 'pages/review_confirm_delete.html', {'review': review})


@login_required
def comment_create(request, review_pk):
    """
    Добавление комментария к отзыву.
    """
    review = get_object_or_404(Review, pk=review_pk)

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.review = review
            comment.user = request.user
            parent_id = request.POST.get('parent_id')
            if parent_id:
                from .models import Comment
                comment.parent = get_object_or_404(Comment, pk=parent_id)
            comment.save()
            messages.success(request, 'Комментарий добавлен!')

    return redirect('review_detail', pk=review.pk)
