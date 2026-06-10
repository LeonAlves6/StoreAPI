from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem
from products.models import Variation
from users.models import Address

class CartItemVariationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    size = serializers.CharField()
    color = serializers.CharField()
    product_name = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()

    def get_product_name(self, obj):
        return obj.product.name
    
    def get_price(self, obj):
        return obj.product.price
    
class CartItemSerializer(serializers.ModelSerializer):
    variation = CartItemVariationSerializer(read_only=True)
    variation_id = serializers.PrimaryKeyRelatedField(
        queryset=Variation.objects.all(),
        source='variation',
        write_only=True
    )
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'variation', 'variation_id', 'quantity', 'subtotal']
    
    def get_subtotal(self, obj):
        return obj.get_subtotal()
    
    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError('Quantidade deve ser maior que zero')
        return value
    
    def validate(self, data):
        variation = data.get('variation')
        quantity = data.get('quantity')

        if variation and quantity:
            if quantity > variation.stock:
                raise serializers.ValidationError(
                    {'quantity': f'Estoque insuficiente. Disponível: {variation.stock}'}
                )
        return data
    
class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total', 'updated_at']

    def get_total(self, obj):
        return obj.get_total()
    
class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='variation.product.name', read_only=True)
    size = serializers.CharField(source='variation.size', read_only=True)
    color = serializers.CharField(source='variation.color', read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'product_name', 'size', 'color', 'quantity', 'unit_price', 'subtotal']

    def get_subtotal(self, obj):
        return obj.get_subtotal()


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'status', 'total', 'items',
            'address_street', 'address_number', 'address_complement',
            'address_neighborhood', 'address_city', 'address_state',
            'address_zip_code', 'created_at'
        ]
        read_only_fields = ['id', 'status', 'total', 'created_at']

class CreateOrderSerializer(serializers.Serializer):
    address_id = serializers.IntegerField()

    def validate_address_id(self, value):
        customer = self.context['request'].user
        try:
            Address.objects.get(id=value, user=customer)
        except Address.DoesNotExist:
            raise serializers.ValidationError('Endreço não encontrado')
        return value
    
    def validate(self, data):
        customer = self.context['request'].user

        try:
            cart = Cart.objects.get(customer=customer)
        except Cart.DoesNotExist:
            raise serializers.ValidationError({'cart': 'Carrinho não encontrado'})
        
        if not cart.items.exists():
            raise serializers.ValidationError({'cart': 'Carrinho está vazio'})
        
        for item in cart.items.all():
            if item.quantity > item.variation.stock:
                raise serializers.ValidationError({
                    'stock': f'Estoque insuficiente para {item.variation.product.name} '
                             f'({item.variation.size}/{item.variation.color}). '
                             f'Disponível: {item.variation.stock}'
                })
            
        return data