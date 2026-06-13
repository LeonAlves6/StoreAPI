from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from django.conf import settings
import threading
from .serializers import ContactSerializer

def send_contact_email_async(name, email, subject, message):
    try:
        send_mail(
            subject=f'[Contato] {subject}',
            message=f'Nome: {name}\nEmail: {email}\n\nMensagem:\n{message}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.CONTACT_EMAIL],
            fail_silently=False,
        )
    except Exception as e:
        print(f'Erro ao enviar email: {e}')

class ContactView(APIView):
    def post(self, request):
        serializer = ContactSerializer(data=request.data)
        if serializer.is_valid():

            contact = serializer.save()

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

            return Response(
                {'message': 'Mensagem enviada com sucesso'},
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)