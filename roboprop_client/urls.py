from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("find-models/", views.find_models, name="find-models"),
    path("add-to-my-models/", views.add_to_my_models, name="add_to_my_models"),
    path("login", views.login, name="login"),
    path("logout", views.logout, name="logout"),
    path("mymodels/", views.mymodels, name="mymodels"),
    path("mymodels/<str:name>/", views.mymodel_detail, name="mymodel_detail"),
    path("myrobots/", views.myrobots, name="myrobots"),
    path("myrobots/<str:name>/", views.myrobot_detail, name="myrobot_detail"),
    path("add-metadata/<str:name>/", views.add_metadata, name="add_metadata"),
    path(
        "update-models-from-blenderkit/",
        views.update_models_from_blenderkit,
        name="update_models_from_blenderkit",
    ),
    path("task-status/<str:task_id>/", views.task_status, name="task_status")
]
