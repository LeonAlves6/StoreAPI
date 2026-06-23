from django.urls import path
from .views import index, Portfolio

urlpatterns = [
    path('home', index, name="home"),
    path('portfolio', Portfolio, name="portfolio"),
]