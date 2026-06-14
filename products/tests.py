from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from .models import Category, Product, Variation
from users.models import User

class ProductTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # cria um seller
        self.seller = User.objects.create_user(
            email='seller@email.com',
            full_name='Seller Test',
            cpf='12345678901',
            phone='84999999999',
            birth_at='1990-01-01',
            role='seller',
            password='Senha@123'
        )

        # cria um customer
        self.customer = User.objects.create_user(
            email='customer@email.com',
            full_name='Customer Test',
            cpf='98765432100',
            phone='84888888888',
            birth_at='1995-01-01',
            role='customer',
            password='Senha@123'
        )

        # cria uma categoria
        self.category = Category.objects.create(
            name='Camisetas',
            slug='camisetas'
        )

        # cria um produto
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='Camiseta Básica',
            description='Camiseta 100% algodão',
            price='59.90',
            is_active=True
        )

        # urls
        self.products_url = '/products/'
        self.product_url = f'/products/{self.product.id}/'

        # dados para criar produto
        self.product_data = {
            'name': 'Camiseta Nova',
            'description': 'Descrição da camiseta',
            'price': '79.90',
            'category_id': self.category.id,
            'is_active': True
        }

    def authenticate_as_seller(self):
        # helper para autenticar como seller
        response = self.client.post('/auth/login/', {
            'email': 'seller@email.com',
            'password': 'Senha@123'
        }, format='json')
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def authenticate_as_customer(self):
        # helper para autenticar como customer
        response = self.client.post('/auth/login/', {
            'email': 'customer@email.com',
            'password': 'Senha@123'
        }, format='json')
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    # seller pode criar produto
    def test_create_product_as_seller(self):
        self.authenticate_as_seller()
        response = self.client.post(self.products_url, self.product_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Camiseta Nova')

    # customer não pode criar produto
    def test_create_product_as_customer(self):
        self.authenticate_as_customer()
        response = self.client.post(self.products_url, self.product_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # não autenticado não pode criar produto
    def test_create_product_unauthenticated(self):
        response = self.client.post(self.products_url, self.product_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # preço negativo não é permitido
    def test_create_product_negative_price(self):
        self.authenticate_as_seller()
        data = self.product_data.copy()
        data['price'] = '-10.00'
        response = self.client.post(self.products_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # preço zero não é permitido
    def test_create_product_zero_price(self):
        self.authenticate_as_seller()
        data = self.product_data.copy()
        data['price'] = '0.00'
        response = self.client.post(self.products_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # customer vê apenas produtos ativos
    def test_list_products_as_customer(self):
        self.authenticate_as_customer()
        response = self.client.get(self.products_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for product in response.data['results']:
            self.assertTrue(product['is_active'])

    # seller vê apenas seus próprios produtos
    def test_list_products_as_seller(self):
        self.authenticate_as_seller()
        response = self.client.get(self.products_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
    # não autenticado não pode listar
    def test_list_products_unauthenticated(self):
        response = self.client.get(self.products_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # produto inativo não aparece para customer
    def test_inactive_product_not_visible_to_customer(self):
        self.product.is_active = False
        self.product.save()
        self.authenticate_as_customer()
        response = self.client.get(self.products_url)
        ids = [p['id'] for p in response.data['results']]
        self.assertNotIn(self.product.id, ids)

    # busca produto por id
    def test_get_product_by_id(self):
        self.authenticate_as_customer()
        response = self.client.get(self.product_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Camiseta Básica')

    # produto inexistente retorna 404
    def test_get_nonexistent_product(self):
        self.authenticate_as_customer()
        response = self.client.get('/products/99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    # seller pode editar seu produto
    def test_update_product_as_seller(self):
        self.authenticate_as_seller()
        data = self.product_data.copy()
        data['name'] = 'Camiseta Editada'
        response = self.client.put(self.product_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Camiseta Editada')

    # customer não pode editar produto
    def test_update_product_as_customer(self):
        self.authenticate_as_customer()
        response = self.client.put(self.product_url, self.product_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_product_as_another_seller(self):
    # qualquer seller pode editar qualquer produto
        other_seller = User.objects.create_user(
        email='other@email.com',
        full_name='Other Seller',
        cpf='11122233344',
        phone='84777777777',
        birth_at='1990-01-01',
        role='seller',
        password='Senha@123'
    )
        response = self.client.post('/auth/login/', {
            'email': 'other@email.com',
            'password': 'Senha@123'
        }, format='json')
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.put(self.product_url, self.product_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # seller pode deletar seu produto
    def test_delete_product_as_seller(self):
        self.authenticate_as_seller()
        response = self.client.delete(self.product_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    # customer não pode deletar produto
    def test_delete_product_as_customer(self):
        self.authenticate_as_customer()
        response = self.client.delete(self.product_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

class VariationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.seller = User.objects.create_user(
            email='seller@email.com',
            full_name='Seller Test',
            cpf='12345678901',
            phone='84999999999',
            birth_at='1990-01-01',
            role='seller',
            password='Senha@123'
        )

        self.customer = User.objects.create_user(
            email='customer@email.com',
            full_name='Customer Test',
            cpf='98765432100',
            phone='84888888888',
            birth_at='1995-01-01',
            role='customer',
            password='Senha@123'
        )

        self.category = Category.objects.create(
            name='Camisetas',
            slug='camisetas'
        )

        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='Camiseta Básica',
            description='Camiseta 100% algodão',
            price='59.90',
            is_active=True
        )

        self.variation = Variation.objects.create(
            product=self.product,
            size='M',
            color='Azul',
            stock=10
        )

        self.variations_url = f'/products/{self.product.id}/variations/'
        self.variation_url = f'/variations/{self.variation.id}/'

        self.variation_data = {
            'size': 'G',
            'color': 'Vermelho',
            'stock': 5
        }

    def authenticate_as_seller(self):
        response = self.client.post('/auth/login/', {
            'email': 'seller@email.com',
            'password': 'Senha@123'
        }, format='json')
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def authenticate_as_customer(self):
        response = self.client.post('/auth/login/', {
            'email': 'customer@email.com',
            'password': 'Senha@123'
        }, format='json')
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    # seller pode criar variação
    def test_create_variation_as_seller(self):
        self.authenticate_as_seller()
        response = self.client.post(self.variations_url, self.variation_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # não permite variação duplicada
    def test_create_duplicate_variation(self):
        self.authenticate_as_seller()
        data = {'size': 'M', 'color': 'Azul', 'stock': 5}  # já existe no setUp
        response = self.client.post(self.variations_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # estoque negativo não é permitido
    def test_create_variation_negative_stock(self):
        self.authenticate_as_seller()
        data = self.variation_data.copy()
        data['stock'] = -1
        response = self.client.post(self.variations_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # customer não pode criar variação
    def test_create_variation_as_customer(self):
        self.authenticate_as_customer()
        response = self.client.post(self.variations_url, self.variation_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # seller pode editar variação
    def test_update_variation_as_seller(self):
        self.authenticate_as_seller()
        data = {'size': 'M', 'color': 'Azul', 'stock': 20}
        response = self.client.put(self.variation_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['stock'], 20)

    # customer não pode editar variação
    def test_update_variation_as_customer(self):
        self.authenticate_as_customer()
        response = self.client.put(self.variation_url, self.variation_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # seller pode deletar variação
    def test_delete_variation_as_seller(self):
        self.authenticate_as_seller()
        response = self.client.delete(self.variation_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    # customer não pode deletar variação
    def test_delete_variation_as_customer(self):
        self.authenticate_as_customer()
        response = self.client.delete(self.variation_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # variação inexistente retorna 404
    def test_delete_nonexistent_variation(self):
        self.authenticate_as_seller()
        response = self.client.delete('/variations/99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)