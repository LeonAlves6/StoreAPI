from django.db import models
from users.models import User
from products.models import Variation

# Create your models here.
class Cart(models.Model):
    customer = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Carrinho de {self.customer.full_name}'
    
    def get_total(self):
        return sum(item.get_subtotal() for item in self.items.all())
    
    class Meta:
        db_table = 'carts'
        verbose_name = 'Carrinho'
        verbose_name_plural = 'Carrinhos'

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    variation = models.ForeignKey(Variation, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)

    def get_subtotal(self):
        return self.variation.product.price * self.quantity
    
    def __str__(self):
        return f'{self.quantity}x {self.variation.product.name} ({self.variation.size}/{self.variation.color})'
    
    class Meta:
        db_table = 'cart_items'
        verbose_name = 'Item do Carrinho'
        verbose_name_plural = 'Itens do Carrinho'
        unique_together = ['cart', 'variation']

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('processing', 'Em processamento'),
        ('shipped', 'Enviado'),
        ('delivered', 'Entregue'),
        ('cancelled', 'Cancelado'),
    ]

    customer = models.ForeignKey(User, on_delete=models.PROTECT, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total = models.DecimalField(max_digits=10, decimal_places=2)
    address_street = models.CharField(max_length=255)
    address_number = models.CharField(max_length=10)
    address_complement = models.CharField(max_length=100, null=True, blank=True)
    address_neighborhood = models.CharField(max_length=100)
    address_city = models.CharField(max_length=100)
    address_state = models.CharField(max_length=2)
    address_zip_code = models.CharField(max_length=8)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Pedido #{self.id} - {self.customer.full_name}'
    
    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    variation = models.ForeignKey(Variation, on_delete=models.PROTECT, related_name='order_items')
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def get_subtotal(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f'{self.quantity}X {self.variation.product.name}'

    class Meta:
        db_table = 'order_items'
        verbose_name = 'Item do Pedido'
        verbose_name_plural = 'Itens do Pedido'
