# views.py — App: contact
# Responsável pelo envio de mensagens de contato para a plataforma.
# Qualquer pessoa pode enviar uma mensagem (não requer autenticação).
# A mensagem é salva no banco para histórico e enviada por email de forma assíncrona.

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from django.conf import settings
import threading
from .serializers import ContactSerializer
from drf_spectacular.utils import extend_schema, OpenApiExample, inline_serializer

def send_contact_email_async(name, email, subject, message):
    """
    Envia o email de contato de forma assíncrona em uma thread separada.
    Isso evita que o cliente precise aguardar o tempo de resposta do servidor
    de email para receber a confirmação da API.

    Em caso de falha no envio, o erro é logado no console mas não propaga
    para a requisição — a mensagem já foi salva no banco, então não se perde.

    Parâmetros:
        name    (str): Nome do remetente informado no formulário
        email   (str): Email do remetente informado no formulário
        subject (str): Assunto da mensagem
        message (str): Conteúdo da mensagem
    """
    try:
        send_mail(
            subject=f'[Contato] {subject}',
            message=f'Nome: {name}\nEmail: {email}\n\nMensagem:\n{message}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.CONTACT_EMAIL],
            fail_silently=False,
        )
    except Exception as e:
        # Loga o erro sem interromper o fluxo da aplicação
        # A mensagem já foi salva no banco, então não há perda de dados
        print(f'Erro ao enviar email: {e}')

# ─────────────────────────────────────────────
# ContactView
# POST /contact/email/
# Recebe uma mensagem de contato, salva no banco e envia por email.
# Não requer autenticação — qualquer pessoa pode entrar em contato.
# ─────────────────────────────────────────────
class ContactView(APIView):
    @extend_schema(
        request=ContactSerializer
    )

    def post(self, request):
        # O serializer valida:
        # - Campos obrigatórios: name, email, subject, message
        # - Formato válido do email
        # - Tamanho mínimo (10 chars) e máximo (1000 chars) da mensagem
        # - Tamanho mínimo (3 chars) do assunto
        serializer = ContactSerializer(data=request.data)
        if serializer.is_valid():

            # Salva a mensagem no banco de dados para histórico
            # Isso garante que nenhuma mensagem seja perdida mesmo
            # que o envio de email falhe
            contact = serializer.save()

            # Dispara o envio de email em uma thread separada
            # para não bloquear a resposta da API
            thread = threading.Thread(
                target=send_contact_email_async,
                args=(
                    contact.name,
                    contact.email,
                    contact.subject,
                    contact.message,
                )
            )
            thread.start()

            # Retorna confirmação imediatamente sem aguardar o envio do email
            return Response(
                {'message': 'Mensagem enviada com sucesso'},
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)