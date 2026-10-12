from django.urls import path

from . import views

app_name = "store"

urlpatterns = [
    path("", views.home, name="home"),
    path("category/<slug:slug>/", views.category_detail, name="category_detail"),
        path("product/<slug:slug>/", views.product_detail, name="product_detail"),
]