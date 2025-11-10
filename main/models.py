from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils.timezone import now
from django.utils import timezone


# -------------------
# Main Product Model
# -------------------
class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    stock = models.IntegerField(default=0)

    def __str__(self):
        return self.name


# -------------------
# Main Inventory
# -------------------
class Material(models.Model):
    name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# -------------------
# History for Main Inventory
# -------------------
class MaterialHistory(models.Model):
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.material.name} -  {self.timestamp}"


# -------------------
# Sinastar Inventory (Branch Inventory)
# -------------------
class SinastarInventory(models.Model):
    TYPE_CHOICES = [
        ('Canteen', 'Canteen'),
        ('mat3am', 'mat3am'),
        ('Baresta', 'Baresta'),
        ('7alak', '7alak'),
        ('shesha', 'shesha'),
    ]

    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)  
    addition = models.PositiveIntegerField(default=0)  
    addition_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    minimum_stock = models.IntegerField(default=0, help_text="الحد الأدنى قبل التنبيه")
    
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)  
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_sale_price(self):
        return self.addition * self.addition_cost

    @property
    def total_purchase_price(self):
        
        return self.addition * self.purchase_price
    @property
    def profit(self):
        return self.total_sale_price - self.total_purchase_price

    def __str__(self):
        return f"{self.material.name} - {self.addition}"




class SinastarInventoryHistory(models.Model):
    TYPE_CHOICES = [
        ('Canteen', 'Canteen'),
        ('mat3am', 'mat3am'),
        ('Baresta', 'Baresta'),
        ("7alak", "7alak"),
        ("shesha", "shesha"),
    ]

    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)   # الكمية الأصلية اللي دخلت
    addition = models.PositiveIntegerField(default=0)   # عدد الوحدات المضافة
    addition_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)  
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)  
    total_purchase_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # ✅ جديد
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)  

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 

    @property
    def total_sale_price(self):
        return self.addition * self.addition_cost

    @property
    def total_purchase_price(self):
        # ✅ نعرض التراكمي
        return self.total_purchase_value

    @property
    def profit(self):
        return self.total_sale_price - self.total_purchase_price

    def __str__(self):
        return f"{self.material.name} - {self.addition}"




# -------------------
# Menu Item
# -------------------
class MenuItem(models.Model):
    CATEGORY_CHOICES = [
        ("food", "Food"),
        ("drink", "Drink"),
        ("7alak", "7alak"),
        ("shesha", "shesha"),
    ]

    SECTION_CHOICES = [
        ("barista", "باريستا"),
        ("mat3am", "مطعم"),
        ("canteen","كانتين"),
        ("7alak", "7alak"),
        ("shesha", "shesha"),
        ("addons","إضافات"),
    ]

    name = models.CharField(max_length=120)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="food")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)  # لو الصنف متوقف أو شغال
    show_in_cafe = models.BooleanField(default=False)
    show_in_takeaway = models.BooleanField(default=False)
    show_in_qeta3 = models.BooleanField(default=False)
    

    # 👇 القسم الجديد
    section = models.CharField(max_length=20, choices=SECTION_CHOICES)
    image = models.ImageField(upload_to="menu_images/", blank=True, null=True)  # ✅ هنا

    def __str__(self):
        return f"{self.name} - {self.get_section_display()} ({self.get_category_display()})"


# --------- Recipes (المكونات لكل صنف) ---------
class Recipe(models.Model):
    menuitem = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name="recipes")
    material = models.ForeignKey("Material", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()  # الكمية المستهلكة من المكون

    def __str__(self):
        return f"{self.menuitem.name} needs {self.quantity} of {self.material.name}"

class Officer(models.Model):
    name = models.CharField(max_length=100)
    discount_rate = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.10,   # 10% افتراضي
        help_text="اكتب النسبة كقيمة عشرية (مثال: 0.10 = 10%, 0.50 = 50%)"
    )

    def __str__(self):
        return self.name

# -------------------
# Order & Order Items
# -------------------
class Order(models.Model):
    ORDER_TYPE_CHOICES = [
        ("cafe", "Cafe"),
        ("takeaway", "Takeaway"),
        ("qeta3", "Qeta3"),
        
    ]
    PAYMENT_CHOICES = [
        ('cash', 'كاش'),
        ('vodafone', 'فودافون كاش'),
        ('moagel', 'مؤجل'),
    ]

    table_number = models.PositiveIntegerField(null=True, blank=True)  # للـ in_cafe
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)

    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cashier = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    officer = models.ForeignKey("Officer", on_delete=models.SET_NULL, null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, blank=True, null=True)
    note = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Order {self.id} - {self.get_order_type_display()}"

    @property
    def subtotal(self):
        return sum(item.total_price for item in self.items.all())

    @property
    def total(self):
        return self.subtotal - self.discount + self.service_charge + self.tax


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menuitem = models.ForeignKey("MenuItem", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    is_done = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.menuitem.name} x {self.quantity}"

    @property
    def total_price(self):
        return self.menuitem.price * self.quantity

    @property
    def section(self):
        # 👇 القسم بيتجاب من الـ MenuItem
        return self.menuitem.section






class Profile(models.Model):
    ROLE_CHOICES = [
        ("barista", "باريستا"),
        ("mat3am", "مطعم"),
        ("waiter", "ويتر"),
        ("admin", "أدمن"),
        ('7alak', 'حلاق'),
        ('shesha', 'شيشة'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)


class MonthlyClosing(models.Model):
    month = models.DateField()  # ممكن تسيبها أو تخليها null لو مش عايزها
    start_date = models.DateField(null=True, blank=True)  # تاريخ البداية
    end_date = models.DateField(null=True, blank=True)    # تاريخ النهاية

    total_sales_orders = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_sales_inventory = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_purchase_inventory = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    profit_from_inventory = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    actual_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # ✅ إضافات جديدة
    total_nesrayat = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_tips = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Closing from {self.start_date} to {self.end_date}"

        

class SoldMaterialHistory(models.Model):
    TYPE_CHOICES = [
        ('Canteen', 'Canteen'),
        ('mat3am', 'mat3am'),
        ('Baresta', 'Baresta'),
        ('7alak', '7alak'),
        ('shesha', 'shesha'),
    ]

    material = models.ForeignKey("Material", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)   # الكمية المطلوبة من الأوردر
    addition = models.PositiveIntegerField(default=0)   # نفس الكمية (كوبي من quantity)
    addition_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # سعر البيع للوحدة
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # سعر الشراء للوحدة
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)  

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_sale_price(self):
        return self.addition * self.addition_cost

    @property
    def total_purchase_price(self):
        return self.addition * self.purchase_price

    @property
    def profit(self):
        return self.total_sale_price - self.total_purchase_price

    def __str__(self):
        return f"{self.material.name} - {self.addition}"


# models.py
class ExtraExpense(models.Model):
    CATEGORY_CHOICES = [
        ("nesrayat", "نسريات"),
        ("tips", "تبس"),
    ]

    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_category_display()} - {self.amount} - {self.created_at.strftime('%Y-%m-%d')}"
