from django.urls import path
from .views import PaymentMethodView, PaymentMethodDetailView

urlpatterns = [
    path('payments/', PaymentMethodView.as_view(), name='payments'),
    path('payments/<int:payment_id>/', PaymentMethodDetailView.as_view(), name='payment-detail'),
]