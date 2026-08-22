from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('academics/', views.academics, name='academics'),
    path('results/', views.results, name='results'),
    path('about/', views.about, name='about'),
]
