from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class UserRoleTests(TestCase):
    def test_roles_and_suspend(self):
        User = get_user_model()
        user = User.objects.create_user('u1', 'u1@example.com', 'pw', role=User.ROLE_LECTEUR)
        self.assertTrue(user.is_lecteur())
        user.is_suspended = True
        user.save()
        self.assertTrue(user.is_suspended)

    def test_admin_cannot_suspend_self(self):
        User = get_user_model()
        admin = User.objects.create_user('self_admin', 'admin@example.com', 'pw', role=User.ROLE_ADMIN)
        self.client.force_login(admin)

        response = self.client.post(reverse('accounts:user_toggle_status', args=[admin.pk]))
        admin.refresh_from_db()

        self.assertRedirects(response, reverse('accounts:user_list'))
        self.assertEqual(admin.statut_compte, User.STATUT_ACTIF)
        self.assertFalse(admin.is_suspended)


class AuthenticationCsrfTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.login_url = reverse('accounts:login')

    def _csrf_token(self, response):
        cookie = response.client.cookies.get('csrftoken')
        self.assertIsNotNone(cookie)
        return cookie.value

    def test_login_get_sets_csrf_cookie(self):
        client = Client(enforce_csrf_checks=True)
        response = client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('csrftoken', client.cookies)
        self.assertIn('no-store', response.headers['Cache-Control'])

    def test_login_requires_valid_csrf_token(self):
        user = self.User.objects.create_user('reader', 'reader@example.com', 'pw', role=self.User.ROLE_LECTEUR)
        client = Client(enforce_csrf_checks=True)
        response = client.get(self.login_url)
        token = self._csrf_token(response)

        response = client.post(self.login_url, {
            'username': user.username,
            'password': 'pw',
            'csrfmiddlewaretoken': token,
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('dashboard:reader'))

    def test_login_redirects_by_role(self):
        cases = [
            ('admin', self.User.ROLE_ADMIN, reverse('dashboard:admin')),
            ('biblio', self.User.ROLE_BIBLIO, reverse('dashboard:biblio')),
            ('reader', self.User.ROLE_LECTEUR, reverse('dashboard:reader')),
        ]
        for username, role, expected_url in cases:
            with self.subTest(role=role):
                self.User.objects.create_user(username, f'{username}@example.com', 'pw', role=role)
                client = Client(enforce_csrf_checks=True)
                response = client.get(self.login_url)
                token = self._csrf_token(response)
                response = client.post(self.login_url, {
                    'username': username,
                    'password': 'pw',
                    'csrfmiddlewaretoken': token,
                })
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response['Location'], expected_url)

    def test_register_get_sets_csrf_cookie(self):
        client = Client(enforce_csrf_checks=True)
        response = client.get(reverse('accounts:register'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('csrftoken', client.cookies)
        self.assertIn('no-store', response.headers['Cache-Control'])

    def test_stale_login_csrf_redirects_to_fresh_login(self):
        client = Client(enforce_csrf_checks=True)
        client.get(self.login_url)
        response = client.post(self.login_url, {
            'username': 'reader',
            'password': 'pw',
            'csrfmiddlewaretoken': 'stale-token-from-browser-cache',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], self.login_url)

    def test_logout_with_valid_csrf(self):
        user = self.User.objects.create_user('reader', 'reader@example.com', 'pw', role=self.User.ROLE_LECTEUR)
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        response = client.get(reverse('dashboard:reader'))
        token = self._csrf_token(response)
        response = client.post(reverse('accounts:logout'), {'csrfmiddlewaretoken': token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/')

    def test_login_after_refresh_uses_current_token(self):
        user = self.User.objects.create_user('reader', 'reader@example.com', 'pw', role=self.User.ROLE_LECTEUR)
        client = Client(enforce_csrf_checks=True)
        client.get(self.login_url)
        response = client.get(self.login_url)
        token = self._csrf_token(response)
        response = client.post(self.login_url, {
            'username': user.username,
            'password': 'pw',
            'csrfmiddlewaretoken': token,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('dashboard:reader'))
