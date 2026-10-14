from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("cart/", views.cart_detail, name="cart"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/item/<int:item_id>/update/", views.update_cart_item, name="update_item"),
    path("cart/item/<int:item_id>/remove/", views.remove_cart_item, name="remove_item"),
    path("checkout/", views.checkout, name="checkout"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
        path("orders/", views.order_list, name="order_list"),
]
