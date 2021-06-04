from django import forms
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()


class PagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='foo')
        cls.group_other = Group.objects.create(
            title='Заголовок другой тестовой группы',
            slug='test-group-2',
            description='Тестовое описание другой группы',
        )
        cls.group = Group.objects.create(
            title='Заголовок тестовой группы',
            slug='test-group',
            description='Тестовое описание группы',
        )
        cls.post_other = Post.objects.create(
            text='test0' * 10,
            pub_date='2020-05-23',
            author=cls.user,
            group=cls.group_other,
        )
        cls.post = Post.objects.create(
            text='test' * 10,
            pub_date='2020-05-22',
            author=cls.user,
            group=cls.group,
            image='posts/small.gif'
        )
        cls.pages = {
            'posts:index': None,
            'posts:group_posts': {'slug': PagesTests.group.slug},
            'posts:profile': {'username': PagesTests.user.username}
        }

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PagesTests.user)

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

    def test_new_post_show_correct_context(self):
        """Шаблон new_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:new_post'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_edit_post_show_correct_context(self):
        """Шаблон edit_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:edit_post',
                    kwargs={'username': PagesTests.user.username,
                            'post_id': PagesTests.post.id})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_pages_show_correct_context(self):
        """Шаблон страницы сформирован с правильным контекстом."""
        for name, kwargs in PagesTests.pages.items():
            with self.subTest(name=name):
                response = self.authorized_client.get(
                    reverse(name, kwargs=kwargs))
                first_object = response.context['page'][0]
                post_text_0 = first_object.text
                post_pub_date_0 = first_object.pub_date
                post_author_0 = first_object.author
                post_group_0 = first_object.group.slug
                post_image_0 = first_object.image
                self.assertEqual(post_text_0, PagesTests.post.text)
                self.assertEqual(post_pub_date_0, PagesTests.post.pub_date)
                self.assertEqual(post_author_0, PagesTests.post.author)
                self.assertEqual(post_group_0, PagesTests.group.slug)
                self.assertEqual(post_image_0, PagesTests.post.image)

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
        response = self.authorized_client.get(
            reverse('posts:group_posts',
                    kwargs={'slug': PagesTests.group.slug})
        )
        first_object = response.context['page'][0]
        post_text_0 = first_object.text
        post_pub_date_0 = first_object.pub_date
        post_group_0 = first_object.group.slug
        self.assertNotEqual(post_text_0, PagesTests.post_other.text)
        self.assertNotEqual(post_pub_date_0, PagesTests.post_other.pub_date)
        self.assertNotEqual(post_group_0, PagesTests.group_other.slug)


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
