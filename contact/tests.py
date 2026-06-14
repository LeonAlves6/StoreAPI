from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

class ContactTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/contact/email/'
        self.data = {
            'name': 'João Silva',
            'email': 'joao@email.com',
            'subject': 'Dúvida sobre pedido',
            'message': 'Gostaria de saber o prazo de entrega para Natal/RN.'
        }

    # envio com sucesso
    def test_contact_success(self):
        response = self.client.post(self.url, self.data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Mensagem enviada com sucesso')

    # campos obrigatórios vazios
    def test_contact_missing_fields(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # email inválido
    def test_contact_invalid_email(self):
        data = self.data.copy()
        data['email'] = 'emailinvalido'
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # mensagem muito curta
    def test_contact_short_message(self):
        data = self.data.copy()
        data['message'] = 'Oi'
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # mensagem muito longa
    def test_contact_long_message(self):
        data = self.data.copy()
        data['message'] = 'x' * 1001
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # assunto muito curto
    def test_contact_short_subject(self):
        data = self.data.copy()
        data['subject'] = 'Oi'
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # mensagem salva no banco
    def test_contact_saved_in_database(self):
        from .models import ContactMessage
        self.client.post(self.url, self.data, format='json')
        self.assertEqual(ContactMessage.objects.count(), 1)
        contact = ContactMessage.objects.first()
        self.assertEqual(contact.email, 'joao@email.com')