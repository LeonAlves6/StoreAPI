from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, VariationView, VariationDetailView

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='products')

urlpatterns = [
    path('', include(router.urls)),
    path('products/<int:product_id>/variations/', VariationView.as_view(), name='product-variations'),
    path('variations/<int:variation_id>/', VariationDetailView.as_view(), name='variation-detail'),
]