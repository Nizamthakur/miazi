from django.shortcuts import get_object_or_404
from .models import Product
from .models import CartItem

def cart_contents(request):
    cart = {}  # Initialize cart to an empty dictionary
    cart_items = []
    total = 0
    cart_total = 0  # Initialize cart_total for authenticated users

    if request.user.is_authenticated:
        cart_items = CartItem.objects.filter(cart__user=request.user)
        cart_total = sum(item.product.price * item.quantity for item in cart_items)
    else:
        cart = request.session.get('cart', {})

        # Debugging: Log the contents of the session cart
        print(f"Session Cart: {cart}")

        for item_id, quantity in cart.items():
            # Debugging: Log the item_id and quantity
            print(f"Processing item_id: {item_id}, quantity: {quantity}")

            # Validate item_id
            if not isinstance(item_id, int) and not item_id.isdigit():
                print(f"Invalid item_id: {item_id}")  # Log invalid IDs
                continue  # Skip this iteration if the ID is invalid

            product = get_object_or_404(Product, id=int(item_id))  # Convert to int
            item_total = product.price * quantity
            total += item_total

            cart_items.append({
                'product': product,
                'quantity': quantity,
                'total_price': item_total
            })

    return {
        'cart_items': cart_items,
        'cart_total': total if not request.user.is_authenticated else cart_total
    }