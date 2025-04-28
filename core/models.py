from datetime import timezone
from decimal import Decimal
from django.db import models
from mptt.models import MPTTModel, TreeForeignKey
from django.contrib.auth.models import User
import uuid
from django.utils import timezone


class Category(MPTTModel):
    name = models.CharField(max_length=100)
    parent = TreeForeignKey('self', on_delete=models.CASCADE,
                            null=True, blank=True, related_name='children')
    slug = models.SlugField(unique=True)

    class MPTTMeta:
        order_insertion_by = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    MANDATORY_CHOICES = [
        ('none', 'None'),
        ('size', 'Size'),
        ('color', 'Color'),
        ('both', 'Both'),
    ]
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', default=1)
    available_sizes = models.CharField(max_length=100, blank=True,
                                       help_text="Comma separated list (e.g., S,M,L,XL)")
    available_colors = models.CharField(max_length=100, blank=True,
                                        help_text="Comma separated list (e.g., Red,Blue,Green)")
    mandatory_fields = models.CharField(max_length=10, choices=MANDATORY_CHOICES, default='none')
    stock = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    is_active = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)
    main_image = models.ImageField(upload_to='products/', blank=True, null=True)
    on_sale = models.BooleanField(default=False)
    buying_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0,verbose_name="buying Price")
    sku = models.CharField(max_length=50, unique=True, default='DEFAULT_SKU',verbose_name="Product SKU",
        help_text="Unique stock keeping unit identifier")

    def get_main_image(self):
        """Priority: 1. Explicit main image 2. First ProductImage marked main 3. First image"""
        if self.main_image:
            return self.main_image.url

        main_img = self.images.filter(is_main=True).first()
        if main_img:
            return main_img.image.url

        first_img = self.images.first()
        return first_img.image.url if first_img else None

    def __str__(self):
        return self.name

    def get_main_image_url(self):
        if self.main_image:
            return self.main_image.url
        image = self.images.filter(is_main=True).first()
        if image:
            return image.image.url
        return self.images.first().image.url if self.images.exists() else ''

    @property
    def get_price(self):
        return self.sale_price if self.sale_price else self.price

    def get_size_list(self):
        return [size.strip() for size in self.available_sizes.split(',')] if self.available_sizes else []

    def get_color_list(self):
        return [color.strip() for color in self.available_colors.split(',')] if self.available_colors else []

    def decrease_stock(self, quantity, size='', color=''):
        if self.mandatory_fields == 'both' and not (size and color):
            raise ValueError("Size and color required")

        if self.variants.exists():
            variant = self.variants.get(size=size, color=color)
            if variant.stock < quantity:
                raise ValueError(f"Only {variant.stock} available in {size}/{color}")
            variant.stock -= quantity
            variant.save()
        else:
            if self.stock < quantity:
                raise ValueError(f"Only {self.stock} available")
            self.stock -= quantity
            self.save()


class Wishlist(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    products = models.ManyToManyField(Product)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Wishlist of {self.user or self.session_key}"


class Cart(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    session_key = models.CharField(
        max_length=40,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def items(self):
        return self.cartitem_set.all()  # Or use your actual related name

    def count(self):
        return self.cartitem_set.count()

    @property
    def get_total_price(self):
        return sum(item.total_price for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    size = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=50, blank=True)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'product', 'size', 'color')  # Prevent duplicates

    @property
    def total_price(self):
        if self.product.sale_price:
            return self.quantity * self.product.sale_price
        return self.quantity * self.product.price

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.CharField(max_length=50)
    color = models.CharField(max_length=50)
    stock = models.PositiveIntegerField(default=0)
    sku = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"{self.product.name} - {self.color} / {self.size}"

    class Meta:
        unique_together = ('product', 'size', 'color')


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                                related_name='images')
    image = models.ImageField(upload_to='product_images/')
    is_main = models.BooleanField(default=False)

    def __str__(self):
        return f"Image for {self.product.name}"


class Slider(models.Model):
    image = models.ImageField(upload_to='sliders/')
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=100)

    def __str__(self):
        return self.title


class Coupon(models.Model):
    COUPON_TYPES = (
        ('percentage', 'Percentage'),
        ('flat', 'Flat Amount'),
    )

    code = models.CharField(max_length=50, unique=True)
    coupon_type = models.CharField(max_length=10, choices=COUPON_TYPES)
    discount = models.DecimalField(max_digits=10, decimal_places=2)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    active = models.BooleanField(default=True)
    minimum_purchase = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Minimum cart value required to use this coupon"
    )

    def is_valid(self, cart_total):
        now = timezone.now()
        return (
            self.active and
            self.valid_from <= now <= self.valid_to and
            cart_total >= self.minimum_purchase
        )

    def __str__(self):
        return self.code


class Review(models.Model):
    image = models.ImageField(upload_to='reviews')
    name = models.CharField(max_length=255)
    rating = models.IntegerField()
    text = models.TextField()
    facebook_link = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Order(models.Model):
    PAYMENT_METHODS = (
        ('bkash', 'Bkash'),
        ('nagad', 'Nagad'),
        ('cod', 'Cash on Delivery'),
    )

    ORDER_STATUS = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    order_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='User'
    )
    name = models.CharField(max_length=255)
    address = models.TextField()
    location = models.CharField(max_length=50)
    phone = models.CharField(max_length=20)
    order_channel = models.CharField(max_length=50)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS)
    bkash_trxid = models.CharField(max_length=255, null=True, blank=True)
    nagad_trxid = models.CharField(max_length=255, null=True, blank=True)
    last_four_digits = models.CharField(max_length=4, blank=True, null=True)
    delivery_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=80.00
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=50, choices=ORDER_STATUS, default='pending')
    products = models.ManyToManyField(Product, through='OrderItem')
    coupon = models.ForeignKey(Coupon, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Order {self.id} - {self.user or 'Anonymous'}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    size = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=50, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"


class SalesReport(OrderItem):
    class Meta:
        proxy = True
        verbose_name = 'Sales Report'
        verbose_name_plural = 'Sales Reports'