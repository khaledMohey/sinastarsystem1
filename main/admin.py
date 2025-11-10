from django.contrib import admin
from .models import (
    Product, Material, MaterialHistory, SinastarInventory,
    MenuItem, Recipe, Order, OrderItem, Profile, Officer
)
from django.utils.html import format_html

# =========================
# Inline for Recipes
# =========================
class RecipeInline(admin.TabularInline):
    model = Recipe
    extra = 1
    autocomplete_fields = ["material"]

# =========================
# Menu Item with Recipes
# =========================
@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = (
        "name", "category", "price", "is_active",
        "show_in_cafe", "show_in_takeaway", "show_in_qeta3", "image_tag"
    )
    list_filter = ("category", "is_active", "show_in_cafe", "show_in_takeaway", "show_in_qeta3")
    search_fields = ("name",)
    inlines = [RecipeInline]
    list_editable = ("is_active", "show_in_cafe", "show_in_takeaway", "show_in_qeta3")

    # ✅ لعرض الصورة داخل الـ admin
    def image_tag(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit:cover;border-radius:5px;"/>',
                obj.image.url
            )
        return "❌ لا توجد صورة"
    image_tag.short_description = "Image"

# =========================
# باقي الموديلات
# =========================
@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ("name", "quantity", "created_at")
    search_fields = ("name",)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "order_type", "officer", "table_number", "cashier", "created_at", "is_paid")
    list_filter = ("order_type", "is_paid", "officer", "created_at")
    search_fields = ("id", "officer__name")
    inlines = [OrderItemInline]

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "menuitem", "quantity")
    list_filter = ("menuitem",)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role")
    list_filter = ("role",)

@admin.register(Officer)
class OfficerAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "total_orders")
    search_fields = ("name",)

    def total_orders(self, obj):
        return Order.objects.filter(officer=obj).count()
    total_orders.short_description = "عدد الأوردرات"

admin.site.register(MaterialHistory)
admin.site.register(SinastarInventory)
