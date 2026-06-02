from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from .models import Product
from .serializers import ProductSerializer

class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

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
        product = self.get_object()
        if product.seller != self.request.user:
            raise PermissionDenied('Você não tem permissão para editar este produto')
        serializer.save()

    def perform_destroy(self, instance):
        if self.request.user.role != 'seller':
            raise PermissionDenied('Apenas lojistas podem deletar produtos')
        if instance.seller != self.request.user:
            raise PermissionDenied('Você não tem permissão para deletar este produto')
        instance.delete()