from rest_framework import serializers
from .models import Cart, CartItem
from products.models import Variation

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