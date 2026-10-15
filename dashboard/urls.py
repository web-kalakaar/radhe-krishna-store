from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.overview, name="overview"),
    path("orders/", views.order_list, name="order_list"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/deliver/", views.order_deliver, name="order_deliver"),
    path("orders/<int:pk>/cancel/", views.order_cancel, name="order_cancel"),
        path("stock/", views.stock_list, name="stock_list"),
    path("stock/<int:pk>/adjust/", views.stock_adjust, name="stock_adjust"),
        path("stock/history/", views.stock_history, name="stock_history"),
]