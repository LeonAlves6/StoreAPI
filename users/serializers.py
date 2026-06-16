from rest_framework import serializers
from .models import User, Address
from .validators import validate_password_strength, validate_cpf, validate_phone

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password_strength])
    cpf = serializers.CharField(validators=[validate_cpf])
    phone = serializers.CharField(validators=[validate_phone])
    class Meta:
        model = User
        fields = ['id', 'full_name', 'cpf', 'email', 'phone', 'birth_at', 'role', 'password']

    def validate_role(self, value):
        if value not in ['customer']:
            raise serializers.ValidationError('Role inválido')
        return value

    def validate(self, data):
        if User.objects.filter(email=data.get('email')).exists():
            raise serializers.ValidationError({'email': 'Email já cadastrado'})

        if User.objects.filter(cpf=data.get('cpf')).exists():
            raise serializers.ValidationError({'cpf': 'CPF já cadastrado'})

        return data
    
    def validate_birth_at(self, value):
        from datetime import date
        if value > date.today():
            raise serializers.ValidationError('Data de nascimento não pode ser no futuro')
        return value

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

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.lower()
    
class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, validators=[validate_password_strength])

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            'id',
            'street',
            'number',
            'complement',
            'neighborhood',
            'city',
            'state',
            'zip_code',
            'is_default',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def validate_state(self, value):
        if len(value) != 2:
            raise serializers.ValidationError('Estado deve ter 2 caracteres (UF)')
        return value.upper()

    def validate_zip_code(self, value):
        if not value.isdigit() or len(value) != 8:
            raise serializers.ValidationError('CEP deve conter 8 dígitos numéricos')
        return value

class ErrorResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()

class MessageResponseSerializer(serializers.Serializer):
    message = serializers.CharField()