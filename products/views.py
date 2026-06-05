from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from .models import Product, Variation
from .serializers import ProductSerializer, VariationSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .filters import ProductFilter

class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'seller':
            return Product.objects.all().order_by('-created_at')
        
        return Product.objects.filter(is_active=True).order_by('-created_at')
    
    def perform_create(self, serializer):
        if self.request.user.role != 'seller':
            raise PermissionDenied('Apenas lojistas podem criar produtos')
        serializer.save(seller=self.request.user)

    def perform_update(self, serializer):
        if self.request.user.role != 'seller':
            raise PermissionDenied('Apenas lojistas podem editar produtos')
        serializer.save()

    def perform_destroy(self, instance):
        if self.request.user.role != 'seller':
            raise PermissionDenied('Apenas lojistas podem deletar produtos')
        instance.delete()

class VariationView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_product(self, product_id):
        try:
            return Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return None
        
    def post(self, request, product_id):
        if request.user.role != 'seller':
            raise PermissionDenied('Apenas lojistas podem criar variações')
        
        product = self._get_product(product_id)
        if not product:
            return Response(
                {'error': 'Produto não encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = VariationSerializer(
            data=request.data,
            context={'product': product}
        )

        if serializer.is_valid():
            serializer.save(product=product)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VariationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_variation(self, variation_id):
        try:
            return Variation.objects.get(id=variation_id)
        except Variation.DoesNotExist:
            return None

    def put(self, request, variation_id):
        if request.user.role != 'seller':
            raise PermissionDenied('Apenas lojistas podem editar variações')

        variation = self._get_variation(variation_id)
        if not variation:
            return Response(
                {'error': 'Variação não encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )

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