from rest_framework import serializers

def validate_positive_price(value):
    if value <= 0:
        raise serializers.ValidationError('Preço deve ser maior que zero')
    return value

def validate_positive_stock(value):
    if value < 0:
        raise serializers.ValidationError('Estoque não pode ser negativo')
    return value