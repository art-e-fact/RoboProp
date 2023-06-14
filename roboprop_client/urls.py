from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("mymodels/", views.mymodels, name="mymodels"),
    path("mymodels/<str:model>/", views.mymodel_detail, name="mymodel_detail"),
    path("fuel/", views.fuel, name="fuel"),
    path("fuel/<int:page>/", views.fuel, name="fuel"),
]
