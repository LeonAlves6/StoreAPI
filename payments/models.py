from django.db import models
from users.models import User

class PaymentMethod(models.Model):
    TYPE_CHOICES = [
        ('credit_card', 'Cartão de Crédito'),
        ('debit_card', 'Cartão de Débito'),
        ('pix', 'PIX'),
    ]

    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    last4 = models.CharField(max_length=4, null=True, blank=True)
    brand = models.CharField(max_length=50, null=True, blank=True)

    pix_key = models.CharField(max_length=255, null=True, blank=True)

    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.type == 'pix':
            return f'PIX - {self.pix_key}'
        return f'{self.brand} **** {self.last4}'
    
    class Meta:
        db_table = 'payment_methods'
        verbose_name = 'Método de Pagamento'
        verbose_name_plural = 'Métodos de Pagamento'