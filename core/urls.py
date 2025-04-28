from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('return-policy/', views.return_policy, name='return_policy'),
    path('exchange-policy/', views.exchange_policy, name='exchange_policy'),
    path('shipping-partners/', views.shipping_partners, name='shipping_partners'),
    path('products/<int:product_id>/quick-view/', views.quick_view, name='quick_view'),
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_view, name='cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('update-cart/<int:product_id>/', views.update_cart, name='update_cart'),
    path('apply-coupon/', views.apply_coupon, name='apply_coupon'),
    path('remove-coupon/', views.remove_coupon, name='remove_coupon'),
    path('order-confirmation/<uuid:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('products/', views.product_view, name='product_view'),
    path('reviews/', views.review_view, name='reviews'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('featured/', views.featured_products, name='featured_products'),
    path('contact/', views.contact, name='contact'),

]