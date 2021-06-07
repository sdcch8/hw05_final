from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import CommentForm, PostForm
from .models import Group, Post, User


def paginator_page(request, posts):
    posts_per_page = 10
    paginator = Paginator(posts, posts_per_page)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def index(request):
    posts = Post.objects.all()
    page = paginator_page(request, posts)
    return render(request, 'index.html', {'page': page})


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()

    page = paginator_page(request, posts)

    context = {"group": group, "page": page}
    return render(request, "group.html", context)


def profile(request, username):
    author = get_object_or_404(User, username=username)

    posts = author.posts.all()
    posts_count = author.posts.count()
    top_post = posts.first()

    followers_count = author.following.count()
    following_count = author.follower.count()
    is_following = author.following.exists()

    page = paginator_page(request, posts)

    context = {'author': author,
               'posts_count': posts_count,
               'top_post': top_post,
               'page': page,
               'followers_count': followers_count,
               'following_count': following_count,
               'is_following': is_following}
    return render(request, 'profile.html', context)


def post_view(request, username, post_id):
    post = get_object_or_404(Post.objects.select_related('author'),
                             author__username=username, id=post_id)
    author = post.author
    posts_count = author.posts.count()

    followers_count = author.following.count()
    following_count = author.follower.count()
    is_following = author.following.exists()

    comments = post.comments.all()
    form = CommentForm()

    context = {'author': author,
               'post': post,
               'posts_count': posts_count,
               'form': form,
               'comments': comments,
               'comment_url': reverse('posts:add_comment',
                                      kwargs={'username': author.username,
                                              'post_id': post.id}),
               'followers_count': followers_count,
               'following_count': following_count,
               'is_following': is_following
               }
    return render(request, 'post.html', context)


@login_required()
def new_post(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:index')

    form = PostForm()
    return render(request, 'post_form.html', {'form': form})


@login_required()
def edit_post_view(request, username, post_id):
    if request.user.username != username:
        return redirect('posts:post', username=username, post_id=post_id)

    original_post = (Post.objects.select_related('author')
                     .filter(author__username=username,
                     id=post_id).first())

    form = PostForm(request.POST or None,
                    files=request.FILES or None,
                    instance=original_post)

    if form.is_valid():
        form.save()
        return redirect('posts:post', username=username, post_id=post_id)

    form_data = {'text': original_post.text, 'group': original_post.group,
                 'image': original_post.image}
    form = PostForm(initial=form_data)
    id = {'username': username, 'post_id': post_id}
    context = {'form': form, 'post': original_post, 'id': id}
    return render(request, 'post_form.html', context)


@login_required()
def add_comment(request, username, post_id):
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post_id = post_id
        comment.author = request.user
        comment.save()
    return redirect('posts:post', username=username, post_id=post_id)


@login_required
def profile_follow(request, username):
    author = User.objects.filter(username=username).first()
    if (author.id == request.user.id
       or author.following.filter(user_id=request.user.id).exists()):
        return redirect(request.META.get('HTTP_REFERER', '/'))

    following = author.following.create(user_id=request.user.id)
    following.save()
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def profile_unfollow(request, username):
    author = User.objects.filter(username=username).first()
    following = author.following.filter(user_id=request.user.id)
    following.delete()
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def follow_index(request):
    posts = Post.objects.filter(author__following__user=request.user)
    page = paginator_page(request, posts)
    return render(request, "follow.html", {'page': page})


def page_not_found(request, exception):
    return render(
        request,
        "misc/404.html",
        {"path": request.path},
        status=404
    )


def server_error(request):
    return render(request, "misc/500.html", status=500)
