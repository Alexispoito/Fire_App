from django.urls import path
from . import views

urlpatterns = [
    # Add your boat-related routes here
    path('', views.boat_list, name='boat_list'),
]
