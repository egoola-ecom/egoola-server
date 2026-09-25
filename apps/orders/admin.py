from django.contrib import admin

from .models import Address, Cart, CartItem, Order, OrderItem, Payment


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "buyer")
    inlines = [CartItemInline]


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "phone", "addressable_type", "addressable_id", "city")
    list_filter = ("addressable_type",)
    search_fields = ("name", "phone", "address_line1")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "order_type", "buyer", "seller", "status", "total", "commission_amount")
    list_filter = ("order_type", "status")
    inlines = [OrderItemInline, PaymentInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "purpose", "user_id", "user_type", "direction", "amount", "status")
    list_filter = ("purpose", "user_type", "direction", "status")
