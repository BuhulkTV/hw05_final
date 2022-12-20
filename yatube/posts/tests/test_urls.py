from http import HTTPStatus

from django.test import TestCase, Client

from ..models import Group, Post, User


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            pk='1',
        )
        cls.another_user = User.objects.create_user(username='not_author')
        cls.post_another_author = Post.objects.create(
            author=cls.another_user,
            text='Тестовый пост',
            pk='2',
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test',
            description='Тестовое описание',
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(StaticURLTests.user)
        self.url_public_names = [
            '/',
            '/group/test/',
            '/profile/auth/',
            '/posts/1/',
        ]
        self.url_private_names = [
            '/',
            '/group/test/',
            '/profile/auth/',
            '/posts/1/',
            '/create/',
            '/posts/1/edit/',
        ]

    def test_exists_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        url_templates_names = {
            '/': 'posts/index.html',
            '/group/test/': 'posts/group_list.html',
            '/profile/auth/': 'posts/profile.html',
            '/posts/1/': 'posts/post_detail.html',
            '/posts/1/edit/': 'posts/post_create.html',
            '/create/': 'posts/post_create.html',
        }
        for url, template in url_templates_names.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_urls_exists_at_desired_location(self):
        """URL-адреса доступны анонимному пользователю"""
        for url in self.url_public_names:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_exists_at_desired_location_authorized(self):
        """URL-адреса доступны залогиненному пользователю"""
        for url in self.url_private_names:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unexisting_page_url_exists_at_desired_location(self):
        """Страница /group/ не существует, возврат ошибки 404"""
        response = self.guest_client.get('/group/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')

    def test_url_redirect_anonymous_on_auth_login(self):
        """Страница /create/, /posts/1/edit/ и /posts/1/comment
        перенаправит анонимного пользователя на страницу логина
        """
        url_login_names = {
            '/create/': '/auth/login/?next=/create/',
            '/posts/1/edit/': '/auth/login/?next=/posts/1/edit/',
            '/posts/1/comment/': '/auth/login/?next=/posts/1/comment/',
        }
        for url, login_url in url_login_names.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url, follow=True)
                self.assertRedirects(
                    response, (login_url))

    def test_edit_redirect_authorized_not_author(self):
        """Страница /posts/2/edit/ перенаправит не автора
        на страницу /posts/2/
        """
        response = self.authorized_client.get('/posts/2/edit/', follow=True)
        self.assertRedirects(
            response, ('/posts/2/'))
