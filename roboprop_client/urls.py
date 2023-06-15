from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("mymodels/", views.mymodels, name="mymodels"),
    path("mymodels/<str:model>/", views.mymodel_detail, name="mymodel_detail"),
    path("find-models/", views.find_models, name="find-models"),
    path("add-to-my-models/", views.add_to_my_models, name="add_to_my_models"),
]
