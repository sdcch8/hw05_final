from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import CommentForm, PostForm
from .models import Comment, Group, Post, User


def index(request):
    post_list = Post.objects.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, 'index.html', {'page': page})


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, "group.html", {"group": group, "page": page})


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts_list = author.posts.all()
    posts_count = author.posts.count()
    if len(posts_list) > 0:
        top_post = posts_list[0]
    else:
        top_post = {}
    paginator = Paginator(posts_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, 'profile.html', {'author': author,
                                            'posts_count': posts_count,
                                            'top_post': top_post,
                                            'page': page, })


def post_view(request, username, post_id):
    post = (Post.objects.select_related('author')
            .filter(author__username=username, id=post_id))[0]
    author = post.author
    posts_count = author.posts.count()
    form = CommentForm()
    comments = Comment.objects.filter(post=post_id)
    context = {'author': author,
               'post': post,
               'posts_count': posts_count,
               'form': form,
               'comments': comments,
               'url': reverse('posts:add_comment',
                              kwargs={'username': author.username,
                                      'post_id': post.id,
                                      }
                              )
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

    form_data = {'text': original_post.text, 'group': original_post.group}
    form = PostForm(initial=form_data)
    id = {'username': username, 'post_id': post_id}
    return render(request, 'post_form.html', {'form': form, 'id': id})


@login_required()
def add_comment(request, username, post_id):
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post_id = post_id
        comment.author = request.user
        comment.save()
        return redirect('posts:post', username=username, post_id=post_id)

    form = CommentForm()
    return render(request, 'comment.html', {'form': form})


def page_not_found(request, exception):
    return render(
        request,
        "misc/404.html",
        {"path": request.path},
        status=404
    )


def server_error(request):
    return render(request, "misc/500.html", status=500)
