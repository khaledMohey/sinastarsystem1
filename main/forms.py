from django import forms

from .models import SinastarInventory,Order, OrderItem,Material,MenuItem,ExtraExpense
class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ['name', 'quantity']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter material name'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter quantity'}),
        }

class InventoryPasswordForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter Inventory Password'}),
        label="Inventory Password"
    )

class SinastarInventoryForm(forms.ModelForm):
    class Meta:
        model = SinastarInventory
        fields = ['material', 'quantity', 'addition', 'addition_cost', 'purchase_price', 'type']
        widgets = {
            'material': forms.Select(attrs={
                'class': 'form-control'
            }),
            'type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1',
                'min': '0',
                'placeholder': 'Enter quantity'
            }),
            'addition': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1',
                'min': '0',
                'placeholder': 'Enter addition'
            }),
            'addition_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',   # 👈 عشان يسمح بالأرقام العشرية
                'min': '0',
                'placeholder': 'Enter addition cost'
            }),
            'purchase_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',   # 👈 سعر شراء عشري
                'min': '0',
                'placeholder': 'Enter purchase price'
            }),
        }


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["order_type", "table_number", "is_paid"]

class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ["menuitem", "quantity"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # نخلي القائمة تختار بالاسم
        self.fields["menuitem"].queryset = MenuItem.objects.all()
        self.fields["menuitem"].label_from_instance = lambda obj: f"{obj.name} (${obj.price})"



class ExtraExpenseForm(forms.ModelForm):
    class Meta:
        model = ExtraExpense
        fields = ["category", "amount", "note"]
        widgets = {
            "category": forms.Select(attrs={"class": "form-control"}),
            "amount": forms.NumberInput(attrs={"class": "form-control", "placeholder": "المبلغ"}),
            "note": forms.TextInput(attrs={"class": "form-control", "placeholder": "ملاحظة (اختياري)"}),
        }