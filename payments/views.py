from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from .models import PaymentMethod
from .serializers import PaymentMethodSerializer

class PaymentMethodView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'customer':
            raise PermissionDenied('Apenas clientes podem acessar métodos de pagamento')
        
        payment_methods = PaymentMethod.objects.filter(
            customer=request.user
        ).order_by('-created_at')

        serializer = PaymentMethodSerializer(payment_methods, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        if request.user.role != 'customer':
            raise PermissionDenied('Apenas clientes podem cadastrar métodos de pagamento')
        
        serializer = PaymentMethodSerializer(data=request.data)
        if serializer.is_valid():
            if request.data.get('is_default'):
                PaymentMethod.objects.filter(
                    customer=request.user,
                    is_default=True
                ).update(is_default=False)

            serializer.save(customer=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PaymentMethodDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_payment_method(self, payment_id, user):
        try:
            return PaymentMethod.objects.get(id=payment_id, customer=user)
        except PaymentMethod.DoesNotExist:
            return None

    def delete(self, request, payment_id):
        if request.user.role != 'customer':
            raise PermissionDenied('Apenas clientes podem remover métodos de pagamento')
        
        payment_method = self._get_payment_method(payment_id, request.user)
        if not payment_method:
            return Response(
                {'error': 'Método de pagamento não encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        payment_method.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)