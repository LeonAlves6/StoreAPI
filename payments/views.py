# views.py — App: payments
# Responsável pelo gerenciamento de métodos de pagamento dos clientes.
# Apenas clientes (role=customer) têm acesso a este app.
# Cada cliente só pode visualizar e remover seus próprios métodos —
# o isolamento é garantido pelo filtro customer=request.user nas queries.

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from .models import PaymentMethod
from .serializers import PaymentMethodSerializer

# ─────────────────────────────────────────────
# PaymentMethodView
# GET  /payments/ — lista métodos de pagamento do cliente
# POST /payments/ — cadastra novo método de pagamento
# Restrito a clientes (role=customer).
# ─────────────────────────────────────────────
class PaymentMethodView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Apenas clientes podem acessar métodos de pagamento
        if request.user.role != 'customer':
            raise PermissionDenied('Apenas clientes podem acessar métodos de pagamento')
        
        # Filtra apenas os métodos do cliente autenticado,
        # garantindo que um cliente nunca veja dados de outro
        payment_methods = PaymentMethod.objects.filter(
            customer=request.user
        ).order_by('-created_at')

        serializer = PaymentMethodSerializer(payment_methods, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        # Apenas clientes podem cadastrar métodos de pagamento
        if request.user.role != 'customer':
            raise PermissionDenied('Apenas clientes podem cadastrar métodos de pagamento')
        
        # O serializer valida as regras por tipo:
        # - credit_card/debit_card: requer last4 e brand, não aceita pix_key
        # - pix: requer pix_key, não aceita last4 nem brand
        serializer = PaymentMethodSerializer(data=request.data)
        if serializer.is_valid():
            # Se o novo método vai ser o padrão (is_default=True),
            # desativa o método padrão anterior para garantir que
            # apenas um método seja o padrão por vez
            if request.data.get('is_default'):
                PaymentMethod.objects.filter(
                    customer=request.user,
                    is_default=True
                ).update(is_default=False)

            # O cliente é associado ao método na hora de salvar,
            # não precisa ser enviado no body da requisição
            serializer.save(customer=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ─────────────────────────────────────────────
# PaymentMethodDetailView
# DELETE /payments/:id/
# Remove um método de pagamento do cliente autenticado.
# Restrito ao dono do método (role=customer).
# ─────────────────────────────────────────────
class PaymentMethodDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_payment_method(self, payment_id, user):
        """
        Helper que busca um método de pagamento pelo ID garantindo que
        ele pertença ao cliente autenticado.
        O filtro customer=user impede que um cliente acesse ou remova
        métodos de pagamento de outro cliente.
        Retorna o PaymentMethod ou None se não encontrado ou não autorizado.
        """
        try:
            return PaymentMethod.objects.get(id=payment_id, customer=user)
        except PaymentMethod.DoesNotExist:
            return None

    def delete(self, request, payment_id):
        # Apenas clientes podem remover métodos de pagamento
        if request.user.role != 'customer':
            raise PermissionDenied('Apenas clientes podem remover métodos de pagamento')
        
        # O helper já garante que o método pertence ao cliente autenticado
        payment_method = self._get_payment_method(payment_id, request.user)
        if not payment_method:
            return Response(
                {'error': 'Método de pagamento não encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        payment_method.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)