# views.py — App: products
# Responsável pelo gerenciamento de produtos e variações (tamanho/cor/estoque).
# Dois atores operam aqui:
#   - Lojista (seller): cria, edita e remove produtos e variações
#   - Cliente (customer): lista e busca produtos ativos com filtros

from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from .models import Product, Variation
from .serializers import ProductSerializer, VariationSerializer, VariationRegisterSerializer, ErrorResponseSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, OpenApiExample
from .filters import ProductFilter

# ─────────────────────────────────────────────
# ProductViewSet
# GET    /products/       — lista produtos
# POST   /products/       — cria produto
# GET    /products/:id/   — detalha produto
# PUT    /products/:id/   — atualiza produto
# PATCH  /products/:id/   — atualiza produto parcialmente
# DELETE /products/:id/   — remove produto
#
# O ModelViewSet implementa automaticamente os 5 métodos CRUD.
# Apenas os hooks perform_create/update/destroy foram sobrescritos
# para aplicar a verificação de role.
# ─────────────────────────────────────────────
class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    # Habilita filtragem por campos definidos em ProductFilter,
    # busca textual por ?search= e ordenação por ?ordering=
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at']
    ordering = ['-created_at']

    @extend_schema(
        summary='Cria um novo produto',
        description=(
            'Cria um produto associado ao lojista autenticado. '
            '**Restrito a lojistas** (`role=seller`). '
            'O preço deve ser maior que zero. '
            'As variações (tamanho/cor/estoque) são gerenciadas separadamente '
            'via `POST /products/:id/variations/`.'
        ),
        request=ProductSerializer,
        examples=[
            OpenApiExample(
                'Criar produto',
                value={
                    'name': 'Camiseta Básica',
                    'description': 'Camiseta 100% algodão',
                    'price': '59.90',
                    'category_id': 1,
                    'is_active': True
                },
                request_only=True
            ),
            OpenApiExample(
                'Produto criado',
                value={
                    'id': 1,
                    'name': 'Camiseta Básica',
                    'description': 'Camiseta 100% algodão',
                    'price': '59.90',
                    'is_active': True,
                    'category': {'id': 1, 'name': 'Camisetas', 'slug': 'camisetas'},
                    'variations': [],
                    'created_at': '2026-06-13T10:00:00Z'
                },
                response_only=True,
                status_codes=['201']
            ),
            OpenApiExample(
                'Preço inválido',
                value={'price': ['Preço deve ser maior que zero']},
                response_only=True,
                status_codes=['400']
            ),
            OpenApiExample(
                'Sem permissão',
                value={'detail': 'Apenas lojistas podem criar produtos'},
                response_only=True,
                status_codes=['403']
            ),
        ],
        responses={201: ProductSerializer, 400: None, 401: None, 403: None},
    )

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user

        # Lojistas veem todos os produtos (ativos e inativos)
        # pois precisam gerenciar inclusive produtos desativados
        if user.role == 'seller':
            return Product.objects.all().order_by('-created_at')
        
        # Clientes veem apenas produtos ativos
        return Product.objects.filter(is_active=True).order_by('-created_at')
    
    
    def perform_create(self, serializer):
        # Apenas lojistas podem criar produtos
        # O seller é associado automaticamente ao produto sem precisar
        # ser informado no body da requisição
        if self.request.user.role != 'seller':
            raise PermissionDenied('Apenas lojistas podem criar produtos')
        serializer.save(seller=self.request.user)

    def perform_update(self, serializer):
        # Qualquer lojista pode editar qualquer produto da loja
        # pois os sellers são funcionários da loja, não donos individuais
        if self.request.user.role != 'seller':
            raise PermissionDenied('Apenas lojistas podem editar produtos')
        serializer.save()

    def perform_destroy(self, instance):
        # Qualquer lojista pode remover qualquer produto da loja
        if self.request.user.role != 'seller':
            raise PermissionDenied('Apenas lojistas podem deletar produtos')
        instance.delete()

# ─────────────────────────────────────────────
# VariationView
# POST /products/:id/variations/
# Cria uma nova variação (combinação de tamanho e cor) para um produto.
# Restrito a lojistas.
# ─────────────────────────────────────────────
class VariationView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_product(self, product_id):
        """
        Helper que busca um produto pelo ID.
        Retorna o objeto Product ou None se não encontrado.
        Centraliza o tratamento de DoesNotExist para evitar repetição.
        """
        try:
            return Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return None

    @extend_schema(
        summary='Acrescentar variação ao produto',
        description=(
            'Acrescenta variação de tamanho e cores ao produto'
            'Não pode repetir variação para o mesmo produto'
        ),
        request=VariationRegisterSerializer,
        responses={
            201: VariationSerializer,
            400: ErrorResponseSerializer,
            401: ErrorResponseSerializer
        },
        examples=[
            OpenApiExample(
                'Cartão de crédito',
                value={
                    "size": "M",
                    "color": "Azul",
                    "stock": 5
                },
                request_only=True
            ),
        ]
    )
        
    def post(self, request, product_id):
        # Apenas lojistas podem criar variações
        if request.user.role != 'seller':
            raise PermissionDenied('Apenas lojistas podem criar variações')
        
        # Busca o produto pai ao qual a variação será associada
        product = self._get_product(product_id)
        if not product:
            return Response(
                {'error': 'Produto não encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # O produto é passado via context para o serializer poder
        # validar a unicidade da combinação size+color dentro deste produto
        serializer = VariationSerializer(
            data=request.data,
            context={'product': product}
        )

        if serializer.is_valid():
            # Associa a variação ao produto na hora de salvar
            serializer.save(product=product)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ─────────────────────────────────────────────
# VariationDetailView
# PUT    /variations/:id/ — atualiza variação
# DELETE /variations/:id/ — remove variação
# Restrito a lojistas.
# ─────────────────────────────────────────────
class VariationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_variation(self, variation_id):
        """
        Helper que busca uma variação pelo ID.
        Retorna o objeto Variation ou None se não encontrado.
        """
        try:
            return Variation.objects.get(id=variation_id)
        except Variation.DoesNotExist:
            return None

    def put(self, request, variation_id):
        # Apenas lojistas podem editar variações
        if request.user.role != 'seller':
            raise PermissionDenied('Apenas lojistas podem editar variações')

        variation = self._get_variation(variation_id)
        if not variation:
            return Response(
                {'error': 'Variação não encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )

        # O produto pai é passado via context para que o serializer
        # valide a unicidade de size+color excluindo a própria variação
        # que está sendo editada (para não conflitar consigo mesma)
        serializer = VariationSerializer(
            variation,
            data=request.data,
            context={'product': variation.product}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, variation_id):
        # Apenas lojistas podem remover variações
        if request.user.role != 'seller':
            raise PermissionDenied('Apenas lojistas podem deletar variações')

        variation = self._get_variation(variation_id)
        if not variation:
            return Response(
                {'error': 'Variação não encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        variation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)