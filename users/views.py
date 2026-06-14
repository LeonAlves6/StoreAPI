# views.py — App: users
# Responsável por toda a lógica de autenticação e gerenciamento de usuários:
# registro, login, recuperação de senha e controle de papéis (roles).

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from users.models import User
from .serializers import RegisterSerializer, LoginSerializer, ForgotPasswordSerializer, ResetPasswordSerializer
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from drf_spectacular.utils import extend_schema, OpenApiExample
import secrets

# ─────────────────────────────────────────────
# UpdateUserRoleView
# PATCH /auth/users/<user_id>/role/
# Permite que um admin altere o papel (role) de qualquer usuário.
# Apenas usuários com role='admin' têm acesso a este endpoint.
# ─────────────────────────────────────────────
class UpdateUserRoleView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, user_id):
        # Apenas admins podem alterar papéis de outros usuários
        if request.user.role != 'admin':
            raise PermissionDenied('Apenas admins podem alterar roles')
        
        # Busca o usuário alvo pelo UUID informado na URL
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'Usuário não encontrado'}, status=status.HTTP_404_NOT_FOUND)
        
        # Valida que o novo papel é 'customer' ou 'seller'
        # O papel 'admin' não pode ser atribuído por este endpoint
        new_role = request.data.get('role')
        if new_role not in ['customer', 'seller']:
            return Response({'error': 'Role inválido'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.role = new_role
        user.save()

        return Response({'message': f'Role atualizado para {new_role}'}, status=status.HTTP_200_OK)
    
# ─────────────────────────────────────────────
# RegisterView
# POST /auth/register/
# Permite que qualquer pessoa crie uma conta na plataforma.
# O papel padrão no cadastro público é 'customer'.
# ─────────────────────────────────────────────
class RegisterView(APIView):
    @extend_schema(
        summary='Cadastra um novo usuário',
        description=(
            'Cria uma conta na plataforma. '
            'O campo `role` aceita apenas `customer` no cadastro público. '
            'A promoção para `seller` é feita por um admin via `PATCH /auth/users/:id/role/`. '
            'A senha deve ter no mínimo 8 caracteres, '
            'uma letra maiúscula, uma minúscula, um número e um caractere especial (`!@#$%^&*(),.?`).'
        ),
        request=RegisterSerializer,
        examples=[
            OpenApiExample(
                'Cadastro de cliente',
                value={
                    'full_name': 'João Silva',
                    'cpf': '13297456043',
                    'email': 'joao@email.com',
                    'phone': '84999999999',
                    'birth_at': '2000-01-01',
                    'role': 'customer',
                    'password': 'Senha@123'
                },
                request_only=True
            ),
            OpenApiExample(
                'Usuário criado com sucesso',
                value={
                    'message': 'Usuário criado com sucesso',
                    'user': {
                        'id': '947dffff-889f-4069-b488-98bb512c1f81',
                        'full_name': 'João Silva',
                        'email': 'joao@email.com',
                        'role': 'customer'
                    }
                },
                response_only=True,
                status_codes=['201']
            ),
            OpenApiExample(
                'Email já cadastrado',
                value={'email': ['Email já cadastrado']},
                response_only=True,
                status_codes=['400']
            ),
            OpenApiExample(
                'Senha fraca',
                value={'password': ['A senha deve conter pelo menos uma letra maiúscula']},
                response_only=True,
                status_codes=['400']
            ),
        ],
        responses={201: None, 400: None},
    )
    def post(self, request):
        # Passa os dados recebidos para o serializer, que valida
        # CPF, email único, força da senha, formato do telefone e role
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            # O serializer cria o usuário já com a senha hasheada via set_password()
            user = serializer.save()
            return Response({
                'message': 'Usuário criado com sucesso',
                'user': {
                    'id': str(user.id),
                    'full_name': user.full_name,
                    'email': user.email,
                    'role': user.role,
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
# ─────────────────────────────────────────────
# LoginView
# POST /auth/login/
# Autentica o usuário com email e senha.
# Retorna um par de tokens JWT: access (curta duração) e refresh (longa duração).
# ─────────────────────────────────────────────
class LoginView(APIView):
    @extend_schema(
        summary='Realiza login e retorna tokens JWT',
        description=(
            'Autentica o usuário com email e senha. '
            'Retorna um `access` token (curta duração) e um `refresh` token (longa duração). '
            'Use o `access` no header `Authorization: Bearer <token>` em todas as requisições autenticadas. '
            'Quando expirar, use o `refresh` em `POST /auth/token/refresh/` para renovar sem fazer login novamente.'
        ),
        request=LoginSerializer,
        examples=[
            OpenApiExample(
                'Credenciais válidas',
                value={
                    'email': 'joao@email.com',
                    'password': 'Senha@123'
                },
                request_only=True
            ),
            OpenApiExample(
                'Login bem-sucedido',
                value={
                    'access': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                    'refresh': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
                },
                response_only=True,
                status_codes=['200']
            ),
            OpenApiExample(
                'Credenciais inválidas',
                value={'error': 'Email ou senha inválidos'},
                response_only=True,
                status_codes=['401']
            ),
        ],
        responses={200: None, 400: None, 401: None},
    )
    def post(self, request):
        # Valida o formato dos dados de entrada (email e senha obrigatórios)
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            # authenticate() verifica as credenciais contra o banco
            # e retorna o objeto User se válidas, ou None se inválidas
            user = authenticate(request, username=email, password=password)

            if user is None:
                return Response({'error': 'Email ou senha inválidos'},
                    status=status.HTTP_401_UNAUTHORIZED)
            
            # Gera o par de tokens JWT para o usuário autenticado
            # O access token é usado nas requisições autenticadas
            # O refresh token é usado para renovar o access quando ele expirar
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ─────────────────────────────────────────────
# ForgotPasswordView
# POST /auth/forgot-password/
# Inicia o fluxo de recuperação de senha enviando um token por email.
# Por segurança, sempre retorna a mesma resposta independente do email existir ou não,
# evitando que atacantes descubram quais emails estão cadastrados (enumeração de usuários).
# ─────────────────────────────────────────────
class ForgotPasswordView(APIView):
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']

            # Mensagem genérica usada em todos os casos (email existe ou não)
            # Isso previne enumeração de usuários por timing ou conteúdo da resposta
            response_message = {'message': 'Se o email estiver cadastrado, você receberá um link de redefinição'}

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                # Retorna 200 mesmo quando o email não existe
                # para não revelar se o email está ou não cadastrado
                return Response(response_message, status=status.HTTP_200_OK)
            
            # Gera um token criptograficamente seguro de 32 bytes
            token = secrets.token_urlsafe(32)
            user.reset_token = token

            # Define expiração de 1 hora a partir do momento atual
            user.reset_token_expires = timezone.now() + timedelta(hours=1)
            user.save()

            # Envia o token por email para que o usuário possa redefinir a senha
            # Em desenvolvimento, o email é exibido no console (EMAIL_BACKEND=console)
            send_mail(
                subject='Redefinição de senha',
                message=f'Use o token abaixo para redefinir sua senha:\n\n{token}\n\nO token expira em 1 hora.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
            )

            return Response(response_message, status=status.HTTP_200_OK)
    
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
# ─────────────────────────────────────────────
# ResetPasswordView
# POST /auth/reset-password/
# Conclui o fluxo de recuperação de senha.
# Recebe o token enviado por email e a nova senha.
# Após uso bem-sucedido, o token é invalidado imediatamente.
# ─────────────────────────────────────────────
class ResetPasswordView(APIView):
    def post(self, request):
        # O serializer valida o token (campo obrigatório) e a força da nova senha
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            token = serializer.validated_data['token']
            password = serializer.validated_data['password']

            # Busca o usuário pelo token de recuperação
            try:
                user = User.objects.get(reset_token=token)
            except User.DoesNotExist:
                return Response(
                    {'error': 'Token inválido'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Verifica se o token ainda está dentro do prazo de 1 hora
            if user.reset_token_expires < timezone.now():
                return Response(
                    {'error': 'Token expirado'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Atualiza a senha com hash e invalida o token
            # Definir reset_token como None garante que o mesmo token
            # não possa ser reutilizado em uma segunda tentativa
            user.set_password(password)
            user.reset_token = None
            user.reset_token_expires = None
            user.save()

            return Response(
                {'message': 'Senha redefinida com sucesso'},
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)