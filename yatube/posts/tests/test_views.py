import shutil

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Comment, Follow, Group, Post

User = get_user_model()


class PagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        cls.user = User.objects.create_user(username='foo')

        cls.group = Group.objects.create(
            title='Заголовок тестовой группы',
            slug='test-group',
            description='Тестовое описание группы',
        )

        cls.post = Post.objects.create(
            text='test' * 10,
            pub_date='2020-05-22',
            author=cls.user,
            group=cls.group,
            image=uploaded
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PagesTests.user)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_pages_use_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            'index.html': reverse('posts:index'),
            'group.html': reverse('posts:group_posts',
                                  kwargs={'slug': PagesTests.group.slug}),
            'post_form.html': reverse('posts:new_post'),
        }
        for template, reverse_name in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_new_and_edit_post_show_correct_context(self):
        """Шаблоны new_post, edit_post сформированы с правильным контекстом."""
        pages = {
            'posts:new_post': None,
            'posts:edit_post': {'username': PagesTests.user.username,
                                'post_id': PagesTests.post.id},
        }
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }

        for name, kwargs in pages.items():
            with self.subTest(name=name):
                response = self.authorized_client.get(
                    reverse(name, kwargs=kwargs))

                for value, expected in form_fields.items():
                    with self.subTest(value=value):
                        form_field = response.context['form'].fields[value]
                        self.assertIsInstance(form_field, expected)

    def test_pages_show_correct_context(self):
        """Шаблон страницы сформирован с правильным контекстом."""
        pages = {
            'posts:index': None,
            'posts:group_posts': {'slug': PagesTests.group.slug},
            'posts:profile': {'username': PagesTests.user.username}
        }

        for name, kwargs in pages.items():
            with self.subTest(name=name):
                response = self.authorized_client.get(
                    reverse(name, kwargs=kwargs))

                first_post = response.context.get('page')[0]
                self.assertEqual(first_post, PagesTests.post)

    def test_post_show_correct_context(self):
        """Шаблон отдельного поста сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post',
                    kwargs={'username': PagesTests.user.username,
                            'post_id': PagesTests.post.id})
        )
        self.assertEqual(response.context['author'],
                         PagesTests.user)
        self.assertEqual(response.context['post'],
                         PagesTests.post)

    def test_group_page_show_correct_context(self):
        """Пост не попадает в другую группу"""
        group_other = Group.objects.create(
            title='Заголовок другой тестовой группы',
            slug='test-group-2',
            description='Тестовое описание другой группы',
        )
        post_other = Post.objects.create(
            text='test0' * 10,
            pub_date='2020-05-23',
            author=PagesTests.user,
            group=group_other,
        )

        response = self.authorized_client.get(
            reverse('posts:group_posts',
                    kwargs={'slug': PagesTests.group.slug})
        )

        first_post = response.context.get('page')[0]
        self.assertNotEqual(first_post, post_other)


class PaginatorTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='foo')

        cls.group = Group.objects.create(
            title='Заголовок тестовой группы',
            slug='test-group',
            description='Тестовое описание группы',
        )
        for i in range(13):
            cls.post = Post.objects.create(
                text=f'test{i}' * 10,
                pub_date='2020-05-22',
                author=cls.user,
                group=cls.group,
            )
        cls.pages = {
            'posts:index': None,
            'posts:group_posts': {'slug': cls.group.slug},
            'posts:profile': {'username': cls.user.username},
        }

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PagesTests.user)

    def test_paginator(self):
        """Тест паджинатора"""
        for name, kwargs in PaginatorTest.pages.items():
            with self.subTest(name=name):
                response = self.authorized_client.get(
                    reverse(name, kwargs=kwargs))
                self.assertEqual(
                    len(response.context['page'].object_list), 10)
                response = self.authorized_client.get(
                    reverse(name, kwargs=kwargs) + '?page=2')
                self.assertEqual(
                    len(response.context['page'].object_list), 3)


class CacheTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='foo')

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(CacheTests.user)

    def test_index_page_cache(self):
        """Проверка кэша главной страницы"""
        initial_response = self.authorized_client.get(reverse('posts:index'))
        Post.objects.create(text='TestCache' * 10,
                            pub_date='2020-05-22',
                            author=CacheTests.user)
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(initial_response.context, response.context)
        self.assertEqual(initial_response.content, response.content)
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(initial_response.content, response.content)


class FollowsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_author = User.objects.create_user(username='foo')
        cls.user_other_author = User.objects.create_user(username='barbar')
        cls.user_follower = User.objects.create_user(username='bar')
        cls.user_other = User.objects.create_user(username='foobar')

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(FollowsTests.user_follower)

    def test_follow(self):
        """Проверка подписки на автора"""
        self.assertFalse(
            Follow.objects.filter(
                author__id=FollowsTests.user_author.id,
                user__id=FollowsTests.user_follower.id
            ).exists()
        )
        response = self.authorized_client.get(
            reverse('posts:profile_follow',
                    kwargs={'username': FollowsTests.user_author.username}))
        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            Follow.objects.filter(
                author__id=FollowsTests.user_author.id,
                user__id=FollowsTests.user_follower.id
            ).exists()
        )

    def test_unfollow(self):
        """Проверка отписки от автора"""
        Follow.objects.create(
            author_id=FollowsTests.user_author.id,
            user_id=FollowsTests.user_follower.id
        )
        response = self.authorized_client.get(
            reverse('posts:profile_unfollow',
                    kwargs={'username': FollowsTests.user_author.username}))
        self.assertEqual(response.status_code, 302)

        self.assertFalse(
            Follow.objects.filter(
                author__id=FollowsTests.user_author.id,
                user__id=FollowsTests.user_follower.id
            ).exists()
        )

    def test_follow_index(self):
        """Проверка ленты подписок"""
        post_other_author = Post.objects.create(
            text='OtherAuthorPost' * 10,
            author=FollowsTests.user_other_author
        )
        post_author = Post.objects.create(
            text='AuthorPost' * 10,
            author=FollowsTests.user_author
        )
        Follow.objects.create(
            author_id=FollowsTests.user_other_author.id,
            user_id=FollowsTests.user_other.id
        )
        Follow.objects.create(
            author_id=FollowsTests.user_author.id,
            user_id=FollowsTests.user_follower.id
        )

        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertEqual(response.status_code, 200)

        first_post = response.context.get('page')[0]
        self.assertEqual(first_post, post_author)

        self.authorized_client.force_login(FollowsTests.user_other)

        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertEqual(response.status_code, 200)

        first_post = response.context.get('page')[0]
        self.assertNotEqual(first_post, post_author)
        self.assertEqual(first_post, post_other_author)


class CommentsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_author = User.objects.create_user(username='foo')
        cls.user_commentator = User.objects.create_user(username='bar')

        cls.post = Post.objects.create(
            text='CommentsTest' * 10,
            author=cls.user_author,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(CommentsTests.user_commentator)

    def test_authorized_user_comment(self):
        """Тестирование комментариев авторизованным пользователем"""
        comment = 'test comment'
        response = self.authorized_client.post(
            reverse('posts:add_comment',
                    kwargs={'username': CommentsTests.user_author.username,
                            'post_id': CommentsTests.post.id}),
            {'text': comment}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Comment.objects.filter(author_id=CommentsTests.user_commentator.id,
                                   post_id=CommentsTests.post.id,
                                   text=comment
                                   ).exists()
        )

    def test_unauthorized_user_comment(self):
        """Тестирование комментариев неавторизованным пользователем"""
        comment = 'test comment'
        initial_comments_count = Comment.objects.filter(
            author_id=CommentsTests.user_commentator.id,
            post_id=CommentsTests.post.id,
        ).count()

        response = self.guest_client.post(
            reverse('posts:add_comment',
                    kwargs={'username': CommentsTests.user_author.username,
                            'post_id': CommentsTests.post.id}),
            {'text': comment}
        )
        self.assertEqual(response.status_code, 302)

        comments_count = Comment.objects.filter(
            author_id=CommentsTests.user_commentator.id,
            post_id=CommentsTests.post.id,
        ).count()

        self.assertEqual(initial_comments_count, comments_count)
