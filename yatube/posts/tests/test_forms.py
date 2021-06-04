import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()


class NewPostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='foo')
        cls.group = Group.objects.create(
            title='Заголовок тестовой группы',
            slug='test-group',
            description='Тестовое описание группы',
        )
        settings.MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(NewPostFormTests.user)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_create_new_post(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
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
        form_data = {
            'text': 'test' * 10,
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:new_post'),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('posts:index'))
        self.assertEqual(Post.objects.count(), posts_count + 1)

        post = Post.objects.filter(text=form_data['text'],
                                   author=NewPostFormTests.user,
                                   group=NewPostFormTests.group.id,
                                   image='posts/small.gif'
                                   ).first()

        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author, NewPostFormTests.user)
        self.assertEqual(post.group_id, NewPostFormTests.group.id)
        self.assertEqual(post.image, 'posts/small.gif')


class EditPostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(EditPostFormTests.user)

    def test_edit_post(self):
        """Валидная форма редактирует запись в Post."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'test2' * 10,
            'group': self.group.id,
        }
        response = self.authorized_client.post(
            reverse('posts:edit_post',
                    kwargs={'username': EditPostFormTests.user.username,
                            'post_id': EditPostFormTests.post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(
            response,
            reverse('posts:post',
                    kwargs={'username': EditPostFormTests.user.username,
                            'post_id': EditPostFormTests.post.id}))
        self.assertEqual(Post.objects.count(), posts_count)

        post = Post.objects.filter(text=form_data['text'],
                                   author=EditPostFormTests.user,
                                   group=EditPostFormTests.group.id).first()
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author, EditPostFormTests.user)
        self.assertEqual(post.group_id, EditPostFormTests.group.id)

        response = self.authorized_client.get(
            reverse('posts:group_posts',
                    kwargs={'slug': EditPostFormTests.group.slug})
        )
        self.assertEqual(response.status_code, 200)
        first_object = response.context['page'][0]
        self.assertEqual(first_object.text, form_data['text'])
        self.assertEqual(first_object.author, EditPostFormTests.user)
        self.assertEqual(first_object.group.id, EditPostFormTests.group.id)


class GuestNewPostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='foo')
        cls.group = Group.objects.create(
            title='Заголовок тестовой группы',
            slug='test-group',
            description='Тестовое описание группы',
        )

    def setUp(self):
        self.unauthorized_client = Client()

    def test_create_new_post(self):
        """Неавторизованный пользователь не создает запись в Post."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'test' * 10,
            'group': self.group.id,
        }
        response = self.unauthorized_client.post(
            reverse('posts:new_post'),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        url_auth = reverse('login')
        url_new_post = reverse('posts:new_post')
        self.assertRedirects(response, f'{url_auth}?next={url_new_post}')
        self.assertEqual(Post.objects.count(), posts_count)
