from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()


class URLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='foo')
        cls.other_auth_user = User.objects.create_user(username='bar')
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
        )
        cls.urls_guest = {
            '/': 200,
            f'/group/{cls.group.slug}/': 200,
            '/new/': 302,
            f'/{cls.user.username}/': 200,
            f'/{cls.user.username}/{cls.post.id}/': 200,
            f'/{cls.user.username}/{cls.post.id}/edit/': 302,
            '/test404/': 404,
        }
        cls.urls_authorized = cls.urls_guest.copy()
        cls.urls_authorized.update(
            {
                '/new/': 200,
                f'/{cls.user.username}/{cls.post.id}/edit/': 200,
            }
        )
        cls.url_auth = reverse('login')
        cls.url_new_post = reverse('posts:new_post')
        cls.redirects_guest = {
            f'{cls.url_new_post}': f'{cls.url_auth}?next={cls.url_new_post}',
            f'/{cls.user.username}/{cls.post.id}/edit/':
                f'{cls.url_auth}?next=/{cls.user.username}/{cls.post.id}/edit/'
        }
        cls.redirects_other_authorized = {
            f'/{cls.user.username}/{cls.post.id}/edit/':
                f'/{cls.user.username}/{cls.post.id}/',
        }

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(URLTests.user)
        self.other_authorized_client = Client()
        self.other_authorized_client.force_login(URLTests.other_auth_user)

    def test_guest_urls(self):
        """Тестирование неавторизованного клиента."""
        for url, response_code in URLTests.urls_guest.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, response_code)

    def test_authorized_urls(self):
        """Тестирование авторизованного клиента."""
        for url, response_code in URLTests.urls_authorized.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertEqual(response.status_code, response_code)

    def test_redirects_guest(self):
        """Тестирование редиректов анонимного пользователя"""
        for url, redirect_page in URLTests.redirects_guest.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url, follow=True)
                self.assertRedirects(response, redirect_page)

    def test_redirects_other_authorized(self):
        """Тестирование редиректов другого авторизованного пользователя"""
        for url, redirect_page in URLTests.redirects_other_authorized.items():
            with self.subTest(url=url):
                response = self.other_authorized_client.get(url, follow=True)
                self.assertRedirects(response, redirect_page)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'index.html',
            '/new/': 'post_form.html',
            f'/group/{URLTests.group.slug}/': 'group.html',
            f'/{URLTests.user.username}/{URLTests.post.id}/edit/':
                'post_form.html',
        }
        for url, template in templates_url_names.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)
