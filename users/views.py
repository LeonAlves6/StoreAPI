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
import secrets

class UpdateUserRoleView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, user_id):
        if request.user.role != 'admin':
            raise PermissionDenied('Apenas admins podem alterar roles')
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'Usuário não encontrado'}, status=status.HTTP_404_NOT_FOUND)
        
        new_role = request.data.get('role')
        if new_role not in ['customer', 'seller']:
            return Response({'error': 'Role inválido'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.role = new_role
        user.save()

        return Response({'message': f'Role atualizado para {new_role}'}, status=status.HTTP_200_OK)
class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
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
    
class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            user = authenticate(request, username=email, password=password)

            if user is None:
                return Response({'error': 'Email ou senha inválidos'},
                    status=status.HTTP_401_UNAUTHORIZED)
            
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ForgotPasswordView(APIView):
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']

            # por segurança, sempre retorna a mesma mensagem
            response_message = {'message': 'Se o email estiver cadastrado, você receberá um link de redefinição'}

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response(response_message, status=status.HTTP_200_OK)
            
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expires = timezone.now() + timedelta(hours=1)
            user.save()

            send_mail(
                subject='Redefinição de senha',
                message=f'Use o token abaixo para redefinir sua senha:\n\n{token}\n\nO token expira em 1 hora.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
            )

            return Response(response_message, status=status.HTTP_200_OK)
    
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ResetPasswordView(APIView):
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            token = serializer.validated_data['token']
            password = serializer.validated_data['password']

            try:
                user = User.objects.get(reset_token=token)
            except User.DoesNotExist:
                return Response(
                    {'error': 'Token inválido'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # verifica se o token expirou
            if user.reset_token_expires < timezone.now():
                return Response(
                    {'error': 'Token expirado'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # atualiza a senha e invalida o token
            user.set_password(password)
            user.reset_token = None
            user.reset_token_expires = None
            user.save()

            return Response(
                {'message': 'Senha redefinida com sucesso'},
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)