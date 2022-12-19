from django.test import TestCase

from ..models import Group, Post, User


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        object_names = {
            self.post: self.post.text,
            self.group: self.group.title,
        }
        for object_name, object_name_str in object_names.items():
            with self.subTest():
                self.assertEqual(object_name_str, str(object_name))

    def test_verbose_name(self):
        """verbose_name в полях Post совпадает с ожидаемым."""
        post = self.post
        field_verboses = {
            'text': 'Текст поста',
            'pub_date': 'Дата публикации',
            'author': 'Автор поста',
            'group': 'Группа',
        }
        for value, expected in field_verboses.items():
            with self.subTest(value=value):
                self.assertEqual(
                    post._meta.get_field(value).verbose_name, expected)

    def test_help_text(self):
        """help_text в полях Post совпадает с ожидаемым."""
        post = self.post
        field_help_texts = {
            'text': 'Укажите текст поста',
            'pub_date': 'Дата публикации поста',
            'author': 'Указывается автор поста',
            'group': 'Указывается принадлежность поста к группе',
        }
        for value, expected in field_help_texts.items():
            with self.subTest(value=value):
                self.assertEqual(
                    post._meta.get_field(value).help_text, expected)
