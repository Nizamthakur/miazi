from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Product, Slider, ProductImage, Category,ProductVariant,Coupon, Order, Review, OrderItem, ContactMessage, SalesReport
from mptt.admin import MPTTModelAdmin
from django.utils import timezone
from django.db.models import Sum
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from django.templatetags.static import static

class ReviewAdmin(admin.ModelAdmin):
    list_display = ('name', 'rating')
    search_fields = ('name', 'text')
    list_filter = ('rating',)
    ordering = ('-rating',)

    def image_tag(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="50" height="50" />')
        return "No Image"

    image_tag.short_description = 'Image'


class OrderAdmin(admin.ModelAdmin):
    actions = ['generate_invoice_action']  # Action list remains

    list_display = ('formatted_order_id', 'name', 'payment_method', 'status', 'created_at', 'transaction_info')
    list_filter = ('status', 'payment_method', 'order_channel')
    search_fields = ('order_id', 'name', 'phone')
    readonly_fields = ('order_id', 'created_at', 'updated_at')

    # Existing fieldsets unchanged
    fieldsets = (
        ('Order Information', {
            'fields': ('order_id', 'user', 'status', 'total_amount')
        }),
        ('Customer Details', {
            'fields': ('name', 'address', 'location', 'phone', 'order_channel')
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'bkash_trxid', 'nagad_trxid', 'last_four_digits')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def formatted_order_id(self, obj):
        # Get SKU from the first item in the order (if available)
        if obj.items.exists():
            first_item = obj.items.first()
            sku = first_item.product.sku if first_item.product else "N/A"
        else:
            sku = "N/A"

        # Get order date in DDMM format
        order_date = obj.created_at.strftime('%d%m')

        # Check if order_id is numeric, if not use the UUID and generate a unique order number
        if isinstance(obj.order_id, int):
            order_number = str(obj.order_id).zfill(5)  # Zero pad to 5 digits
        else:
            order_number = str(abs(hash(obj.order_id)) % (10 ** 5)).zfill(
                5)  # Fallback to a hash-based unique ID (5 digits)

        return f"{sku}-{order_date}-{order_number}"

    formatted_order_id.short_description = 'Order ID'

    def transaction_info(self, obj):
        if obj.bkash_trxid:
            return obj.bkash_trxid
        elif obj.nagad_trxid:
            return obj.nagad_trxid
        elif obj.last_four_digits:
            return obj.last_four_digits
        return "."

    transaction_info.short_description = 'Transaction ID'

    # UPDATED INVOICE ACTION METHOD WITH XHTML2PDF
    def generate_invoice_action(self, request, queryset):
        from django.http import HttpResponse
        from django.template.loader import render_to_string
        from xhtml2pdf import pisa  # Changed import
        from io import BytesIO

        for order in queryset:
            order_items = order.items.all()
            subtotal = sum(item.price * item.quantity for item in order_items)

            context = {
                'order': order,
                'formatted_order_id': self.formatted_order_id(order),  # Use admin method here
                'order_items': order_items,
                'subtotal': subtotal,
                'total': order.total_amount,
                'date': timezone.now().strftime("%d %b, %Y"),
                'logo_url': request.build_absolute_uri(static('images/icons/logo1.png')),
            }

            html_string = render_to_string('admin/order_invoice.html', context)

            # Create PDF buffer
            pdf_buffer = BytesIO()

            # Generate PDF using xhtml2pdf
            pisa_status = pisa.CreatePDF(
                html_string,
                dest=pdf_buffer,
                encoding='UTF-8'
            )

            if pisa_status.err:
                return HttpResponse('PDF generation failed', status=500)

            response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="invoice_{order.order_id}.pdf"'
            pdf_buffer.close()
            return response  # Returns first PDF for multiple selections

    generate_invoice_action.short_description = "Generate PDF invoice for selected orders"


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'coupon_type', 'discount', 'valid_from', 'valid_to', 'active')
    search_fields = ('code',)
    list_filter = ('active', 'coupon_type')


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline, ProductVariantInline]
    list_display = ['name', 'sku', 'on_sale', 'buying_price', 'price', 'sale_price', 'featured']
    list_filter = ['on_sale', 'category', 'featured']
    search_fields = ['name', 'sku']


@admin.register(Slider)
class SliderAdmin(admin.ModelAdmin):
    list_display = ['title', 'subtitle']  # Fields to display in the list view


class CategoryAdmin(MPTTModelAdmin):
    list_display = ('name', 'slug', 'parent')
    prepopulated_fields = {'slug': ('name',)}
    mptt_level_indent = 20  # For better visual hierarchy


class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'created_at')
    search_fields = ('name', 'email')


@admin.register(SalesReport)
class SalesReportAdmin(admin.ModelAdmin):
    change_list_template = 'admin/sales_report.html'
    list_display = ()  # Hide default list

    def has_add_permission(self, request):
        return False  # Disable adding new entries

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        # Aggregate data
        daily_sales = OrderItem.objects.annotate(
            date=TruncDate('order__created_at')
        ).values('date').annotate(
            total_quantity=Sum('quantity'),
            total_sales=Sum('price')
        ).order_by('-date')

        weekly_sales = OrderItem.objects.annotate(
            week=TruncWeek('order__created_at')
        ).values('week').annotate(
            total_quantity=Sum('quantity'),
            total_sales=Sum('price')
        ).order_by('-week')

        monthly_sales = OrderItem.objects.annotate(
            month=TruncMonth('order__created_at')
        ).values('month').annotate(
            total_quantity=Sum('quantity'),
            total_sales=Sum('price')
        ).order_by('-month')

        product_sales = OrderItem.objects.values(
            'product__name', 'product__sku'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_sales=Sum('price')
        ).order_by('-total_quantity')

        extra_context.update({
            'daily_sales': daily_sales,
            'weekly_sales': weekly_sales,
            'monthly_sales': monthly_sales,
            'product_sales': product_sales,
        })

        return super().changelist_view(request, extra_context=extra_context)


admin.site.register(Order, OrderAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(ProductImage)
admin.site.register(Review, ReviewAdmin)
admin.site.register(ContactMessage, ContactMessageAdmin)
