import re
from rest_framework import serializers


def validate_password_strength(value):
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

def validate_cpf(value):
    cpf = re.sub(r'\D', '', value)

    if len(cpf) != 11:
        raise serializers.ValidationError('CPF deve ter 11 dígitos')

    if cpf == cpf[0] * 11:
        raise serializers.ValidationError('CPF inválido')

    return cpf

def validate_phone(value):
    phone = re.sub(r'\D', '', value)

    if len(phone) not in [10, 11]:
        raise serializers.ValidationError('Telefone inválido')

    return phone