from rest_framework import serializers

def validate_message_length(value):
    if len(value) < 10:
        raise serializers.ValidationError('Mensagem deve ter no mínimo 10 caracteres')
    if len(value) > 1000:
        raise serializers.ValidationError('Mensagem deve ter no máximo 1000 caracteres')
    return value

def validate_subject_length(value):
    if len(value) < 3:
        raise serializers.ValidationError('Assunto deve ter no mínimo 3 caracteres')
    return value