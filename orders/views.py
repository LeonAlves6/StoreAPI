from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer

class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'customer':
            raise PermissionDenied('Apenas clientes podem acessar o carrinho')
        
        cart, _ = Cart.objects.get_or_create(customer=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class CartItemView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != 'customer':
            raise PermissionDenied('Apenas clientes podem adicionar itens ao carrinho')
        cart, _ = Cart.objects.get_or_create(customer=request.user)

        variation_id = request.data.get('variation_id')
        existing_item = CartItem.objects.filter(
            cart=cart,
            variation_id=variation_id
        ).first()

        if existing_item:
            new_quantity = existing_item.quantity + request.data.get('quantity', 1)
            serializer = CartItemSerializer(
                existing_item,
                data={'variation_id': variation_id, 'quantity': new_quantity},
                partial=True
            )
        else:
            serializer = CartItemSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(cart=cart)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CartItemDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_item(self, item_id, user):
        try:
            return CartItem.objects.get(id=item_id, cart__customer=user)
        except CartItem.DoesNotExist:
            return None
    
    def put(self, request, item_id):
        if request.user.role != 'customer':
            raise PermissionDenied('Apenas clientes podem atualizar itens do carrinho')
        
        item = self._get_item(item_id, request.user)
        if not item:
            return Response(
                {'error': 'Item não encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = CartItemSerializer(item, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, item_id):
        if request.user.role != 'customer':
            raise PermissionDenied('Apenas clientes podem remover itens do carrinho')
        
        item = self._get_item(item_id, request.user)
        if not item:
            return Response(
                {'error': 'Item não encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)