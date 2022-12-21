import shutil
import tempfile

from django.test import Client, TestCase, override_settings
from django.conf import settings
from django.urls import reverse
from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache

from ..models import Group, Post, User, Follow

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image=cls.uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(StaticURLTests.user)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответсвующий шаблон"""
        templates_page_names = {
            reverse('posts:index'): 'posts/index.html',
            (
                reverse('posts:group_list', kwargs={'slug': 'test'})
            ): 'posts/group_list.html',
            (
                reverse('posts:profile', kwargs={'username': 'auth'})
            ): 'posts/profile.html',
            (
                reverse('posts:post_detail', kwargs={'post_id': '1'})
            ): 'posts/post_detail.html',
            (
                reverse('posts:post_edit', kwargs={'post_id': '1'})
            ): 'posts/post_create.html',
            reverse('posts:post_create'): 'posts/post_create.html',
        }
        for reverse_name, template in templates_page_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_post_show_correct_context(self):
        """Объект Post сформирован с правильным контекстом во всех шаблонах"""
        reverse_page_names = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': 'test'}),
            reverse('posts:profile', kwargs={'username': 'auth'}),
            reverse('posts:post_detail', kwargs={'post_id': '1'}),
        ]
        for reverse_name in reverse_page_names:
            if reverse_name == reverse(
                'posts:post_detail', kwargs={'post_id': '1'}
            ):
                response = self.guest_client.get(reverse_name)
                post_obj = response.context.get('post')
            else:
                response = self.guest_client.get(reverse_name)
                post_obj = response.context.get('page_obj').object_list[0]
            context_name = {
                post_obj.text: self.post.text,
                post_obj.author: self.post.author,
                post_obj.group: self.post.group,
                post_obj.pub_date: self.post.pub_date,
                post_obj.image: self.post.image,
            }
            for object_name, expected in context_name.items():
                with self.subTest():
                    self.assertEqual(object_name, expected)

    def test_index_pages_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.guest_client.get(reverse('posts:index'))
        context_names = {
            response.context.get('title'):
            'Это главная страница проекта Yatube',
        }
        for object_name, expected in context_names.items():
            with self.subTest():
                self.assertEqual(object_name, expected)

    def test_group_list_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом"""
        response = self.guest_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test'})
        )
        response_group = response.context.get('group')
        context_names = {
            response_group.slug: self.group.slug,
            response_group.title: self.group.title,
            response_group.description: self.group.description,
        }
        for response_name, context in context_names.items():
            with self.subTest():
                self.assertEqual(response_name, context)
        self.assertEqual(
            response.context.get('is_group'), True
        )

    def test_profile_list_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом"""
        response = self.guest_client.get(
            reverse('posts:profile', kwargs={'username': 'auth'})
        )
        context_names = {
            response.context.get('author'): self.user,
            response.context.get('posts_count'): self.user.posts.count(),
        }
        for response_name, context in context_names.items():
            with self.subTest():
                self.assertEqual(response_name, context)

    def test_post_detail_pages_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом"""
        response = self.guest_client.get(
            reverse('posts:post_detail', kwargs={'post_id': '1'})
        )
        context_names = {
            response.context.get('posts_count'): self.user.posts.count(),
        }
        for response_name, context in context_names.items():
            with self.subTest():
                self.assertEqual(response_name, context)

    def test_post_create_pages_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом"""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_post_edit_pages_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом"""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': '1'})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)
        self.assertEqual(
            response.context.get('post').text, self.post.text
        )
        self.assertEqual(
            response.context.get('is_edit'), True
        )


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test',
            description='Тестовое описание',
        )
        cls.page_one_len = 10
        cls.page_two_len = 3

        objs = [
            Post(
                author=cls.user,
                text=f'Тестовый пост №{x}',
                group=cls.group,
            )
            for x in range(cls.page_one_len + cls.page_two_len)
        ]
        cls.post = Post.objects.bulk_create(objs=objs)

    def setUp(self):
        cache.clear()
        self.guest_client = Client()

    def test_paginator_on_pages(self):
        """Проверка работы паджинатора"""
        reverse_context_names = {
            reverse('posts:index'): 'page_obj',
            (
                reverse('posts:group_list', kwargs={'slug': 'test'})
            ): 'page_obj',
            (
                reverse('posts:profile', kwargs={'username': 'auth'})
            ): 'page_obj',
        }
        for reverse_name, context in reverse_context_names.items():
            response_first_page = self.guest_client.get(reverse_name)
            response_second_page = self.guest_client.get(
                reverse_name + '?page=2'
            )
            self.assertEqual(
                len(response_first_page.context[context]), self.page_one_len
            )
            self.assertEqual(len(
                response_second_page.context[context]), self.page_two_len
            )


class PostOnPagesViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа 01',
            slug='test',
            description='Тестовое описание',
        )
        cls.post_group = Post.objects.create(
            author=cls.user,
            text='Тестовый пост с группой',
            group=cls.group,
        )
        cls.post_not_group = Post.objects.create(
            author=cls.user,
            text='Тестовый пост без группы',
        )

    def setUp(self):
        cache.clear()
        self.guest_client = Client()

    def test_post_on_pages(self):
        """Post с группой показывается на нужных страницах"""
        page_names = {
            reverse('posts:index'): self.post_group,
            reverse(
                'posts:group_list', kwargs={'slug': 'test'}
            ): self.post_group,
            reverse(
                'posts:profile', kwargs={'username': 'auth'}
            ): self.post_group,
        }
        for reverse_name, post_name in page_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.guest_client.get(reverse_name)
                self.assertIn(
                    post_name, response.context['page_obj'].object_list
                )

    def test_post_not_on_pages(self):
        """Post с группой не показывается на странице другой группы"""
        page_names = {
            reverse(
                'posts:group_list', kwargs={'slug': 'test'}
            ): self.post_not_group,
        }
        for reverse_name, post_name in page_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.guest_client.get(reverse_name)
                self.assertNotIn(
                    post_name, response.context['page_obj'].object_list
                )


class CacheIndexTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.post_in_index = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )
        cls.post_delete = Post.objects.create(
            author=cls.user,
            text='Тестовый пост для удаления',
        )

    def setUp(self):
        self.guest_client = Client()

    def test_cache_index(self):
        """Тест кеширования главной страницы"""
        cache.clear()
        response_first = self.guest_client.get(reverse('posts:index'))
        response_first.context['page_obj'].object_list[0].delete()
        response_second = self.guest_client.get(reverse('posts:index'))
        self.assertEqual(response_first.content, response_second.content)
        cache.clear()
        response_third = self.guest_client.get(reverse('posts:index'))
        self.assertNotEqual(response_third.content, response_second.content)


class TestFollow(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_following_one = User.objects.create_user(username='auth')
        cls.user_following_two = User.objects.create_user(
            username='following_two'
        )
        cls.user_followed = User.objects.create_user(username='user_followed')

        cls.post_following_one = Post.objects.create(
            author=cls.user_following_one,
            text='Тестовый пост первого автора',
        )
        cls.post_following_two = Post.objects.create(
            author=cls.user_following_two,
            text='Тестовый пост второго автора',
        )

    def setUp(self):
        self.authorized_client_one = Client()
        self.authorized_client_one.force_login(self.user_followed)
        self.authorized_client_two = Client()
        self.authorized_client_two.force_login(self.user_following_one)

    def test_follow(self):
        """Авторизованный пользователь может подписываться на других
        пользователей
        """
        form_data = {
            'username': self.user_followed,
        }
        self.authorized_client_one.post(
            reverse('posts:profile_follow', kwargs={
                'username': self.user_following_one.username
            }),
            data=form_data,
            follow=True,
        )
        self.assertIs(
            Follow.objects.filter(
                user=self.user_followed, author=self.user_following_one
            ).exists(),
            True
        )

    def test_unfollow(self):
        """Авторизованный пользователь может удалять избранных
        авторов из подписок.
        """
        form_data = {
            'username': self.user_followed,
        }
        Follow.objects.create(
            user=self.user_followed, author=self.user_following_one
        )
        self.authorized_client_one.post(
            reverse('posts:profile_unfollow', kwargs={
                'username': self.user_following_one.username
            }),
            data=form_data,
            follow=True,
        )
        self.assertIs(
            Follow.objects.filter(
                user=self.user_followed, author=self.user_following_one
            ).exists(),
            False
        )

    def test_new_post_in_follow(self):
        """Новая запись пользователя появляется в ленте тех,
           кто на него подписан и не появляется в ленте тех,
           кто не подписан.
        """
        Follow.objects.create(
            user=self.user_followed, author=self.user_following_one
        )
        post = Post.objects.create(
            author=self.user_following_one,
            text='Новый тестовый пост первого автора',
        )
        response = self.authorized_client_one.get(
            reverse(
                'posts:follow_index',
            )
        )
        self.assertIn(post, response.context['page_obj'].object_list)
        response = self.authorized_client_two.get(
            reverse(
                'posts:follow_index',
            )
        )
        self.assertNotIn(post, response.context['page_obj'].object_list)

    def test_follow_count(self):
        """Подписаться на автора можно только один раз"""
        Follow.objects.create(
            user=self.user_followed, author=self.user_following_one
        )
        follow_counts = self.user_followed.follower.count()
        Follow.objects.get_or_create(
            user=self.user_followed, author=self.user_following_one
        )
        self.assertEqual(self.user_followed.follower.count(), follow_counts)
