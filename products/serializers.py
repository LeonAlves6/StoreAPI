from rest_framework import serializers
from .models import Category, Product, Variation

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']

class VariationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Variation
        fields = ['id', 'size', 'color', 'stock']

class ProductSerializer(serializers.ModelSerializer):
    variations = VariationSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True
    )

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'is_active', 'category', 'category_id', 'variations', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError('Preço deve ser maior que zero!')
        return value