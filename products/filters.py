import django_filters
from .models import Product

class ProductFilter(django_filters.FilterSet):

    #filtro por nome
    name = django_filters.CharFilter(lookup_expr='icontains')

    #filtro por categoria
    category = django_filters.NumberFilter(field_name='category__id')
    category_slug = django_filters.CharFilter(field_name='category__slug', lookup_expr='iexact')
    category_name = django_filters.CharFilter(field_name='category__name', lookup_expr='icontains')

    #filtro por faixa de preço
    price_min = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = django_filters.NumberFilter(field_name='price', lookup_expr='lte')

    #filtro por tamanho
    size = django_filters.CharFilter(field_name='variation__size', lookup_expr='iexact')

    #filtro por cor
    color = django_filters.CharFilter(field_name='variations__color', lookup_expr='icontains')

    class Meta:
        model = Product
        fields = ['name', 'category', 'category_slug', 'category_name', 'price_min', 'price_max', 'size', 'color']