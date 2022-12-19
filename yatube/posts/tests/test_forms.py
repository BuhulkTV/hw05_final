import shutil
import tempfile

from django.test import Client, TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.urls import reverse

from ..models import Group, Post, User, Comment, Follow

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test',
            description='Тестовое описание',
        )
        cls.post_group = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='Тестовый пост с группой',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PostCreateFormTests.user)

    def test_post_create_with_group(self):
        """Валидная форма создает запись Post с группой"""
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
            'text': 'Тестовый пост',
            'group': self.group.pk,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': 'auth'}
        ))
        post_response = Post.objects.latest('pub_date')
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(post_response.text, form_data['text'])
        self.assertEqual(post_response.group.pk, form_data['group'])
        self.assertEqual(post_response.image.name, 'posts/small.gif')

    def test_post_edit_with_group(self):
        """После редактирования Post с группой изменяется в БД"""
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
            'text': 'Тест редактирования поста',
            'group': self.group.pk,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post_group.pk}),
            data=form_data,
            follow=True,
        )
        post_response = Post.objects.get(pk=self.post_group.pk)
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': post_response.pk}
        ))
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertEqual(post_response.text, form_data['text'])
        self.assertEqual(post_response.group.pk, form_data['group'])
        self.assertContains(response, '<img')


class CommentFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост с комментарием',
        )
        cls.comment = Comment.objects.create(
            text='Тестовый комментарий',
            post=cls.post,
            author=cls.user
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(CommentFormTest.user)

    def test_post_create_with_group(self):
        """Валидная форма создает Comment к Post"""
        comment_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовый новый комментарий',
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.pk}
        ))
        comment_response = Comment.objects.latest('created')
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        self.assertEqual(comment_response.text, form_data['text'])


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
        пользователей и удалять их из подписок.
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
