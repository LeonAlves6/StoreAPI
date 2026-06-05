from django.db import models
from users.models import User
from autoslug import AutoSlugField

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name='Nome')
    slug = models.SlugField(unique=True, verbose_name='Slug')

    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'categories'
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'

class Product(models.Model):
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    slug = AutoSlugField(populate_from='name', unique=True, always_update=True, null=True, blank=True)
    name = models.CharField(max_length=255, verbose_name='Nome')
    description = models.TextField(verbose_name='Descrição')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Preço')
    is_active = models.BooleanField(default=True, verbose_name='Ativo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'products'
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'

class Variation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variations')
    size = models.CharField(max_length=10, verbose_name='Tamanho')
    color = models.CharField(max_length=50, verbose_name='Cor')
    stock = models.PositiveIntegerField(default=0, verbose_name='Estoque')

    def __str__(self):
        return f'{self.product.name} - {self.size} - {self.color}'
    
    class Meta:
        db_table = 'variations'
        verbose_name = 'Variação'
        verbose_name_plural = 'Variações'
        unique_together = ['product', 'size', 'color']