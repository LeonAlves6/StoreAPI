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