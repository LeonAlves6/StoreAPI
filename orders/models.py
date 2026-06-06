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