# views.py — App: orders
# Responsável pelo gerenciamento de carrinho e pedidos.
# Dois atores operam aqui:
#   - Cliente (customer): gerencia o próprio carrinho e realiza pedidos
#   - Lojista (seller): lista todos os pedidos e atualiza o status deles

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from .models import Cart, CartItem, Order, OrderItem
from .serializers import CartSerializer, CartItemSerializer, OrderSerializer, CreateOrderSerializer
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema, OpenApiExample, inline_serializer
from rest_framework import serializers as drf_serializers
from django.db import transaction
from users.models import Address

# ─────────────────────────────────────────────
# CartView
# GET /cart/
# Retorna o carrinho do cliente autenticado com itens e total.
# Restrito a clientes (role=customer).
# ─────────────────────────────────────────────
class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Apenas clientes possuem carrinho
        if request.user.role != 'customer':
            raise PermissionDenied('Apenas clientes podem acessar o carrinho')
        
        # get_or_create garante que o carrinho existe antes de retorná-lo
        # Se o cliente ainda não tiver um carrinho, ele é criado vazio
        cart, _ = Cart.objects.get_or_create(customer=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    # ─────────────────────────────────────────────
# CartItemView
# POST /cart/items/
# Adiciona um item ao carrinho do cliente autenticado.
# Se a variação já estiver no carrinho, a quantidade é somada (não duplicada).
# Restrito a clientes (role=customer).
# ─────────────────────────────────────────────
class CartItemView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Adiciona um item ao carrinho',
        description=(
            'Adiciona uma variação de produto ao carrinho do cliente autenticado. '
            '**Restrito a clientes** (`role=customer`). '
            'Se a variação já estiver no carrinho, a quantidade é **somada** '
            '(ex: já tem 2 → adiciona 3 → fica 5). '
            'A quantidade total não pode exceder o estoque disponível.'
        ),
        request=CartItemSerializer,
        examples=[
            OpenApiExample(
                'Adicionar item',
                value={'variation_id': 1, 'quantity': 2},
                request_only=True
            ),
            OpenApiExample(
                'Item adicionado',
                value={
                    'id': 1,
                    'variation': {
                        'id': 1,
                        'size': 'M',
                        'color': 'Azul',
                        'product_name': 'Camiseta Básica',
                        'price': '59.90'
                    },
                    'quantity': 2,
                    'subtotal': '119.80'
                },
                response_only=True,
                status_codes=['201']
            ),
            OpenApiExample(
                'Estoque insuficiente',
                value={'quantity': ['Estoque insuficiente. Disponível: 10']},
                response_only=True,
                status_codes=['400']
            ),
            OpenApiExample(
                'Quantidade zero',
                value={'quantity': ['Quantidade deve ser maior que zero']},
                response_only=True,
                status_codes=['400']
            ),
        ],
        responses={201: CartItemSerializer, 400: None, 401: None, 403: None},
    )

    def post(self, request):
        # Apenas clientes podem manipular o carrinho
        if request.user.role != 'customer':
            raise PermissionDenied('Apenas clientes podem adicionar itens ao carrinho')
        
        # Obtém ou cria o carrinho do cliente antes de adicionar o item
        cart, _ = Cart.objects.get_or_create(customer=request.user)

        variation_id = request.data.get('variation_id')

        # Verifica se a variação já existe no carrinho para evitar duplicatas
        existing_item = CartItem.objects.filter(
            cart=cart,
            variation_id=variation_id
        ).first()

        if existing_item:
            # Se o item já existe, soma a nova quantidade à existente
            # Em vez de criar um novo registro duplicado
            new_quantity = existing_item.quantity + request.data.get('quantity', 1)
            serializer = CartItemSerializer(
                existing_item,
                data={'variation_id': variation_id, 'quantity': new_quantity},
                partial=True
            )
        else:
            # Item novo: cria um registro completo no carrinho
            serializer = CartItemSerializer(data=request.data)

        if serializer.is_valid():
            # O carrinho é associado ao item na hora de salvar,
            # não precisa ser enviado no body da requisição
            serializer.save(cart=cart)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ─────────────────────────────────────────────
# CartItemDetailView
# PUT    /cart/items/:id/ — atualiza quantidade de um item
# DELETE /cart/items/:id/ — remove um item do carrinho
# Restrito ao cliente dono do carrinho (role=customer).
# ─────────────────────────────────────────────
class CartItemDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_item(self, item_id, user):
        """
        Helper que busca um item do carrinho pelo ID, garantindo que
        ele pertença ao carrinho do usuário autenticado.
        O filtro cart__customer=user impede que um cliente acesse
        ou modifique itens do carrinho de outro cliente.
        Retorna o CartItem ou None se não encontrado ou não autorizado.
        """
        try:
            return CartItem.objects.get(id=item_id, cart__customer=user)
        except CartItem.DoesNotExist:
            return None
    
    def put(self, request, item_id):
        # Apenas clientes podem atualizar itens do próprio carrinho
        if request.user.role != 'customer':
            raise PermissionDenied('Apenas clientes podem atualizar itens do carrinho')
        
        # O helper já garante que o item pertence ao cliente autenticado
        item = self._get_item(item_id, request.user)
        if not item:
            return Response(
                {'error': 'Item não encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # partial=True permite atualizar só a quantidade sem exigir variation_id
        serializer = CartItemSerializer(item, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, item_id):
        # Apenas clientes podem remover itens do próprio carrinho
        if request.user.role != 'customer':
            raise PermissionDenied('Apenas clientes podem remover itens do carrinho')
        
        # O helper já garante que o item pertence ao cliente autenticado
        item = self._get_item(item_id, request.user)
        if not item:
            return Response(
                {'error': 'Item não encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
# ─────────────────────────────────────────────
# OrderView
# POST /orders/
# Converte o carrinho em um pedido.
# Valida estoque, subtrai as quantidades, registra snapshot do endereço
# e esvazia o carrinho — tudo dentro de uma única transação atômica.
# Restrito a clientes (role=customer).
# ─────────────────────────────────────────────
class OrderView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Cria um pedido a partir do carrinho',
        description=(
            'Finaliza a compra convertendo os itens do carrinho em um pedido. '
            '**Restrito a clientes** (`role=customer`). '
            'O carrinho não pode estar vazio. '
            'O endereço informado deve pertencer ao cliente autenticado. '
            'O estoque é subtraído automaticamente e o carrinho é esvaziado. '
            'O pedido é criado com status `pending`.'
        ),
        request=CreateOrderSerializer,
        examples=[
            OpenApiExample(
                'Criar pedido',
                value={'address_id': 1},
                request_only=True
            ),
            OpenApiExample(
                'Pedido criado',
                value={
                    'id': 1,
                    'status': 'pending',
                    'total': '119.80',
                    'items': [
                        {
                            'id': 1,
                            'product_name': 'Camiseta Básica',
                            'size': 'M',
                            'color': 'Azul',
                            'quantity': 2,
                            'unit_price': '59.90',
                            'subtotal': '119.80'
                        }
                    ],
                    'address_street': 'Rua das Flores',
                    'address_number': '10',
                    'address_complement': None,
                    'address_neighborhood': 'Tirol',
                    'address_city': 'Natal',
                    'address_state': 'RN',
                    'address_zip_code': '59020000',
                    'created_at': '2026-06-13T10:00:00Z'
                },
                response_only=True,
                status_codes=['201']
            ),
            OpenApiExample(
                'Carrinho vazio',
                value={'cart': ['Carrinho está vazio']},
                response_only=True,
                status_codes=['400']
            ),
            OpenApiExample(
                'Estoque insuficiente',
                value={'stock': ['Estoque insuficiente para Camiseta Básica (M/Azul). Disponível: 1']},
                response_only=True,
                status_codes=['400']
            ),
            OpenApiExample(
                'Endereço inválido',
                value={'address_id': ['Endereço não encontrado']},
                response_only=True,
                status_codes=['400']
            ),
        ],
        responses={201: OrderSerializer, 400: None, 401: None, 403: None},
    )

    def post(self, request):
        # Apenas clientes podem realizar pedidos
        if request.user.role != 'customer':
            raise PermissionDenied('Apenas clientes podem realizar pedidos')
        
        # CreateOrderSerializer valida:
        # - se o address_id pertence ao cliente autenticado
        # - se o carrinho não está vazio
        # - se há estoque suficiente para cada item
        serializer = CreateOrderSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            # Busca o endereço validado para copiar os dados para o pedido
            address = Address.objects.get(
                id=serializer.validated_data['address_id'],
                user=request.user
            )
            cart = Cart.objects.get(customer=request.user)

            # transaction.atomic garante que todas as operações abaixo
            # são executadas como uma unidade: se qualquer etapa falhar,
            # nenhuma alteração é persistida no banco (tudo ou nada)
            with transaction.atomic():
                # Calcula o total somando preço * quantidade de cada item
                total = sum(
                    item.variation.product.price * item.quantity
                    for item in cart.items.all()
                )

                # Cria o pedido com snapshot do endereço
                # O endereço é copiado campo a campo para preservar o histórico:
                # se o cliente alterar o endereço depois, o pedido mantém o endereço original
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

                # Para cada item do carrinho, cria um OrderItem e subtrai o estoque
                for item in cart.items.all():
                    # unit_price é salvo no momento da compra para preservar o histórico:
                    # se o preço do produto mudar depois, o pedido mantém o preço original
                    OrderItem.objects.create(
                        order=order,
                        variation=item.variation,
                        quantity=item.quantity,
                        unit_price=item.variation.product.price,
                    )

                    # Subtrai a quantidade comprada do estoque da variação
                    item.variation.stock -= item.quantity
                    item.variation.save()

                # Esvazia o carrinho após a criação bem-sucedida do pedido
                cart.items.all().delete()

            return Response(
                OrderSerializer(order).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
# ─────────────────────────────────────────────
# OrderDetailView
# GET /orders/:id/
# Retorna os dados completos de um pedido.
# Cliente: só vê seus próprios pedidos.
# Lojista: pode ver qualquer pedido.
# ─────────────────────────────────────────────
class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        try:
            if request.user.role == 'customer':
                # Clientes só podem visualizar seus próprios pedidos
                # O filtro customer=request.user garante o isolamento
                order = Order.objects.get(id=order_id, customer=request.user)
            else:
                # Lojistas e admins podem visualizar qualquer pedido
                order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response(
                {'error': 'pedido não encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

# ─────────────────────────────────────────────
# OrderListView
# GET /orders/list/
# Lista todos os pedidos da loja com suporte a filtro por status e paginação.
# Ordenados do mais antigo para o mais novo (conforme UC09).
# Restrito a lojistas (role=seller).
# ─────────────────────────────────────────────
class OrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Apenas lojistas têm acesso à listagem completa de pedidos
        if request.user.role != 'seller':
            raise PermissionDenied('Apenas lojistas podem listar todos os pedidos')

        # Ordena do mais antigo para o mais novo para que lojistas
        # atendam os pedidos na ordem de chegada (FIFO)
        queryset = Order.objects.all().order_by('created_at')

        # Filtro opcional por status via query param: ?status=pending
        status_filter = request.query_params.get('status')

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Paginação manual com 10 pedidos por página
        paginator = PageNumberPagination()
        paginator.page_size = 10
        page = paginator.paginate_queryset(queryset, request)
        serializer = OrderSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
# ─────────────────────────────────────────────
# OrderStatusView
# PATCH /orders/:id/status/
# Atualiza o status de um pedido seguindo um fluxo válido de transições.
# Transições permitidas:
#   pending → processing | cancelled
#   processing → shipped | cancelled
#   shipped → delivered
#   delivered → (estado final, sem transições)
#   cancelled → (estado final, sem transições)
# Restrito a lojistas (role=seller).
# ─────────────────────────────────────────────
class OrderStatusView(APIView):
    permission_classes = [IsAuthenticated]

    # Mapa de transições válidas: chave é o status atual,
    # valor é a lista de status para os quais é permitido avançar
    VALID_TRANSITIONS = {
        'pending':    ['processing', 'cancelled'],
        'processing': ['shipped', 'cancelled'],
        'shipped':    ['delivered'],
        'delivered':  [],  # status final
        'cancelled':  [],  # status final
    }

    @extend_schema(
        summary='Atualiza o status de um pedido',
        description=(
            'Atualiza o status de um pedido seguindo o fluxo válido de transições. '
            '**Restrito a lojistas** (`role=seller`). '
            '\n\n**Fluxo permitido:**\n'
            '- `pending` → `processing` ou `cancelled`\n'
            '- `processing` → `shipped` ou `cancelled`\n'
            '- `shipped` → `delivered`\n'
            '- `delivered` e `cancelled` são **estados finais** — não podem ser alterados.'
        ),
        request=inline_serializer(
            name='OrderStatusRequest',
            fields={
                'status': drf_serializers.ChoiceField(
                    choices=['pending', 'processing', 'shipped', 'delivered', 'cancelled']
                )
            }
        ),
        examples=[
            OpenApiExample(
                'Avançar para processando',
                value={'status': 'processing'},
                request_only=True
            ),
            OpenApiExample(
                'Cancelar pedido',
                value={'status': 'cancelled'},
                request_only=True
            ),
            OpenApiExample(
                'Status atualizado',
                value={
                    'id': 1,
                    'status': 'processing',
                    'total': '119.80',
                    'created_at': '2026-06-13T10:00:00Z'
                },
                response_only=True,
                status_codes=['200']
            ),
            OpenApiExample(
                'Transição inválida',
                value={'error': 'Transição inválida. De "pending" só é permitido ir para: [\'processing\', \'cancelled\']'},
                response_only=True,
                status_codes=['400']
            ),
            OpenApiExample(
                'Status inexistente',
                value={'error': 'Status inválido. Valores permitidos: [\'pending\', \'processing\', \'shipped\', \'delivered\', \'cancelled\']'},
                response_only=True,
                status_codes=['400']
            ),
            OpenApiExample(
                'Pedido não encontrado',
                value={'error': 'Pedido não encontrado'},
                response_only=True,
                status_codes=['404']
            ),
        ],
        responses={200: OrderSerializer, 400: None, 401: None, 403: None, 404: None},
    )

    def patch(self,request, order_id):
        # Apenas lojistas podem alterar o status de pedidos
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

        # O campo status é obrigatório no body da requisição
        if not new_status:
            return Response(
                {'error': 'Status é obrigatório'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Extrai os valores válidos do choices do model Order
        valid_statuses = [choice[0] for choice in Order.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response(
                {'error': f'Status inválido. Valores permitidos: {valid_statuses}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verifica se a transição do status atual para o novo é permitida
        # Consulta o mapa VALID_TRANSITIONS com o status atual do pedido
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