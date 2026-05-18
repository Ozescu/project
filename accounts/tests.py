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

    def test_reader_can_edit_own_profile_without_changing_role(self):
        User = get_user_model()
        reader = User.objects.create_user('reader_profile', 'old@example.com', 'pw', role=User.ROLE_LECTEUR)
        self.client.force_login(reader)

        response = self.client.post(reverse('accounts:profile_edit'), {
            'username': 'reader_updated',
            'email': 'new@example.com',
            'first_name': 'Ali',
            'last_name': 'Amrani',
            'telephone': '0600000000',
            'adresse': 'Casablanca',
            'role': User.ROLE_ADMIN,
        })

        reader.refresh_from_db()
        self.assertRedirects(response, reverse('accounts:profile'))
        self.assertEqual(reader.username, 'reader_updated')
        self.assertEqual(reader.email, 'new@example.com')
        self.assertEqual(reader.telephone, '0600000000')
        self.assertEqual(reader.adresse, 'Casablanca')
        self.assertEqual(reader.role, User.ROLE_LECTEUR)

    def test_admin_can_add_edit_and_suspend_bibliothecaire(self):
        User = get_user_model()
        admin = User.objects.create_user('admin_staff', 'admin_staff@example.com', 'pw', role=User.ROLE_ADMIN)
        self.client.force_login(admin)

        response = self.client.post(reverse('accounts:user_add') + f'?role={User.ROLE_BIBLIO}', {
            'username': 'new_biblio',
            'email': 'biblio@example.com',
            'first_name': 'Sara',
            'last_name': 'Biblio',
            'telephone': '0611111111',
            'adresse': 'Rabat',
            'role': User.ROLE_BIBLIO,
            'statut_compte': User.STATUT_ACTIF,
            'password': 'biblio-pass-123',
        })

        biblio = User.objects.get(username='new_biblio')
        self.assertRedirects(response, reverse('accounts:user_list') + f'?role={User.ROLE_BIBLIO}')
        self.assertEqual(biblio.role, User.ROLE_BIBLIO)
        self.assertEqual(biblio.statut_compte, User.STATUT_ACTIF)
        self.assertFalse(biblio.is_suspended)
        self.assertTrue(biblio.check_password('biblio-pass-123'))

        response = self.client.post(reverse('accounts:user_edit', args=[biblio.pk]), {
            'username': 'new_biblio',
            'email': 'updated_biblio@example.com',
            'first_name': 'Sara',
            'last_name': 'Updated',
            'telephone': '0622222222',
            'adresse': 'Casablanca',
            'role': User.ROLE_BIBLIO,
            'statut_compte': User.STATUT_ACTIF,
            'password': '',
        })
        biblio.refresh_from_db()

        self.assertRedirects(response, reverse('accounts:user_list') + f'?role={User.ROLE_BIBLIO}')
        self.assertEqual(biblio.email, 'updated_biblio@example.com')
        self.assertEqual(biblio.telephone, '0622222222')

        response = self.client.post(reverse('accounts:user_toggle_status', args=[biblio.pk]))
        biblio.refresh_from_db()

        self.assertRedirects(response, reverse('accounts:user_list'))
        self.assertEqual(biblio.statut_compte, User.STATUT_SUSPENDU)
        self.assertTrue(biblio.is_suspended)

        self.client.logout()
        response = self.client.post(reverse('accounts:login'), {
            'username': 'new_biblio',
            'password': 'biblio-pass-123',
        })
        self.assertRedirects(response, reverse('accounts:login'))


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
