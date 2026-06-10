from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from users.models import User
from products.models import Category, Product, Variation
from .models import Cart, CartItem
from users.models import Address

class CartTests(TestCase):
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

        self.category = Category.objects.create(name='Camisetas', slug='camisetas')

        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='Camiseta Básica',
            description='Algodão',
            price='59.90',
            is_active=True
        )

        self.variation = Variation.objects.create(
            product=self.product,
            size='M',
            color='Azul',
            stock=10
        )

        self.cart_url = '/cart/'
        self.cart_items_url = '/cart/items/'

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

    # ✅ customer pode ver carrinho
    def test_get_cart_as_customer(self):
        self.authenticate_as_customer()
        response = self.client.get(self.cart_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('items', response.data)
        self.assertIn('total', response.data)

    # ❌ seller não pode acessar carrinho
    def test_get_cart_as_seller(self):
        self.authenticate_as_seller()
        response = self.client.get(self.cart_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ✅ customer pode adicionar item
    def test_add_item_to_cart(self):
        self.authenticate_as_customer()
        response = self.client.post(self.cart_items_url, {
            'variation_id': self.variation.id,
            'quantity': 2
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # ❌ quantidade maior que estoque
    def test_add_item_exceeds_stock(self):
        self.authenticate_as_customer()
        response = self.client.post(self.cart_items_url, {
            'variation_id': self.variation.id,
            'quantity': 999
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ❌ quantidade zero não é permitida
    def test_add_item_zero_quantity(self):
        self.authenticate_as_customer()
        response = self.client.post(self.cart_items_url, {
            'variation_id': self.variation.id,
            'quantity': 0
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ✅ adicionar mesma variação aumenta a quantidade
    def test_add_same_variation_increases_quantity(self):
        self.authenticate_as_customer()
        self.client.post(self.cart_items_url, {
            'variation_id': self.variation.id,
            'quantity': 2
        }, format='json')
        response = self.client.post(self.cart_items_url, {
            'variation_id': self.variation.id,
            'quantity': 3
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['quantity'], 5)

    # ✅ customer pode atualizar quantidade
    def test_update_cart_item(self):
        self.authenticate_as_customer()
        self.client.post(self.cart_items_url, {
            'variation_id': self.variation.id,
            'quantity': 2
        }, format='json')
        cart = Cart.objects.get(customer=self.customer)
        item = CartItem.objects.get(cart=cart)
        response = self.client.put(f'/cart/items/{item.id}/', {
            'quantity': 5
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['quantity'], 5)

    # ✅ customer pode remover item
    def test_delete_cart_item(self):
        self.authenticate_as_customer()
        self.client.post(self.cart_items_url, {
            'variation_id': self.variation.id,
            'quantity': 2
        }, format='json')
        cart = Cart.objects.get(customer=self.customer)
        item = CartItem.objects.get(cart=cart)
        response = self.client.delete(f'/cart/items/{item.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    # ❌ seller não pode adicionar item ao carrinho
    def test_add_item_as_seller(self):
        self.authenticate_as_seller()
        response = self.client.post(self.cart_items_url, {
            'variation_id': self.variation.id,
            'quantity': 1
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ❌ não autenticado não pode acessar carrinho
    def test_get_cart_unauthenticated(self):
        response = self.client.get(self.cart_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class OrderTests(TestCase):
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

        self.category = Category.objects.create(name='Camisetas', slug='camisetas')

        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='Camiseta Básica',
            description='Algodão',
            price='59.90',
            is_active=True
        )

        self.variation = Variation.objects.create(
            product=self.product,
            size='M',
            color='Azul',
            stock=10
        )

        self.address = Address.objects.create(
            user=self.customer,
            street='Rua das Flores',
            number='10',
            neighborhood='Tirol',
            city='Natal',
            state='RN',
            zip_code='59020000',
            is_default=True
        )

        self.orders_url = '/orders/'

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

    def add_item_to_cart(self, quantity=2):
        self.client.post('/cart/items/', {
            'variation_id': self.variation.id,
            'quantity': quantity
        }, format='json')

    # ✅ cria pedido com sucesso
    def test_create_order_success(self):
        self.authenticate_as_customer()
        self.add_item_to_cart()
        response = self.client.post(self.orders_url, {
            'address_id': self.address.id
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'pending')

    # ✅ estoque é subtraído após pedido
    def test_stock_decremented_after_order(self):
        self.authenticate_as_customer()
        self.add_item_to_cart(quantity=3)
        self.client.post(self.orders_url, {
            'address_id': self.address.id
        }, format='json')
        self.variation.refresh_from_db()
        self.assertEqual(self.variation.stock, 7)  # 10 - 3

    # ✅ carrinho limpo após pedido
    def test_cart_cleared_after_order(self):
        self.authenticate_as_customer()
        self.add_item_to_cart()
        self.client.post(self.orders_url, {
            'address_id': self.address.id
        }, format='json')
        cart = Cart.objects.get(customer=self.customer)
        self.assertEqual(cart.items.count(), 0)

    # ❌ carrinho vazio não permite pedido
    def test_create_order_empty_cart(self):
        self.authenticate_as_customer()
        response = self.client.post(self.orders_url, {
            'address_id': self.address.id
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ❌ sem estoque suficiente
    def test_create_order_insufficient_stock(self):
        self.authenticate_as_customer()
        self.add_item_to_cart(quantity=999)
        response = self.client.post(self.orders_url, {
            'address_id': self.address.id
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ❌ seller não pode criar pedido
    def test_create_order_as_seller(self):
        self.authenticate_as_seller()
        response = self.client.post(self.orders_url, {
            'address_id': self.address.id
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ❌ endereço de outro cliente não é permitido
    def test_create_order_with_wrong_address(self):
        self.authenticate_as_customer()
        self.add_item_to_cart()
        response = self.client.post(self.orders_url, {
            'address_id': 99999
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ✅ customer pode ver seu pedido
    def test_get_order_as_customer(self):
        self.authenticate_as_customer()
        self.add_item_to_cart()
        create_response = self.client.post(self.orders_url, {
            'address_id': self.address.id
        }, format='json')
        order_id = create_response.data['id']
        response = self.client.get(f'/orders/{order_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ❌ customer não pode ver pedido de outro cliente
    def test_get_order_of_another_customer(self):
        self.authenticate_as_customer()
        self.add_item_to_cart()
        create_response = self.client.post(self.orders_url, {
            'address_id': self.address.id
        }, format='json')
        order_id = create_response.data['id']

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
        response = self.client.get(f'/orders/{order_id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)