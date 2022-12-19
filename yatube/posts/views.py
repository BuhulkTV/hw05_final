from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from .models import Post, Group, User, Follow
from .forms import PostForm, CommentForm
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page
from django.urls import reverse


def get_page_context(queryset, request):
    paginator = Paginator(queryset, settings.POSTS_COUNT)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return {
        'paginator': paginator,
        'page_number': page_number,
        'page_obj': page_obj,
    }


@cache_page(settings.CACHES_SEC)
def index(request):
    template = 'posts/index.html'
    title = 'Это главная страница проекта Yatube'
    post_list = Post.objects.select_related('author', 'group').all()
    context = {
        'title': title,
    }
    context.update(get_page_context(post_list, request))
    return render(request, template, context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    template = 'posts/group_list.html'
    post_list = group.posts.all()
    is_group = True
    context = {
        'group': group,
        'is_group': is_group
    }
    context.update(get_page_context(post_list, request))
    return render(request, template, context)


def profile(request, username):
    template = 'posts/profile.html'
    author = get_object_or_404(User, username=username)
    post_list = author.posts.all()
    posts_count = author.posts.count()
    user = request.user
    following = user.is_authenticated and author.following.exists()
    context = {
        'author': author,
        'posts_count': posts_count,
        'following': following,
    }
    context.update(get_page_context(post_list, request))
    return render(request, template, context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    template = 'posts/post_detail.html'
    author = post.author
    posts_count = author.posts.select_related('author').count()
    comment_form = CommentForm(request.POST or None)
    comments = post.comments.all()
    context = {
        'post': post,
        'posts_count': posts_count,
        'comments': comments,
        'comment_form': comment_form
    }
    return render(request, template, context)


@login_required
def post_create(request):
    templates = "posts/post_create.html"
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
    )
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', post.author)
    context = {
        'form': form
    }
    return render(request, templates, context)


@login_required
def post_edit(request, post_id):
    templates = "posts/post_create.html"
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post.pk)
    is_edit = True
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post,
    )
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:post_detail', post.pk)
    context = {
        'form': form,
        'post': post,
        'is_edit': is_edit,
    }
    return render(request, templates, context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post.pk)


@login_required
def follow_index(request):
    title = 'Посты ваших избранных авторов'
    template = 'posts/follow.html'
    user = request.user
    authors = user.follower.values_list('author', flat=True)
    post_list = Post.objects.filter(author__id__in=authors)
    context = {
        'title': title,
    }
    context.update(get_page_context(post_list, request))
    return render(request, template, context)


@login_required
def profile_follow(request, username):
    user_active = request.user
    author = get_object_or_404(User, username=username)
    if user_active != author:
        Follow.objects.get_or_create(user=user_active, author=author)
        return redirect(reverse('posts:follow_index'))
    return redirect(reverse('posts:follow_index'))


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user, author=author).delete()
    return redirect(reverse('posts:follow_index'))
