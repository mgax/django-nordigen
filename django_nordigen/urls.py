from django.urls import path

from . import views

app_name = "nordigen"

urlpatterns = [
    path("redirect", views.redirect, name="redirect"),
]
