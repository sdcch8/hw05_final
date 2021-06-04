from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class ModelTest(TestCase):
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

    def test_post_object_name_is_title_field(self):
        """В поле __str__  объекта post записано значение post.title[:15]."""
        post = ModelTest.post
        expected_object_name = post.text[:15]
        self.assertEqual(expected_object_name, str(post))

    def test_group_object_name_is_title_field(self):
        """В поле __str__  объекта group записано значение group.title."""
        group = ModelTest.group
        expected_object_name = group.title
        self.assertEqual(expected_object_name, str(group))
