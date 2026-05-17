from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/auth/register/'
        self.login_url = '/auth/login/'
        self.user_data = {
            'full_name': 'João Silva',
            'cpf': '12345678901',
            'email': 'joao@email.com',
            'phone': '84999999999',
            'birth_at': '2000-01-01',
            'role': 'customer',
            'password': 'Senha@123'
        }
    
    def test_register_success(self):
        response = self.client.post(self.register_url, self.user_data, format='json')
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['email'], 'joao@email.com')

    def test_register_duplicate_email(self):
        self.client.post(self.register_url, self.user_data, format='json')
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code,status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_cpf(self):
        self.client.post(self.register_url, self.user_data, format='json')
        data = self.user_data.copy()
        data['email'] = 'outro@email.com'
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_success(self):
        self.client.post(self.register_url, self.user_data, format='json')
        response = self.client.post(self.login_url, {
            'email': 'joao@email.com',
            'password': 'Senha@123'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
    
    def test_login_wrong_password(self):
        self.client.post(self.register_url, self.user_data, format='json')
        response = self.client.post(self.login_url, {
            'email': 'joao@email.com',
            'password': 'senhaerrada'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_email(self):
        response = self.client.post(self.login_url, {
            'email': 'naoexiste@email.com',
            'password': 'senha123'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_register_weak_password(self):
        data = self.user_data.copy()
        data['password'] = '123'
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_invalid_cpf(self):
        data = self.user_data.copy()
        data['cpf'] = '111'
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_invalid_phone(self):
        data = self.user_data.copy()
        data['phone'] = '123'
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)