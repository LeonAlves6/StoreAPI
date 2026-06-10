from django.urls import path
from .views import CartView, CartItemView, CartItemDetailView, OrderView, OrderDetailView

urlpatterns = [
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/items/', CartItemView.as_view(), name='cart-items'),
    path('cart/items/<int:item_id>/', CartItemDetailView.as_view(), name='cart-item-detail'),
    path('orders/', OrderView.as_view(), name='orders'),
    path('orders/<int:order_id>/', OrderDetailView.as_view(), name='order-detail'),
]