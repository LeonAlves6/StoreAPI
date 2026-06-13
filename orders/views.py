from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from .models import Cart, CartItem, Order, OrderItem
from .serializers import CartSerializer, CartItemSerializer, OrderSerializer, CreateOrderSerializer
from rest_framework.pagination import PageNumberPagination
from django.db import transaction
from users.models import Address

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
    
class OrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != 'customer':
            raise PermissionDenied('Apenas clientes podem realizar pedidos')
        
        serializer = CreateOrderSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            address = Address.objects.get(
                id=serializer.validated_data['address_id'],
                user=request.user
            )
            cart = Cart.objects.get(customer=request.user)


            with transaction.atomic():
                total = sum(
                    item.variation.product.price * item.quantity
                    for item in cart.items.all()
                )

                order = Order.objects.create(
                    customer=request.user,
                    total=total,
                    address_street=address.street,
                    address_number=address.number,
                    address_complement=address.complement,
                    address_neighborhood=address.neighborhood,
                    address_city=address.city,
                    address_state=address.state,
                    address_zip_code=address.zip_code,
                )

                for item in cart.items.all():
                    OrderItem.objects.create(
                        order=order,
                        variation=item.variation,
                        quantity=item.quantity,
                        unit_price=item.variation.product.price,
                    )

                    item.variation.stock -= item.quantity
                    item.variation.save()
                
                cart.items.all().delete()

            return Response(
                OrderSerializer(order).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        try:
            if request.user.role == 'customer':
                order = Order.objects.get(id=order_id, customer=request.user)
            else:
                order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response(
                {'error': 'pedido não encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

class OrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'seller':
            raise PermissionDenied('Apenas lojistas podem listar todos os pedidos')

        queryset = Order.objects.all().order_by('created_at')

        status_filter = request.query_params.get('status')

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        paginator = PageNumberPagination()
        paginator.page_size = 10
        page = paginator.paginate_queryset(queryset, request)
        serializer = OrderSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
class OrderStatusView(APIView):
    permission_classes = [IsAuthenticated]

    VALID_TRANSITIONS = {
        'pending':    ['processing', 'cancelled'],
        'processing': ['shipped', 'cancelled'],
        'shipped':    ['delivered'],
        'delivered':  [],  # status final
        'cancelled':  [],  # status final
    }

    def patch(self,request, order_id):
        if request.user.role != 'seller':
            raise PermissionDenied('Apenas lojistas podem atualizar o status de pedidos')
        
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response(
                {'error': 'Pedido não encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        new_status = request.data.get('status')

        if not new_status:
            return Response(
                {'error': 'Status é obrigatório'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        valid_statuses = [choice[0] for choice in Order.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response(
                {'error': f'Status inválido. Valores permitidos: {valid_statuses}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        allowed = self.VALID_TRANSITIONS.get(order.status, [])
        if new_status not in allowed:
            return Response(
                {'error': f'Transição inválida. De "{order.status}" só é permitido ir para: {allowed}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = new_status
        order.save()

        return Response(
            OrderSerializer(order).data,
            status=status.HTTP_200_OK
        )