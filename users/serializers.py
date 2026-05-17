from rest_framework import serializers
from .models import User
import re

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'full_name', 'cpf', 'email', 'phone', 'birth_at', 'role', 'password']

    def validate_cpf(self, value):
        cpf = re.sub(r'\D', '', value)

        if len(cpf) != 11:
            raise serializers.ValidationError('CPF deve ter 11 dígitos')
    
        if cpf == cpf[0] * 11:
            raise serializers.ValidationError('CPF inválido')

        return cpf

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError('A senha deve conter pelo menos 8 caracteres')
        
        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError('A senha deve conter pelo menos uma letra maiúscula')
        
        if not re.search(r'[a-z]', value):
            raise serializers.ValidationError('A senha deve conter pelo menos uma letra minúscula')
        
        if not re.search(r'[0-9]', value):
            raise serializers.ValidationError('Senha deve ter pelo menos um número')

        if not re.search(r'[!@#$%^&*(),.?]', value):
            raise serializers.ValidationError('Senha deve ter pelo menos um caractere especial')

        return value

    def validate_phone(self, value):
        phone = re.sub(r'\D', '', value)

        if len(phone) not in [10, 11]:
            raise serializers.ValidationError('Telefone inválido')
        
        return phone

    def validate_role(self, value):
        if value not in ['customer', 'seller']:
            raise serializers.ValidationError('Role inválido')
        
        return value

    def validate(self, data):
        if User.objects.filter(email=data.get('email')).exists():
            raise serializers.ValidationError({'email': 'Email já cadastrado'})

        if User.objects.filter(cpf=data.get('cpf')).exists():
            raise serializers.ValidationError({'cpf': 'CPF já cadastrado'})

        return data

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()

        return user
    
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        return value.lower()
