from rest_framework import serializers
from .models import Category, Product, Variation
from .validators import validate_positive_price, validate_positive_stock

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']

class VariationSerializer(serializers.ModelSerializer):
    stock = serializers.IntegerField(validators=[validate_positive_stock])

    class Meta:
        model = Variation
        fields = ['id', 'size', 'color', 'stock']

    def validate(self, data):
        product = self.context.get('product')
        size = data.get('size')
        color = data.get('color')

        if product:
            queryset = Variation.objects.filter(
                product=product,
                size=size,
                color=color
            )
            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)

            if queryset.exists():
                raise serializers.ValidationError(
                    {'variation': f'Variação {size} + {color} já existe para este produto'}
                )

        return data

class ProductSerializer(serializers.ModelSerializer):
    variations = VariationSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True
    )
    price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[validate_positive_price]
    )

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'is_active', 'category', 'category_id', 'variations', 'created_at']
        read_only_fields = ['id', 'created_at']
    
class VariationRegisterSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    size = serializers.ChoiceField(choices=['P', 'M', 'G'])
    color = serializers.CharField()
    stock = serializers.IntegerField()

class ErrorResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()