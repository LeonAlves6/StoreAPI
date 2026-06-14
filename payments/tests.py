from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from users.models import User
from .models import PaymentMethod

class PaymentMethodTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.customer = User.objects.create_user(
            email='customer@email.com',
            full_name='Customer Test',
            cpf='98765432100',
            phone='84888888888',
            birth_at='1995-01-01',
            role='customer',
            password='Senha@123'
        )

        self.seller = User.objects.create_user(
            email='seller@email.com',
            full_name='Seller Test',
            cpf='12345678901',
            phone='84999999999',
            birth_at='1990-01-01',
            role='seller',
            password='Senha@123'
        )

        self.payment_method = PaymentMethod.objects.create(
            customer=self.customer,
            type='credit_card',
            last4='1234',
            brand='Visa',
            is_default=True
        )

        self.payments_url = '/payments/'
        self.payment_url = f'/payments/{self.payment_method.id}/'

        self.credit_card_data = {
            'type': 'credit_card',
            'last4': '5678',
            'brand': 'Mastercard',
            'is_default': False
        }

        self.pix_data = {
            'type': 'pix',
            'pix_key': 'joao@email.com',
            'is_default': False
        }

    def authenticate_as_customer(self):
        response = self.client.post('/auth/login/', {
            'email': 'customer@email.com',
            'password': 'Senha@123'
        }, format='json')
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def authenticate_as_seller(self):
        response = self.client.post('/auth/login/', {
            'email': 'seller@email.com',
            'password': 'Senha@123'
        }, format='json')
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    # customer pode listar seus métodos
    def test_list_payment_methods(self):
        self.authenticate_as_customer()
        response = self.client.get(self.payments_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    # cadastra cartão de crédito
    def test_create_credit_card(self):
        self.authenticate_as_customer()
        response = self.client.post(self.payments_url, self.credit_card_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['last4'], '5678')

    # cadastra pix
    def test_create_pix(self):
        self.authenticate_as_customer()
        response = self.client.post(self.payments_url, self.pix_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['pix_key'], 'joao@email.com')

    # cartão sem last4
    def test_create_card_without_last4(self):
        self.authenticate_as_customer()
        data = self.credit_card_data.copy()
        data.pop('last4')
        response = self.client.post(self.payments_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # pix sem chave
    def test_create_pix_without_key(self):
        self.authenticate_as_customer()
        data = {'type': 'pix', 'is_default': False}
        response = self.client.post(self.payments_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # last4 não numérico
    def test_create_card_invalid_last4(self):
        self.authenticate_as_customer()
        data = self.credit_card_data.copy()
        data['last4'] = 'abcd'
        response = self.client.post(self.payments_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ao cadastrar novo padrão, desativa o anterior
    def test_new_default_deactivates_old(self):
        self.authenticate_as_customer()
        data = self.credit_card_data.copy()
        data['is_default'] = True
        self.client.post(self.payments_url, data, format='json')
        self.payment_method.refresh_from_db()
        self.assertFalse(self.payment_method.is_default)

    # customer pode deletar seu método
    def test_delete_payment_method(self):
        self.authenticate_as_customer()
        response = self.client.delete(self.payment_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    # customer não pode deletar método de outro customer
    def test_delete_payment_method_of_another_customer(self):
        other_customer = User.objects.create_user(
            email='other@email.com',
            full_name='Other Customer',
            cpf='11122233344',
            phone='84777777777',
            birth_at='1998-01-01',
            role='customer',
            password='Senha@123'
        )
        response = self.client.post('/auth/login/', {
            'email': 'other@email.com',
            'password': 'Senha@123'
        }, format='json')
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.delete(self.payment_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # seller não pode acessar pagamentos
    def test_list_payments_as_seller(self):
        self.authenticate_as_seller()
        response = self.client.get(self.payments_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # não autenticado não pode acessar
    def test_list_payments_unauthenticated(self):
        response = self.client.get(self.payments_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)