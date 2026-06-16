from rest_framework import serializers
from .models import PaymentMethod

class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ['id', 'type', 'last4', 'brand', 'pix_key', 'is_default', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def validate(self, data):
        payment_type = data.get('type')

        if payment_type in ['credit_card', 'debit_card']:
            if not data.get('last4'):
                raise serializers.ValidationError({'last4': 'Últimos 4 dígitos são obrigatórios para cartão'})
            if not data.get('brand'):
                raise serializers.ValidationError({'brand': 'Bandeira é obrigatória para cartão'})
            if data.get('pix_key'):
                raise serializers.ValidationError({'pix_key': 'Chave PIX não deve ser informada para cartão'})
        
        if payment_type == 'pix':
            if not data.get('pix_key'):
                raise serializers.ValidationError({'pix_key': 'Chave PIX é obrigatória'})
            if data.get('last4') or data.get('brand'):
                raise serializers.ValidationError({'pix_key': 'Dados de cartão não devem ser informados para PIX'})
            
        return data
    
    def validate_last4(self, value):
        if value and not value.isdigit():
            raise serializers.ValidationError('Últimos 4 dígitos devem ser numéricos')
        return value
    
class PaymentRegisterSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    type = serializers.ChoiceField(choices=['credit_card', 'debit_card', 'pix'])
    card_last_digits = serializers.CharField(required=False)
    card_brand = serializers.CharField(required=False)
    is_default = serializers.BooleanField(default=False)
    created_at = serializers.DateTimeField(read_only=True)

class ErrorResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()