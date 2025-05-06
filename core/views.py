import json
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.shortcuts import render, redirect
from .forms import CheckoutForm, ContactForm
from .models import Product, Slider, Coupon, Review, Category
from django.http import JsonResponse, Http404
from django.contrib.auth.decorators import login_required
from .models import Wishlist, Cart, CartItem, Order,OrderItem,ContactMessage
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.db import transaction


def home(request):
    products = Product.objects.all()
    sliders = Slider.objects.all()
    on_sale_products = Product.objects.filter(on_sale=True, is_active=True)
    cart = None

    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()  # Create a new session if it doesn't exist
            session_key = request.session.session_key
        print(f"Session Key: {session_key}")  # Debugging line
        cart = Cart.objects.filter(session_key=session_key, user=None).first()
        print(f"Cart: {cart}")  # Debugging line

    if cart:
        print(f"Cart Items: {cart.items.all()}")  # Debugging line

    context = {
        'sliders': sliders,
        'products': products,
        'on_sale_products': on_sale_products,
        'cart': cart
    }
    return render(request, 'index.html', context)


def quick_view(request, product_id):
    try:
        product = get_object_or_404(Product, id=product_id)

        # Get main image URL
        main_image_url = product.get_main_image_url()
        if main_image_url:
            main_image_url = request.build_absolute_uri(main_image_url)
        else:
            main_image_url = ''

        # Get all images
        other_images = [
            request.build_absolute_uri(img.image.url)
            for img in product.images.all()
        ]

        # Prepare product data
        data = {
            'sku': product.sku,
            'name': product.name,
            'price': "{:.2f}".format(product.price),
            'sale_price': "{:.2f}".format(product.sale_price) if product.sale_price else None,
            'description': product.description,
            'description_parts': product.description.split(','),  # Split the description into parts
            'images': [main_image_url] + other_images,
            'sizes': product.get_size_list(),
            'colors': product.get_color_list(),
            'mandatory': product.mandatory_fields
        }

        return JsonResponse(data)

    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



def return_policy(request):
        return render(request, 'return_policy.html')


def exchange_policy(request):
        return render(request, 'exchange_policy.html')


def shipping_partners(request):
        return render(request, 'shipping_partners.html')


def wishlist(request):
    if request.user.is_authenticated:
        wishlist = get_object_or_404(Wishlist, user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()  # Create a new session if it doesn't exist
            session_key = request.session.session_key
        wishlist, created = Wishlist.objects.get_or_create(session_key=session_key)

    context = {
        'wishlist': wishlist,
        'wishlist_items': wishlist.products.all()
    }
    return render(request, 'wishlist.html', context)


def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # Check if the user is authenticated
    if request.user.is_authenticated:
        wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    else:
        # Handle session key for anonymous users
        session_key = request.session.session_key
        if not session_key:
            request.session.create()  # Create a new session if it doesn't exist
            session_key = request.session.session_key
        wishlist, created = Wishlist.objects.get_or_create(session_key=session_key)

    wishlist.products.add(product)
    return JsonResponse({'count': wishlist.products.count()})


def remove_from_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.user.is_authenticated:
        wishlist = get_object_or_404(Wishlist, user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()  # Create a new session if it doesn't exist
            session_key = request.session.session_key
        wishlist = get_object_or_404(Wishlist, session_key=session_key)

    wishlist.products.remove(product)
    return JsonResponse({'count': wishlist.products.count()})


@require_POST
def add_to_cart(request, product_id):
    try:
        product = get_object_or_404(Product, id=product_id)
        data = json.loads(request.body)

        # Handle cart creation for both authenticated and anonymous users
        if request.user.is_authenticated:
            cart, created = Cart.objects.get_or_create(user=request.user)
        else:
            # Handle session key creation for anonymous users
            if not request.session.session_key:
                request.session.create()
                request.session.save()
            session_key = request.session.session_key
            cart, created = Cart.objects.get_or_create(
                session_key=session_key,
                user=None
            )

        # Validate mandatory fields
        mandatory = product.mandatory_fields
        size = data.get('size', '')
        color = data.get('color', '')
        quantity = int(data.get('quantity', 1))

        # Validation checks
        if quantity < 1:
            return JsonResponse({'success': False, 'message': 'Quantity must be at least 1.'}, status=400)

        if mandatory == 'both' and (not size or not color):
            return JsonResponse({'success': False, 'message': 'Please select both size and color.'}, status=400)
        if mandatory == 'size' and not size:
            return JsonResponse({'success': False, 'message': 'Please select a size.'}, status=400)
        if mandatory == 'color' and not color:
            return JsonResponse({'success': False, 'message': 'Please select a color.'}, status=400)

        # Get or create cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            size=size,
            color=color,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        return JsonResponse({
            'success': True,
            'cart_count': cart.items.count(),
            'message': 'Item added to cart successfully.'
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid data format. Please try again.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': 'An error occurred: ' + str(e)}, status=500)


def cart_view(request):
    # Get or create cart
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        # Handle session key creation properly
        if not request.session.session_key:
            request.session.create()  # Create new session
            request.session.modified = True  # Mark session as modified
            request.session.save()  # Force session save

        session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(
            session_key=session_key,
            user=None
        )

    cart_items = cart.items.all()

    # Calculate cart total using Decimal
    cart_total = sum(Decimal(str(item.total_price)) for item in cart_items)

    # Coupon handling
    discount = Decimal('0.00')
    coupon_code = request.session.get('coupon_code')
    coupon = None

    if coupon_code:
        try:
            coupon = Coupon.objects.get(code=coupon_code)
            if coupon.is_valid(float(cart_total)):
                if coupon.coupon_type == 'percentage':
                    discount = cart_total * (Decimal(str(coupon.discount)) / Decimal('100'))
                else:
                    discount = Decimal(str(coupon.discount))

                # Ensure discount doesn't exceed cart total
                discount = min(discount, cart_total)
            else:
                del request.session['coupon_code']
                coupon = None
                messages.error(request, "Coupon is expired or minimum amount not met")
        except Coupon.DoesNotExist:
            del request.session['coupon_code']

    # Calculate totals with proper decimal handling
    delivery_charge = Decimal('80.00')
    subtotal = (cart_total - discount)
    grand_total = (subtotal + delivery_charge)

    context = {
        'cart_items': cart_items,
        'cart_total': cart_total,
        'discount': discount,
        'subtotal': subtotal,
        'coupon': coupon,
        'delivery_charge': delivery_charge,
        'grand_total': grand_total,
    }
    return render(request, 'cart.html', context)


@require_POST
def apply_coupon(request):
    coupon_code = request.POST.get('coupon_code', '').strip()

    # Check if request is AJAX
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    # Check if coupon is already applied
    if 'coupon_code' in request.session and request.session['coupon_code'] == coupon_code:
        message = "Coupon is already applied"
        if is_ajax:
            return JsonResponse({'success': False, 'message': message})
        messages.info(request, message)
        return redirect('cart')

    try:
        coupon = Coupon.objects.get(code=coupon_code)

        # Get or create cart
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
        else:
            session_key = request.session.session_key
            cart = Cart.objects.filter(session_key=session_key, user=None).first()

        if not cart:
            message = "Your cart is empty"
            if is_ajax:
                return JsonResponse({'success': False, 'message': message})
            messages.error(request, message)
            return redirect('cart')

        # Calculate cart total
        cart_total = sum(item.total_price for item in cart.items.all())

        if coupon.is_valid(float(cart_total)):
            request.session['coupon_code'] = coupon_code
            request.session.modified = True
            message = "Coupon applied successfully!"

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': message,
                    'discount': str(coupon.get_discount_amount(cart_total)),
                    'new_total': str(cart_total - coupon.get_discount_amount(cart_total))
                })
            messages.success(request, message)
        else:
            message = "Coupon is expired or minimum amount not met"
            if 'coupon_code' in request.session:
                del request.session['coupon_code']
                request.session.modified = True
            if is_ajax:
                return JsonResponse({'success': False, 'message': message})
            messages.error(request, message)

    except Coupon.DoesNotExist:
        message = "Invalid coupon code"
        if 'coupon_code' in request.session:
            del request.session['coupon_code']
            request.session.modified = True
        if is_ajax:
            return JsonResponse({'success': False, 'message': message})
        messages.error(request, message)

    return redirect('cart')


def checkout(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Get or create cart
                if request.user.is_authenticated:
                    cart = Cart.objects.filter(user=request.user).first()
                else:
                    session_key = request.session.session_key
                    cart = Cart.objects.filter(session_key=session_key, user=None).first()

                if not cart:
                    messages.error(request, "Your cart is empty")
                    return redirect('cart')

                # Validate required fields
                required_fields = {
                    'name': 'Full name',
                    'address': 'Address',
                    'phone': 'Phone number',
                    'payment_method': 'Payment method'
                }

                missing_fields = [name for field, name in required_fields.items() if not request.POST.get(field)]
                if missing_fields:
                    messages.error(request, f"Missing required fields: {', '.join(missing_fields)}")
                    return redirect('cart')

                # Calculate totals
                cart_items = cart.items.all()
                cart_total = sum(item.total_price for item in cart_items)
                delivery_charge = Decimal(request.POST.get('delivery_charge', '80'))

                # Coupon handling
                coupon = None
                discount_amount = Decimal('0')
                coupon_code = request.session.get('coupon_code')

                if coupon_code:
                    try:
                        coupon = Coupon.objects.get(code=coupon_code)
                        if coupon.is_valid(float(cart_total)):
                            if coupon.coupon_type == 'percentage':
                                discount_amount = cart_total * (coupon.discount / Decimal('100'))
                            else:
                                discount_amount = coupon.discount
                            discount_amount = min(discount_amount, cart_total)
                        else:
                            messages.error(request, "Coupon is not valid for this order")
                            return redirect('cart')
                    except Coupon.DoesNotExist:
                        pass

                # Create order
                order = Order.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    name=request.POST['name'],
                    address=request.POST['address'],
                    location=request.POST.get('location', 'inside'),
                    phone=request.POST['phone'],
                    order_channel=request.POST.get('order_channel', 'website'),
                    payment_method=request.POST['payment_method'],
                    total_amount=cart_total + delivery_charge - discount_amount,
                    delivery_charge=delivery_charge,
                    coupon=coupon,
                    bkash_trxid=request.POST.get('bkash_trxid'),
                    nagad_trxid=request.POST.get('nagad_trxid'),
                    last_four_digits=request.POST.get('last_four_digits')
                )

                # Create order items and reduce stock
                for cart_item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product=cart_item.product,
                        quantity=cart_item.quantity,
                        size=cart_item.size,
                        color=cart_item.color,
                        price=cart_item.product.get_price
                    )

                    # Reduce stock
                    try:
                        cart_item.product.decrease_stock(
                            quantity=cart_item.quantity,
                            size=cart_item.size,
                            color=cart_item.color
                        )
                    except Exception as e:
                        messages.error(request, f"Failed to process {cart_item.product.name}: {str(e)}")
                        return redirect('cart')

                # Clear cart and coupon
                cart.items.all().delete()
                if 'coupon_code' in request.session:
                    del request.session['coupon_code']

                # Redirect to order confirmation page
                return redirect('order_confirmation', order_id=order.order_id)

        except Cart.DoesNotExist:
            messages.error(request, "Your cart is empty")
        except Exception as e:
            messages.error(request, f"Order failed: {str(e)}")

        return redirect('cart')
    return redirect('cart')


def order_confirmation(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)  # Use order_id to query
    context = {
        'order': order,
    }
    return render(request, 'order_confirmation.html', context)


@require_POST
def update_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    size = request.POST.get('size', '')
    color = request.POST.get('color', '')
    action = request.POST.get('action')
    quantity = request.POST.get('quantity')

    try:
        if request.user.is_authenticated:
            # For authenticated users, get or create the cart
            cart, created = Cart.objects.get_or_create(user=request.user)
            # Get or create the cart item
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                size=size,
                color=color,
                defaults={'quantity': 0}
            )
        else:
            # For anonymous users, handle via session_key
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key
            cart, created = Cart.objects.get_or_create(
                session_key=session_key,
                user=None
            )
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                size=size,
                color=color,
                defaults={'quantity': 0}
            )

        # Update the quantity based on the action
        if action == 'increment':
            cart_item.quantity += 1
        elif action == 'decrement':
            cart_item.quantity = max(1, cart_item.quantity - 1)
        elif quantity:
            cart_item.quantity = max(1, int(quantity))

        # Remove item if quantity is 0, otherwise save
        if cart_item.quantity == 0:
            cart_item.delete()
        else:
            cart_item.save()

    except Exception as e:
        messages.error(request, f"Error updating cart: {str(e)}")

    return redirect('cart')


def remove_coupon(request):
    if 'coupon_code' in request.session:
        del request.session['coupon_code']
        request.session.modified = True
    return redirect('cart')


def product_view(request):
    # Get all root categories (top-level categories)
    root_categories = Category.objects.filter(parent=None)

    selected_category_slug = request.GET.get('category')
    products = Product.objects.all()

    if selected_category_slug:
        # Get the selected category and all its descendants
        selected_category = Category.objects.get(slug=selected_category_slug)
        descendants = selected_category.get_descendants(include_self=True)

        # Filter products that belong to any of these categories
        products = products.filter(category__in=descendants)

    # Get cart for both authenticated and anonymous users
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        session_key = request.session.session_key
        cart = Cart.objects.filter(session_key=session_key, user=None).first()

    context = {
        'root_categories': root_categories,
        'all_products': products,
        'selected_category_slug': selected_category_slug,
        'cart': cart,  # Add cart to the context
    }
    return render(request, 'product.html', context)


def review_view(request):
    reviews = Review.objects.all()
    star_range = range(1, 6)
    return render(request, 'reviews.html', {'reviews': reviews, 'star_range': star_range})


@require_POST
def remove_from_cart(request, item_id):
    # Handle both authenticated and anonymous users
    if request.user.is_authenticated:
        # Authenticated: check cart belongs to user
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    else:
        # Anonymous: check session_key and user is None
        session_key = request.session.session_key
        if not session_key:
            raise Http404("No session found.")
        cart_item = get_object_or_404(
            CartItem,
            id=item_id,
            cart__session_key=session_key,
            cart__user=None
        )

    cart_item.delete()
    return redirect('cart')


def featured_products(request):
    featured_items = Product.objects.filter(featured=True)
    return render(request, 'featured.html', {'featured_items': featured_items})


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Save the contact message to the database
            contact_message = ContactMessage(
                name=form.cleaned_data['name'],
                email=form.cleaned_data['email'],
                message=form.cleaned_data['message']
            )
            contact_message.save()  # Save the message

            messages.success(request, 'Your message has been sent successfully!')
            return redirect('contact')  # Redirect to the contact page after submission
    else:
        form = ContactForm()

    return render(request, 'contact.html', {'form': form})