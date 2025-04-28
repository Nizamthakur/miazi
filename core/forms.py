from django import forms
from django.core.validators import RegexValidator

class CheckoutForm(forms.Form):
    name = forms.CharField(max_length=100)
    address = forms.CharField(widget=forms.Textarea)
    LOCATION_CHOICES = [
        ('inside', 'Inside Dhaka (+৳80)'),
        ('outside', 'Outside Dhaka (+৳150)'),
    ]
    location = forms.ChoiceField(choices=LOCATION_CHOICES)
    phone = forms.CharField(
        validators=[RegexValidator(r'^01\d{9}$', 'Enter a valid 11 digit phone number.')]
    )
    ORDER_CHANNEL_CHOICES = [
        ('website', 'Website'),
        ('facebook', 'Facebook'),
        ('whatsapp', 'WhatsApp'),
        ('tiktok', 'TikTok'),
    ]
    order_channel = forms.ChoiceField(choices=ORDER_CHANNEL_CHOICES)
    PAYMENT_CHOICES = [
        ('bkash', 'Bkash'),
        ('nagad', 'Nagad'),
        ('cod', 'Cash on Delivery'),
    ]
    payment_method = forms.ChoiceField(choices=PAYMENT_CHOICES)
    transaction_id = forms.CharField(required=False, max_length=4)

class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, required=True, label='Your Name')
    email = forms.EmailField(required=True, label='Your Email')
    message = forms.CharField(widget=forms.Textarea, required=True, label='Your Message')

