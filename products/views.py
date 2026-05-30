from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Product
from .serializers import ProductSerializer

class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.role == 'seller':
            return Product.objects.filter(seller=user)
        
        return Product.objects.filter(is_active=True)
    
    def perform_create(self, serializer):
        if self.request.user.role != 'seller':
            raise PermissionError('Apenas lojistas podem criar produtos')
        serializer.save(seller=self.request.user)

    def perform_update(self, serializer):
        product = self.get_object()
        if product.seller != self.request.user:
            raise PermissionError('Você não tem permissão para editar este produto!')
        serializer.save()

    def perform_destroy(self, instance):
        if instance.seller != self.request.user:
            raise PermissionError('Você não tem permissão para deletar este produto!')
        instance.delete()