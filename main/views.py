from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from .models import Product, Material, MaterialHistory,SinastarInventory,MenuItem, Recipe, Material, Order, OrderItem,MonthlyClosing,SinastarInventoryHistory,SoldMaterialHistory,ExtraExpense,Officer
from .forms import InventoryPasswordForm,SinastarInventoryForm,OrderItemForm,OrderForm,ExtraExpenseForm,MaterialForm
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from django.utils.timezone import now, timedelta
from django.forms import inlineformset_factory
from .decorators import role_required
from django.db.models import Sum, Count, F
from datetime import timedelta,date,datetime
from django.db.models.functions import TruncDay
from django.utils.dateparse import parse_date
from decimal import Decimal
from django.db import models


# ----------------- Authentication -----------------
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('redirect_user')

    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})


def logout_view(request):
    request.session.pop('inventory_access', None)  # remove inventory access
    logout(request)
    return redirect('login')

# ----------------- Home -----------------
@login_required
def home(request):
    return render(request, 'home.html')

def add_product(request):
    if request.method == 'POST':
        form = MaterialForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']  # change to correct field name in your model
            quantity = form.cleaned_data['quantity']
            

            # Check if material already exists
            existing_material = Material.objects.filter(name__iexact=name).first()

            if existing_material:
                # Update existing material quantity
                existing_material.quantity += quantity
                
                existing_material.save()

                # Save history
                MaterialHistory.objects.create(
                    material=existing_material,
                    quantity=quantity,       
                    user=request.user
                )
            else:
                # Create new material
                material = form.save()

                # Save history
                MaterialHistory.objects.create(
                    material=material,
                    quantity=material.quantity,              
                    user=request.user
                )

            return redirect('inventory')
    else:
        form = MaterialForm()

    return render(request, 'add_product.html', {'form': form})

@login_required
def edit_product(request, pk):
    material = get_object_or_404(Material, pk=pk)
    if request.method == 'POST':
        form = MaterialForm(request.POST, instance=material)
        if form.is_valid():
            form.save()
            return redirect('inventory')
    else:
        form = MaterialForm(instance=material)
    return render(request, 'edit_product.html', {'form': form, 'material': material})

@login_required
def delete_product(request, pk):
    material = get_object_or_404(Material, pk=pk)
    if request.method == 'POST':
        material.delete()
        return redirect('inventory')
    return render(request, 'delete_product.html', {'material': material})
@login_required
def delete_selected_products(request):
    if request.method == "POST":
        ids = request.POST.getlist("selected_ids")
        if ids:
            Material.objects.filter(id__in=ids).delete()
    return redirect("inventory")

@login_required
def material_history(request):
    history = MaterialHistory.objects.select_related('material', 'user').order_by('-timestamp')
    return render(request, 'material_history.html', {'history': history})

@login_required
def inventory_password_check(request):
    if request.session.get('inventory_access', False):
        return redirect('inventory')

    if request.method == 'POST':
        form = InventoryPasswordForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['password'] == settings.INVENTORY_PAGE_PASSWORD:
                request.session['inventory_access'] = True
                return redirect('inventory')
            else:
                form.add_error('password', 'Incorrect password')
    else:
        form = InventoryPasswordForm()

    return render(request, 'inventory_password.html', {'form': form})

@login_required
def inventory_view(request):
    if not request.session.get('inventory_access', False):
        return redirect('inventory_password_check')

    materials = Material.objects.all()
    return render(request, 'inventory.html', {'materials': materials})
@login_required
def add_sinastar_inventory(request):
    if request.method == 'POST':
        form = SinastarInventoryForm(request.POST)
        if form.is_valid():
            material = form.cleaned_data['material']
            type_val = form.cleaned_data['type']
            quantity = form.cleaned_data['quantity']
            addition = form.cleaned_data['addition']
            addition_cost = form.cleaned_data['addition_cost']
            purchase_price = form.cleaned_data['purchase_price']  # 👉 سعر شراء للقطعة

            # ✅ إجمالي الشراء (مجرد حساب مش تخزين)
            purchase_value = purchase_price * addition  

            # Check main inventory stock
            if material.quantity < quantity:
                form.add_error('quantity', 'Not enough stock in main inventory')
            else:
                # ✅ تحديث المخزن الفرعي
                existing_item = SinastarInventory.objects.filter(material=material, type=type_val).first()
                if existing_item:
                    existing_item.quantity += quantity
                    existing_item.addition += addition
                    existing_item.addition_cost = addition_cost

                    # 👇 هنا بلاش تعيد حساب purchase_price بالمتوسط
                    # خليه يفضل زي اللي دخله المستخدم أو آخر قيمة محفوظة
                    existing_item.purchase_price = purchase_price  

                    existing_item.save()
                else:
                    existing_item = SinastarInventory.objects.create(
                        material=material,
                        type=type_val,
                        quantity=quantity,
                        addition=addition,
                        addition_cost=addition_cost,
                        purchase_price=purchase_price,  # 👈 هنا الرقم اللي في الفورم
                    )

                # ✅ تحديث History (ممكن تخليها نفس الفكرة برضه property لو عايز)
                history_item = SinastarInventoryHistory.objects.filter(material=material, type=type_val).first()
                if history_item:
                    history_item.quantity += quantity
                    history_item.addition += addition
                    history_item.addition_cost = addition_cost
                    history_item.purchase_price = purchase_price  # 👈 هنا كمان الرقم اللي في الفورم
                    history_item.save()
                else:
                    SinastarInventoryHistory.objects.create(
                        material=material,
                        type=type_val,
                        quantity=quantity,
                        addition=addition,
                        addition_cost=addition_cost,
                        purchase_price=purchase_price,
                    )


                # ✅ خصم من الـ Main Inventory
                material.quantity -= quantity
                material.save()

                return redirect('sinastar_inventory_list')
    else:
        form = SinastarInventoryForm()

    return render(request, 'add_sinastar_inventory.html', {'form': form})

@login_required
def sinastar_inventory_list(request):
    filter_type = request.GET.get("type", "all")  # فلتر النوع من الـ GET

    items = SinastarInventory.objects.select_related('material').all()

    if filter_type != "all":
        items = items.filter(type=filter_type)

    updated_total_sum = 0
    total_sum = 0
    total_purchase_sum = 0
    total_profit_sum = 0

    for item in items:
        item.updated_total = item.total_sale_price
        updated_total_sum += item.updated_total

        
        total_purchase_sum += item.total_purchase_price

        item.total_profit = item.profit
        total_profit_sum += item.total_profit

        total_sum += item.updated_total

    context = {
        'items': items,
        'updated_total_sum': updated_total_sum,
        'total_sum': total_sum,
        'total_purchase_sum': total_purchase_sum,
        'total_profit_sum': total_profit_sum,
        'filter_type': filter_type,  # عشان نستخدمه في الـ template
    }
    return render(request, 'sinastar_inventory.html', context)

# --------------------------
# 4. in cafe Handling
# --------------------------
def in_cafe(request):
    menu_items = MenuItem.objects.filter(is_active=True, show_in_cafe=True)

    tables = []
    for i in range(1, 21):  # 10 ترابيزات
        order = Order.objects.filter(table_number=i, is_paid=False).first()
        tables.append({
            "number": i,
            "order": order  # لو فيه أوردر غير مدفوع بيرجع، غير كده بيرجع None
        })

    return render(request, "in_cafe.html", {
        "menu_items": menu_items,
        "tables": tables
    })


@csrf_exempt
@login_required
def create_order(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST فقط"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
        order_type = data.get("order_type", "cafe")
        table_number = data.get("table_number")
        items = data.get("items", [])

        if order_type == "cafe" and not table_number:
            return JsonResponse({"error": "رقم الترابيزة مطلوب"}, status=400)
        if not items:
            return JsonResponse({"error": "الأصناف مطلوبة"}, status=400)

        with transaction.atomic():
            order = Order.objects.filter(
                order_type="cafe", table_number=table_number, is_paid=False
            ).first()

            if not order:
                order = Order.objects.create(
                    order_type="cafe", table_number=table_number, cashier=request.user
                )

            old_items = {oi.menuitem_id: oi for oi in order.items.all()}
            new_items = {int(it["menuitem_id"]): it for it in items}

            # 1) لو صنف اتشال
            for mid, old_item in old_items.items():
                if mid not in new_items:
                    _restore_materials(old_item.menuitem, old_item.quantity, request.user)
                    old_item.delete()

            # 2) تعديل / إضافة أصناف
            for mid, new_item in new_items.items():
                qty_new = int(new_item.get("quantity", 1))
                if mid in old_items:
                    old_item = old_items[mid]
                    qty_old = old_item.quantity

                    if qty_new <= 0:
                        # لو الكمية الجديدة صفر → رجّع كل الكمية القديمة واحذف الصنف
                        _restore_materials(old_item.menuitem, qty_old, request.user)
                        old_item.delete()
                    else:
                        if qty_new > qty_old:
                            _deduct_materials(old_item.menuitem, qty_new - qty_old, request.user)
                        elif qty_new < qty_old:
                            _restore_materials(old_item.menuitem, qty_old - qty_new, request.user)
                        old_item.quantity = qty_new
                        old_item.save()

                else:
                    menuitem = get_object_or_404(MenuItem, id=mid)
                    _deduct_materials(menuitem, qty_new, request.user)
                    OrderItem.objects.create(order=order, menuitem=menuitem, quantity=qty_new)

            order.tax = order.subtotal * Decimal("0.14")
            order.save()

        return JsonResponse({"ok": True, "order_id": order.id})

    except Exception as e:
        import traceback
        print("❌ Error in create_order:", traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)

def _deduct_materials(menuitem, qty, user):
    recipes = Recipe.objects.filter(menuitem=menuitem)
    for recipe in recipes:
        material = recipe.material
        required_qty = recipe.quantity * qty
        inventories = SinastarInventory.objects.filter(material=material)
        if not inventories.exists():
            raise ValueError(f"المكون {material.name} مش موجود في أي مخزن")

        total_addition = sum(inv.addition for inv in inventories)
        if total_addition < required_qty:
            raise ValueError(f"الإضافات لا تكفي: {material.name}")

        remaining = required_qty
        for inv in inventories:
            if remaining <= 0: break
            deducted = min(inv.addition, remaining)
            inv.addition -= deducted
            remaining -= deducted
            inv.save()
            if deducted > 0:
                SoldMaterialHistory.objects.create(
                    material=inv.material,
                    quantity=deducted,
                    addition=deducted,
                    addition_cost=inv.addition_cost,
                    purchase_price=inv.purchase_price,
                    type=inv.type,
                )
        
def _restore_materials(menuitem, qty, user):
    recipes = Recipe.objects.filter(menuitem=menuitem)
    for recipe in recipes:
        material = recipe.material
        return_qty = recipe.quantity * qty

        # 1) رجّع الكمية للمخزن
        inv = SinastarInventory.objects.filter(material=material).first()
        if inv:
            inv.addition += return_qty
            inv.save()

        # 2) انقص من سجل المبيعات
        sold_qs = SoldMaterialHistory.objects.filter(material=material).order_by("-id")
        remaining = return_qty
        for sold in sold_qs:
            if remaining <= 0:
                break

            deducted = min(sold.quantity, remaining)

            # قلل من الكمية والإضافة مع بعض
            sold.quantity -= deducted
            sold.addition -= deducted

            if sold.quantity <= 0 and sold.addition <= 0:
                sold.delete()
            else:
                sold.save()

            remaining -= deducted

@login_required
def get_order(request, table_number):
    try:
        order = Order.objects.filter(
            order_type="cafe", table_number=table_number, is_paid=False
        ).first()
        if not order:
            return JsonResponse({"order": None, "items": []})

        items = []
        for oi in order.items.select_related("menuitem"):  # ✅ استخدم related_name="items"
            items.append({
                "menuitem_id": oi.menuitem.id,
                "name": oi.menuitem.name,
                "quantity": oi.quantity,
                "price": float(oi.menuitem.price),
            })

        return JsonResponse({
            "order": {
                "id": order.id,
                "table_number": order.table_number,
                "subtotal": str(order.subtotal),
                "tax": str(order.tax),
                "total": str(order.total),  # 👈 أضفتها عشان يبان السعر النهائي
            },
            "items": items
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def orders_list(request):
    order_type = request.GET.get("type")  # فلتر النوع
    date_filter = request.GET.get("date")  # فلتر التاريخ
    cashier_name = request.GET.get("cashier")  # فلتر الكاشير
    payment_filter = request.GET.get("payment")
    all_orders = Order.objects.all().select_related("cashier")
    
    # فلترة النوع
    if order_type in ["cafe", "takeaway","qeta3"]:
        all_orders = all_orders.filter(order_type=order_type)

    # فلترة التاريخ
    today = now().date()
    if date_filter == "today":
        all_orders = all_orders.filter(created_at__date=today)
    elif date_filter == "week":
        start_week = today - timedelta(days=today.weekday())
        all_orders = all_orders.filter(created_at__date__gte=start_week)
    elif date_filter == "month":
        all_orders = all_orders.filter(
            created_at__month=today.month,
            created_at__year=today.year,
        )

    # فلترة الكاشير
    if cashier_name:
        all_orders = all_orders.filter(cashier__username__icontains=cashier_name)

    # ✅ فلترة طريقة الدفع
    if payment_filter in ["cash", "vodafone", "moagel"]:
        all_orders = all_orders.filter(payment_method=payment_filter)
    # إحصائيات
    total_orders = all_orders.count()
    total_sales = sum(order.total for order in all_orders)

    # العدادات (بدون فلترة التاريخ أو الكاشير)
    cafe_count = Order.objects.filter(order_type="cafe").count()
    takeaway_count = Order.objects.filter(order_type="takeaway").count()
    qeta3_count = Order.objects.filter(order_type="qeta3").count()
    all_count = Order.objects.count()

    return render(request, "orders_list.html", {
        "orders": all_orders.order_by("-created_at"),
        "active_filter": order_type or "all",
        "date_filter": date_filter or "all",
        "cashier_filter": cashier_name or "",
        "payment_filter": payment_filter or "",
        "cafe_count": cafe_count,
        "takeaway_count": takeaway_count,
        "qeta3_count": qeta3_count,
        "all_count": all_count,
        "total_orders": total_orders,
        "total_sales": total_sales,
    })
from django.http import JsonResponse

@login_required
def get_latest_orders(request):
    from .models import Order

    # نستقبل آخر ID ظاهر في الصفحة
    last_id = request.GET.get('last_id')
    if last_id:
        new_orders = Order.objects.filter(id__gt=last_id).order_by('id')
    else:
        new_orders = Order.objects.all().order_by('-id')[:10]

    data = []
    for order in new_orders:
        data.append({
            'id': order.id,
            'order_type': order.order_type,
            'table_number': order.table_number,
            'cashier': order.cashier.username if order.cashier else '',
            'created_at': order.created_at.strftime("%Y-%m-%d %H:%M"),
            'is_paid': order.is_paid,
            'payment_method': order.get_payment_method_display() if order.is_paid else '',
            'subtotal': float(order.subtotal),
            'discount': float(order.discount),
            'tax': float(order.tax),
            'total': float(order.total),
            'note': order.note or '',
        })

    return JsonResponse({'orders': data})


def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    section_filter = request.GET.get("section", "all")

    if section_filter == "barista":
        items = order.items.filter(section="barista")
    elif section_filter == "mat3am":
        items = order.items.filter(section="mat3am")
    else:
        items = order.items.all()

    return render(request, "order_detail.html", {
        "order": order,
        "items": items,
        "section_filter": section_filter,
    })

'''def pay_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.is_paid = True
    order.save()
    return redirect("orders_list")'''

# views.py
def pay_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "select_payment.html", {"order": order})
def confirm_payment(request, order_id, method):
    order = get_object_or_404(Order, id=order_id)

    # تحديث بيانات الدفع
    order.payment_method = method
    order.is_paid = True
    order.save()

    # لو الدفع كاش أو فودافون كاش → يروح صفحة الطباعة
    if method in ["cash", "vodafone"]:
        return redirect("print_order", order.id)

    # لو الدفع مؤجل → فقط ارجع لقائمة الأوردرات حالياً
    return redirect("orders_list")


@login_required
def edit_order_from_list(request, order_id):
    order = get_object_or_404(Order, pk=order_id)

    OrderItemFormSet = inlineformset_factory(
        Order, OrderItem, form=OrderItemForm,
        extra=1, can_delete=True
    )

    if request.method == "POST":
        form = OrderForm(request.POST, instance=order)
        formset = OrderItemFormSet(request.POST, instance=order)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                # 🟢 خزن نسخة من الأصناف القديمة
                old_items = {oi.pk: oi for oi in OrderItem.objects.filter(order=order)}

                form.save()

                # 🟡 احفظ العناصر الجديدة والمعدلة
                instances = formset.save(commit=False)
                updated_item_pks = []

                for inst in instances:
                    inst.order = order
                    inst.save()
                    updated_item_pks.append(inst.pk)

                    old_item = old_items.pop(inst.pk, None)
                    if old_item:
                        diff = inst.quantity - old_item.quantity
                        if diff > 0:
                            _deduct_materials(inst.menuitem, diff, request.user)
                        elif diff < 0:
                            _restore_materials(inst.menuitem, abs(diff), request.user)
                    else:
                        _deduct_materials(inst.menuitem, inst.quantity, request.user)

                # 🟠 احذف العناصر اللي فعلاً اتعلم عليها كـ delete
                for obj in formset.deleted_objects:
                    _restore_materials(obj.menuitem, obj.quantity, request.user)
                    obj.delete()

                # ⚙️ الجديد هنا: احتفظ بالأصناف القديمة اللي مش في الـ POST
                # لو المستخدم ما لمسهاش، سيبها زي ما هي
                for pk, oi in old_items.items():
                    if pk not in updated_item_pks:
                        # 🟣 نرجعها للأوردر زي ما كانت بدون أي تعديل
                        oi.order = order
                        oi.save()

                # ✅ تحديث الضريبة
                try:
                    order.tax = order.subtotal * Decimal("0.14")
                except Exception:
                    pass
                order.save()

            return redirect("orders_list")

        else:
            print("Form errors:", form.errors)
            print("Formset errors:", formset.errors)

    else:
        form = OrderForm(instance=order)
        formset = OrderItemFormSet(instance=order)

    return render(request, "edit_order_from_list.html", {
        "form": form,
        "formset": formset,
        "order": order
    })


@login_required
def delete_order_from_list(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if request.method == "POST":
        with transaction.atomic():
            # 🟢 رجّع كل المخزون قبل الحذف
            for oi in order.items.all():
                _restore_materials(oi.menuitem, oi.quantity, request.user)

            order.delete()

        return redirect("orders_list")

    return render(request, "confirm_delete_order.html", {
        "order": order
    })

#take away
def takeaway(request):
    menu_items = MenuItem.objects.filter(is_active=True, show_in_takeaway=True)

    # الأقسام ثابتة
    SECTIONS = {
        "barista": "باريستا",
        "mat3am": "مطعم",
        "canteen": "كانتين",
        "7alak": "حلاق",
        "shesha": "شيشة",
        "addons": "إضافات",
    }

    sections_display = [(sec, name) for sec, name in SECTIONS.items()]

    return render(
        request,
        "takeaway_menu.html",
        {
            "menu_items": menu_items,
            "sections_display": sections_display,
        },
    )

@csrf_exempt
@login_required
def create_takeaway_order(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST فقط"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
        items = data.get("items", [])
        note = data.get("note", "").strip()  # ✅ استلام الملاحظة من الواجهة

        if not items:
            return JsonResponse({"error": "مفيش أصناف"}, status=400)

        missing_materials = []

        # ✅ التشيك على الكميات المتاحة في المخزن
        for item in items:
            menuitem_id = item.get("menuitem_id")
            qty = int(item.get("quantity", 1))
            menuitem = get_object_or_404(MenuItem, id=menuitem_id)

            recipes = Recipe.objects.filter(menuitem=menuitem)
            for recipe in recipes:
                material = recipe.material
                required_qty = recipe.quantity * qty

                inventories = SinastarInventory.objects.filter(material=material)
                if not inventories.exists():
                    missing_materials.append(f"{material.name} مش موجود في أي مخزن")
                    continue

                total_addition = sum(inv.addition for inv in inventories)
                if total_addition < required_qty:
                    missing_materials.append(
                        f"{material.name} (مطلوب {required_qty}، متاح {total_addition})"
                    )

        if missing_materials:
            return JsonResponse(
                {"error": "المخزن لا يكفي", "missing": missing_materials},
                status=400,
            )

        # ✅ إنشاء الأوردر وسحب المواد من المخزون
        with transaction.atomic():
            order = Order.objects.create(
                order_type="takeaway",
                cashier=request.user,
                note=note  # ✅ حفظ الملاحظة في الأوردر
            )

            for item in items:
                menuitem_id = item.get("menuitem_id")
                qty = int(item.get("quantity", 1))
                menuitem = get_object_or_404(MenuItem, id=menuitem_id)

                # إنشاء عنصر الأوردر
                OrderItem.objects.create(order=order, menuitem=menuitem, quantity=qty)

                # خصم المواد من المخزون
                recipes = Recipe.objects.filter(menuitem=menuitem)
                for recipe in recipes:
                    material = recipe.material
                    required_qty = recipe.quantity * qty

                    inventories = SinastarInventory.objects.filter(material=material)
                    remaining = required_qty

                    for inv in inventories:
                        if remaining <= 0:
                            break

                        deducted = 0
                        if inv.addition >= remaining:
                            deducted = remaining
                            inv.addition -= remaining
                            remaining = 0
                        else:
                            deducted = inv.addition
                            remaining -= inv.addition
                            inv.addition = 0

                        inv.save()

                        # 🟢 سجل في SoldMaterialHistory (تجميع يومي)
                        sold_item = SoldMaterialHistory.objects.filter(material=inv.material).first()
                        if not sold_item:
                            sold_item = SoldMaterialHistory.objects.create(
                                material=inv.material,
                                quantity=0,
                                addition=0,
                                addition_cost=inv.addition_cost,
                                purchase_price=inv.purchase_price,
                            )

                        sold_item.quantity += deducted
                        sold_item.addition += deducted
                        sold_item.save()

            return JsonResponse({"success": True, "order_id": order.id})

    except Exception as e:
        import traceback
        print("❌ Error in create_takeaway_order:", traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)

@login_required
def check_menuitem(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            menuitem_id = data.get("menuitem_id")
            qty = int(data.get("quantity", 1))

            menuitem = get_object_or_404(MenuItem, id=menuitem_id)

            missing_materials = []
            recipes = Recipe.objects.filter(menuitem=menuitem)

            for recipe in recipes:
                material = recipe.material
                required_qty = recipe.quantity * qty

                # 🟢 هات كل الـ rows الخاصة بالمكون بغض النظر عن type
                inventories = SinastarInventory.objects.filter(material=material)

                if not inventories.exists():
                    missing_materials.append(f"{material.name} (مش موجود في أي مخزن)")
                    continue

                total_addition = sum(inv.addition for inv in inventories)

                # ✅ check على addition فقط
                if total_addition < required_qty:
                    missing_materials.append(
                        f"{material.name} (مطلوب {required_qty}، متاح {total_addition})"
                    )

            if missing_materials:
                return JsonResponse({"ok": False, "missing": missing_materials})

            return JsonResponse({"ok": True})

        except Exception as e:
            return JsonResponse({"ok": False, "error": str(e)}, status=500)

    return JsonResponse({"ok": False, "error": "POST فقط"}, status=405)

def pending_items(request):
    role = getattr(request.user.profile, "role", None)
    inv_type = request.GET.get("type")  # Baresta / Buffet / Canteen

    orders = Order.objects.filter(is_paid=False).order_by("created_at")

    filtered_orders = []
    for order in orders:
        items = order.items.filter(is_done=False)

        # فلترة حسب القسم (على مستوى الـ MenuItem.section)
        if inv_type:
            items = items.filter(menuitem__section=inv_type)

        if items.exists():
            filtered_orders.append({
                "order": order,
                "items": items
            })

    # ✅ تحديد إذا كان المستخدم ينتمي لجروب "barista"
    #is_barista = request.user.groups.filter(name="barista").exists()
    profile = request.user.profile
    return render(request, "pending_items.html", {
        "orders": filtered_orders,
        "inv_type": inv_type,
        "role": role,  # إرسال المتغير للتمبليت
    })


def mark_item_done(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id)
    item.is_done = True
    item.save()

    # لو عايز ترجع AJAX
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"success": True, "order_id": item.order.id})

    return redirect("pending_items")

def waiter_items(request):
    orders = Order.objects.filter(is_paid=False).order_by("created_at")

    finished_orders = []
    for order in orders:
        items = order.items.filter(is_done=True)  # بس اللي خلصت
        if items.exists():
            finished_orders.append({
                "order": order,
                "items": items
            })

    return render(request, "waiter_items.html", {
        "orders": finished_orders
    })
def waiter_mark_done(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # نخلي كل الايتمات اللي خلصت خلاص تتشال من صفحة الويتر
    order.items.filter(is_done=True).delete()

    return redirect("waiter_items")

#take away
def qeta3(request):
    menu_items = MenuItem.objects.filter(is_active=True, show_in_qeta3=True)
    officers = Officer.objects.all()

    # الأقسام
    SECTIONS = {
        "barista": "باريستا",
        "mat3am": "مطعم",
        "canteen": "كانتين",
        "7alak": "حلاق",
        "shesha": "شيشة",
        "addons": "إضافات",
    }

    sections_display = [(sec, name) for sec, name in SECTIONS.items()]
    
    return render(
        request,
        "qeta3_menu.html",
        {
            "menu_items": menu_items,
            "officers": officers,
            "sections_display": sections_display,
        },
    )


@csrf_exempt
@login_required
def create_qeta3_order(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST فقط"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
        items = data.get("items", [])
        officer_id = data.get("officer_id")

        if not items:
            return JsonResponse({"error": "مفيش أصناف"}, status=400)

        if not officer_id:
            return JsonResponse({"error": "لازم تختار اسم الظابط"}, status=400)

        officer = get_object_or_404(Officer, id=officer_id)
        missing_materials = []

        # ✅ التشيك الأول على المخزن
        for item in items:
            menuitem_id = item.get("menuitem_id")
            qty = int(item.get("quantity", 1))
            menuitem = get_object_or_404(MenuItem, id=menuitem_id)

            recipes = Recipe.objects.filter(menuitem=menuitem)
            for recipe in recipes:
                material = recipe.material
                required_qty = recipe.quantity * qty

                inventories = SinastarInventory.objects.filter(material=material)
                if not inventories.exists():
                    missing_materials.append(f"{material.name} مش موجود في أي مخزن")
                    continue

                total_addition = sum(inv.addition for inv in inventories)
                if total_addition < required_qty:
                    missing_materials.append(
                        f"{material.name} (مطلوب {required_qty}، متاح {total_addition})"
                    )

        if missing_materials:
            return JsonResponse(
                {"error": "المخزن لا يكفي", "missing": missing_materials},
                status=400,
            )

        # ✅ إنشاء الأوردر
        with transaction.atomic():
            order = Order.objects.create(
                order_type="qeta3",
                cashier=request.user,
                officer=officer
            )

            subtotal = Decimal("0.00")

            for item in items:
                menuitem_id = item.get("menuitem_id")
                qty = int(item.get("quantity", 1))
                menuitem = get_object_or_404(MenuItem, id=menuitem_id)

                OrderItem.objects.create(order=order, menuitem=menuitem, quantity=qty)
                subtotal += Decimal(menuitem.price) * qty

                # تحديث المخزن
                recipes = Recipe.objects.filter(menuitem=menuitem)
                for recipe in recipes:
                    material = recipe.material
                    required_qty = recipe.quantity * qty
                    inventories = SinastarInventory.objects.filter(material=material)
                    remaining = required_qty

                    for inv in inventories:
                        if remaining <= 0:
                            break

                        deducted = 0
                        if inv.addition >= remaining:
                            deducted = remaining
                            inv.addition -= remaining
                            remaining = 0
                        else:
                            deducted = inv.addition
                            remaining -= inv.addition
                            inv.addition = 0

                        inv.save()

                        sold_item = SoldMaterialHistory.objects.filter(
                            material=inv.material,
                            type=inv.type  # لو النوع مهم في التمييز
                        ).first()

                        if not sold_item:
                            sold_item = SoldMaterialHistory.objects.create(
                                material=inv.material,
                                type=inv.type,
                                quantity=0,
                                addition=0,
                                addition_cost=inv.addition_cost,
                                purchase_price=inv.purchase_price,
                            )

                        sold_item.quantity += deducted
                        sold_item.addition += deducted
                        sold_item.save()


            # ✅ الخصم من officer.discount_rate
            discount = subtotal * officer.discount_rate
            order.discount = discount
            order.tax = Decimal("0.00")
            order.save(update_fields=["discount", "tax"])

            return JsonResponse({
                "success": True,
                "order_id": order.id,
                "subtotal": str(order.subtotal),  # property
                "discount": str(order.discount),
                "total": str(order.total)         # property
            })

    except Exception as e:
        import traceback
        print("❌ Error in create_qeta3_order:", traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)



def officer_orders(request):
    officers = Officer.objects.all()
    selected_officer = None

    officer_id = request.GET.get("officer_id")
    payment_filter = request.GET.get("payment_method")
    payment_status = request.GET.get("payment_status")

    # ✅ نجيب كل أوردرات القطاع
    orders = Order.objects.filter(order_type="qeta3").select_related("officer").prefetch_related("items__menuitem")

    # ✅ فلتر الضابط
    if officer_id:
        selected_officer = get_object_or_404(Officer, id=officer_id)
        orders = orders.filter(officer=selected_officer)

    # ✅ فلتر طريقة الدفع
    if payment_filter:
        orders = orders.filter(payment_method=payment_filter)

    # ✅ فلتر حالة الدفع
    if payment_status == "paid":
        orders = orders.filter(is_paid=True).exclude(payment_method="moagel")  # المؤجل مش مدفوع
    elif payment_status == "unpaid":
        orders = orders.filter(is_paid=False) | orders.filter(payment_method="moagel")

    # ✅ الترتيب
    orders = orders.order_by("-created_at").distinct()

    # ✅ حساب الإجماليات
    total_sum = Decimal("0.00")
    for order in orders:
        subtotal = sum(Decimal(i.menuitem.price) * i.quantity for i in order.items.all())
        discount_amount = subtotal * order.officer.discount_rate if order.officer else Decimal("0.00")
        total = subtotal - discount_amount
        order.calc_subtotal = subtotal
        order.discount_amount = discount_amount
        order.calc_total = total
        total_sum += total

    return render(
        request,
        "officer_orders.html",
        {
            "officers": officers,
            "selected_officer": selected_officer,
            "orders": orders,
            "payment_filter": payment_filter,
            "payment_status": payment_status,
            "total_sum": total_sum,
        },
    )



@login_required
def daily_closing(request):
    # فلتر اليوم (افتراضيًا النهاردة)
    selected_date = request.GET.get("date")
    if selected_date:
        selected_date = parse_date(selected_date)
    else:
        selected_date = now().date()

    # 🟢 الاوردرات
    order_items = OrderItem.objects.filter(order__created_at__date=selected_date)

    # 🟢 اجمع حسب السكشن
    section_summary = (
        order_items.values("menuitem__section")
        .annotate(
            total_qty=Sum("quantity"),
            total_sales=Sum(F("menuitem__price") * F("quantity")),
        )
        .order_by("menuitem__section")
    )

    # 🟢 اجمع تفاصيل الأصناف
    item_summary = (
        order_items.values("menuitem__name", "menuitem__section")
        .annotate(
            total_qty=Sum("quantity"),
            total_sales=Sum(F("menuitem__price") * F("quantity")),
        )
        .order_by("menuitem__section", "menuitem__name")
    )

    # 🟢 ترجمات السكاشن
    SECTION_DISPLAY = {
        "barista": "باريستا",
        "mat3am": "مطعم",
        "canteen": "كانتين",
        "7alak": "حلاق",
        "shesha": "شيشة",
        "addons": "إضافات",
    }

    section_summary = [
        {
            "section": SECTION_DISPLAY.get(s["menuitem__section"], s["menuitem__section"]),
            "total_qty": s["total_qty"],
            "total_sales": s["total_sales"],
        }
        for s in section_summary
    ]

    # 🟢 هات النسريات والتبس
    expenses = ExtraExpense.objects.filter(created_at__date=selected_date).order_by("-created_at")

    total_nesrayat = expenses.filter(category="nesrayat").aggregate(Sum("amount"))["amount__sum"] or 0
    total_tips = expenses.filter(category="tips").aggregate(Sum("amount"))["amount__sum"] or 0
    total_all = total_nesrayat + total_tips

    return render(
        request,
        "daily_closing.html",
        {
            "section_summary": section_summary,
            "item_summary": item_summary,
            "expenses": expenses,
            "total_nesrayat": total_nesrayat,
            "total_tips": total_tips,
            "total_all": total_all,
            "selected_date": selected_date,
        },
    )

@login_required
def profit_chart_data(request):
    today = date.today()
    first_day = today.replace(day=1)

    data = (
        MonthlyClosing.objects.filter(month__gte=first_day)
        .annotate(day=TruncDay("created_at"))
        .values("day")
        .annotate(
            actual=Sum("profit_actual"),
            expected=Sum("profit_expected"),
            remaining=Sum("profit_remaining"),
        )
        .order_by("day")
    )

    return JsonResponse(list(data), safe=False)

@login_required
def monthly_closing_list(request):
    # 🟢 فلتر التاريخ بتاع SoldMaterialHistory
    sold_start = request.GET.get("sold_start")
    sold_end = request.GET.get("sold_end")
    sold_history = SoldMaterialHistory.objects.all()
    if sold_start:
        sold_history = sold_history.filter(created_at__date__gte=parse_date(sold_start))
    if sold_end:
        sold_history = sold_history.filter(created_at__date__lte=parse_date(sold_end))

    total_quantity = sum(item.quantity for item in sold_history)
    total_addition = sum(item.addition for item in sold_history)
    total_sale = sum(item.total_sale_price for item in sold_history)
    total_purchase = sum(item.total_purchase_price for item in sold_history)
    total_profit = sum(item.profit for item in sold_history)

    # 🟢 فلتر التاريخ بتاع SinastarInventoryHistory
    inv_start = request.GET.get("inv_start")
    inv_end = request.GET.get("inv_end")
    inventory_history = SinastarInventoryHistory.objects.all()
    if inv_start:
        inventory_history = inventory_history.filter(created_at__date__gte=parse_date(inv_start))
    if inv_end:
        inventory_history = inventory_history.filter(created_at__date__lte=parse_date(inv_end))

    updated_total_sum = sum(item.total_sale_price for item in inventory_history)
    total_purchase_sum = sum(item.total_purchase_price for item in inventory_history)
    total_profit_sum = sum(item.profit for item in inventory_history)

    # 🟢 فلتر التاريخ بتاع SinastarInventory (المخزن الحالي)
    store_start = request.GET.get("store_start")
    store_end = request.GET.get("store_end")
    current_inventory = SinastarInventory.objects.all()
    if store_start:
        current_inventory = current_inventory.filter(updated_at__date__gte=parse_date(store_start))
    if store_end:
        current_inventory = current_inventory.filter(updated_at__date__lte=parse_date(store_end))

    store_total_sale = sum(item.total_sale_price for item in current_inventory)
    store_total_purchase = sum(item.total_purchase_price for item in current_inventory)
    store_total_profit = sum(item.profit for item in current_inventory)

    # 🟢 جدول الفواتير (Orders)
    order_start = request.GET.get("order_start")
    order_end = request.GET.get("order_end")
    orders = Order.objects.filter(is_paid=True)
    if order_start:
        orders = orders.filter(created_at__date__gte=parse_date(order_start))
    if order_end:
        orders = orders.filter(created_at__date__lte=parse_date(order_end))

    total_orders = orders.count()

    total_orders_sales = 0
    for order in orders:
        items_total = sum(item.total_price for item in order.items.all())
        order_total = items_total + order.tax + order.service_charge - order.discount
        total_orders_sales += order_total

    # 🟢 جدول ExtraExpense
    exp_start = request.GET.get("exp_start")
    exp_end = request.GET.get("exp_end")
    expenses = ExtraExpense.objects.all().order_by("-created_at")
    if exp_start:
        expenses = expenses.filter(created_at__date__gte=parse_date(exp_start))
    if exp_end:
        expenses = expenses.filter(created_at__date__lte=parse_date(exp_end))

    total_nesrayat = expenses.filter(category="nesrayat").aggregate(Sum("amount"))["amount__sum"] or 0
    total_tips = expenses.filter(category="tips").aggregate(Sum("amount"))["amount__sum"] or 0
    total_all_exp = total_nesrayat + total_tips

    context = {
        # ✅ Sold Materials
        "sold_history": sold_history,
        "total_quantity": total_quantity,
        "total_addition": total_addition,
        "total_sale": total_sale,
        "total_purchase": total_purchase,
        "total_profit": total_profit,
        "sold_start": sold_start,
        "sold_end": sold_end,

        # ✅ Inventory History
        "inventory_history": inventory_history,
        "updated_total_sum": updated_total_sum,
        "total_purchase_sum": total_purchase_sum,
        "total_profit_sum": total_profit_sum,
        "inv_start": inv_start,
        "inv_end": inv_end,

        # ✅ Current Inventory
        "current_inventory": current_inventory,
        "store_total_sale": store_total_sale,
        "store_total_purchase": store_total_purchase,
        "store_total_profit": store_total_profit,
        "store_start": store_start,
        "store_end": store_end,

        # ✅ Orders
        "orders": orders.order_by("-created_at"),
        "order_start": order_start,
        "order_end": order_end,
        "total_orders": total_orders,
        "total_orders_sales": total_orders_sales,

        # ✅ Closings
        "closings": MonthlyClosing.objects.all().order_by("-created_at"),

        # ✅ Extra Expenses
        "expenses": expenses,
        "total_nesrayat": total_nesrayat,
        "total_tips": total_tips,
        "total_all_exp": total_all_exp,
        "exp_start": exp_start,
        "exp_end": exp_end,
    }
    return render(request, "monthly_closing_list.html", context)

@login_required
def create_monthly_closing(request):
    if request.method == "POST":
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")

        if not start_date or not end_date:
            return render(request, "create_monthly_closing.html", {
                "error": "لازم تختار تاريخ البداية والنهاية"
            })

        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        # 1️⃣ إجمالي مبيعات الفواتير
        orders = Order.objects.filter(
            is_paid=True,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
        total_sales_orders = 0
        for order in orders:
            items_total = sum(item.total_price for item in order.items.all())
            order_total = items_total + order.tax + order.service_charge - order.discount
            total_sales_orders += order_total

        # 2️⃣ إجمالي بيع المتبقي (SinastarInventory)
        current_items = SinastarInventory.objects.filter(
            updated_at__date__gte=start_date,
            updated_at__date__lte=end_date
        )
        total_sales_inventory = sum(item.total_sale_price for item in current_items)

        # 3️⃣ إجمالي الشراء = (سعر شراء المواد المباعة + سعر شراء المخزن الحالي)
        sold_items = SoldMaterialHistory.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
        sold_purchase_total = sum(item.total_purchase_price for item in sold_items)

        current_purchase_total = sum(item.total_purchase_price for item in current_items)

        total_purchase_inventory = sold_purchase_total + current_purchase_total

        # 4️⃣ الربح
        total_profit = (total_sales_orders + total_sales_inventory) - total_purchase_inventory

        # 5️⃣ الربح من المخزن
        profit_from_inventory = sum(item.profit for item in current_items)

        # 6️⃣ الخزينة (قبل الخصم والإضافة)
        actual_profit = total_profit - profit_from_inventory

        # 7️⃣ اجمع النسريات + التبس
        total_nesrayat = ExtraExpense.objects.filter(
            category="nesrayat",
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).aggregate(Sum("amount"))["amount__sum"] or 0

        total_tips = ExtraExpense.objects.filter(
            category="tips",
            created_at__date__gte=start_date,
            created_at__lte=end_date
        ).aggregate(Sum("amount"))["amount__sum"] or 0

        # 8️⃣ عدل الربح الفعلي (خصم النسريات + إضافة التبس)
        actual_profit = actual_profit - total_nesrayat + total_tips

        # ✅ حفظ الـ Closing
        closing = MonthlyClosing.objects.create(
            month=start_date,
            start_date=start_date,
            end_date=end_date,
            total_sales_orders=total_sales_orders,
            total_sales_inventory=total_sales_inventory,
            total_purchase_inventory=total_purchase_inventory,
            total_profit=total_profit,
            profit_from_inventory=profit_from_inventory,
            actual_profit=actual_profit,
            total_nesrayat=total_nesrayat,
            total_tips=total_tips,
        )

        # ✅ تعديل History (الخصم من SinastarInventoryHistory حسب المباع)
        for sold in sold_items:
            qty_to_deduct = sold.quantity
            histories = SinastarInventoryHistory.objects.filter(material=sold.material).order_by("created_at")

            for h in histories:
                if qty_to_deduct <= 0:
                    break
                if h.addition >= qty_to_deduct:
                    h.addition -= qty_to_deduct
                    h.save()
                    qty_to_deduct = 0
                else:
                    qty_to_deduct -= h.addition
                    h.addition = 0
                    h.save()

            SinastarInventoryHistory.objects.filter(material=sold.material, addition=0).delete()

        # ✅ تحديث الـ updated_at لكل المخزون
        SinastarInventory.objects.all().update(updated_at=now())

        return redirect("monthly_closing_list")

    return render(request, "create_closing_form.html")

@login_required
def sinastar_inventory_history(request):
    items = SinastarInventoryHistory.objects.select_related('material').all()

    # فلترة بالتاريخ
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    if start_date:
        items = items.filter(created_at__date__gte=parse_date(start_date))
    if end_date:
        items = items.filter(created_at__date__lte=parse_date(end_date))

    # 🟢 حساب الإجماليات يدويًا
    updated_total_sum = sum(item.total_sale_price for item in items)
    total_purchase_sum = sum(item.total_purchase_price for item in items)
    total_profit_sum = sum(item.profit for item in items)

    context = {
        "items": items,
        "updated_total_sum": updated_total_sum,
        "total_purchase_sum": total_purchase_sum,
        "total_profit_sum": total_profit_sum,
        "start_date": start_date,
        "end_date": end_date,
    }
    return render(request, "sinastar_inventory_history.html", context)

@login_required
def update_addition(request, item_id, action):
    try:
        item = SinastarInventory.objects.get(id=item_id)
        data = json.loads(request.body.decode("utf-8"))
        amount = int(data.get("amount", 1))

        # ✅ تعديل الـ addition
        if action == "increase":
            item.addition += amount
            history_change = amount
        elif action == "decrease":
            if item.addition - amount < 0:
                return JsonResponse({"success": False, "error": "القيمة لا يمكن أن تكون سالبة"})
            item.addition -= amount
            history_change = -amount
        else:
            return JsonResponse({"success": False, "error": "Invalid action"})

        # ✅ تحديث سعر الشراء الجديد (متوسط) لو حابب تحسبه
        if item.addition > 0:
            item.purchase_price = item.purchase_price  # (ممكن تسيبها زي ما هي أو تحسب متوسط جديد لو عندك لوجيك)

        # ✅ إجماليات جديدة (باستخدام الـ property)
        new_purchase = item.total_purchase_price
        new_sale = item.addition * item.addition_cost
        new_profit = new_sale - new_purchase

        # ✅ حفظ التعديلات
        item.save()

        # ✅ تحديث المخزن الثابت (History)
        history_item, created = SinastarInventoryHistory.objects.get_or_create(
            material=item.material,
            type=item.type,
            defaults={
                "quantity": item.quantity,
                "addition": 0,
                "addition_cost": item.addition_cost,
                "purchase_price": item.purchase_price,
            },
        )

        history_item.addition += history_change
        history_item.addition_cost = item.addition_cost
        history_item.purchase_price = item.purchase_price
        history_item.save()

        # ✅ تحديث الإجماليات لكل المخزن (بالاعتماد على property)
        items = SinastarInventory.objects.all()
        updated_total_sum = sum(i.total_sale_price for i in items)  # اجمالي البيع
        total_purchase_sum = sum(i.total_purchase_price for i in items)  # اجمالي الشراء
        total_profit_sum = updated_total_sum - total_purchase_sum  # اجمالي الربح

        return JsonResponse({
            "success": True,
            "new_addition": item.addition,
            "new_sale": new_sale,
            "new_total_purchase": new_purchase,
            "new_profit": new_profit,
            "updated_total_sum": updated_total_sum,
            "total_purchase_sum": total_purchase_sum,
            "total_profit_sum": total_profit_sum,
        })

    except SinastarInventory.DoesNotExist:
        return JsonResponse({"success": False, "error": "Item not found"})

from django.utils.dateparse import parse_date

def extra_expenses_view(request):
    form = ExtraExpenseForm(request.POST or None)

    # فلاتر
    category_filter = request.GET.get("category", "")
    start_date = request.GET.get("start_date", "")
    end_date = request.GET.get("end_date", "")

    expenses = ExtraExpense.objects.all().order_by("-created_at")

    if category_filter:
        expenses = expenses.filter(category=category_filter)

    if start_date:
        expenses = expenses.filter(created_at__date__gte=parse_date(start_date))
    if end_date:
        expenses = expenses.filter(created_at__date__lte=parse_date(end_date))

    # POST: إضافة بند جديد
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("extra_expenses")

    # 🟢 احصائيات بعد الفلترة
    total_nesrayat = expenses.filter(category="nesrayat").aggregate(Sum("amount"))["amount__sum"] or 0
    total_tips = expenses.filter(category="tips").aggregate(Sum("amount"))["amount__sum"] or 0
    total_all = total_nesrayat + total_tips

    context = {
        "form": form,
        "expenses": expenses,
        "total_nesrayat": total_nesrayat,
        "total_tips": total_tips,
        "total_all": total_all,
        "category_filter": category_filter,
        "start_date": start_date,
        "end_date": end_date,
    }
    return render(request, "extra_expenses.html", context)

# 🗑️ دالة لحذف بند
def delete_expense(request, pk):
    expense = get_object_or_404(ExtraExpense, id=pk)
    expense.delete()
    return redirect("extra_expenses")
from decimal import Decimal

@login_required
def print_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    items = order.items.all()

    # احسب الإجمالي لكل صنف
    for item in items:
        item.line_total = Decimal(item.menuitem.price) * item.quantity

    # احسب الإجماليات
    subtotal = sum(item.line_total for item in items)
    discount = Decimal(order.discount or 0)
    tax = Decimal(order.tax or 0)
    total = subtotal - discount + tax

    return render(request, "print_order.html", {
        "order": order,
        "items": items,
        "subtotal": subtotal,
        "discount": discount,
        "tax": tax,
        "total": total,
    })

from django.views.decorators.http import require_POST
from django.shortcuts import redirect

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt  # أو استخدم @csrf_protect مع CSRF token

@require_POST
@csrf_exempt
def mark_order_paid(request, order_id):
    """
    تحديث حالة الأوردر المؤجل إلى مدفوع
    """
    from .models import Order
    payment_method = request.POST.get("payment_method")

    if payment_method not in ["cash", "vodafone"]:
        return JsonResponse({"error": "طريقة الدفع غير صالحة."}, status=400)

    try:
        order = Order.objects.get(id=order_id)
        order.payment_method = payment_method
        order.is_paid = True
        order.save()
        return JsonResponse({"success": True})
    except Order.DoesNotExist:
        return JsonResponse({"error": "الأوردر غير موجود."}, status=404)

@login_required
def redirect_user(request):
    profile = request.user.profile  # جِب الـ role

    if profile.role in ['admin', 'cashier']:
        return redirect('home')

    elif profile.role == 'waiter':
        return redirect('waiter_items')

    elif profile.role == 'mat3am':
        return redirect('/pending-items/?type=mat3am')

    elif profile.role == 'barista':
        return redirect('/pending-items/?type=barista')

    else:
        return redirect('home')

@login_required
@csrf_exempt
def update_min_stock(request, item_id):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            new_min_stock = int(data.get("minimum_stock", 0))
            item = SinastarInventory.objects.get(id=item_id)
            item.minimum_stock = new_min_stock
            item.save()
            return JsonResponse({"success": True, "new_minimum_stock": new_min_stock})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"success": False, "error": "Invalid request"})
@login_required
def sinastar_inventory_shortage(request):
    from django.db.models import F
    from django.http import HttpResponse
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    # ✅ لو الـ addition أقل من الحد الأدنى يتحسب نواقص
    items = SinastarInventory.objects.filter(addition__lt=F('minimum_stock'))

    # نحسب النقص (الفرق بين الحد الأدنى والكمية الفعلية)
    for item in items:
        item.deficit = item.minimum_stock - item.addition

    # ✅ في حالة التصدير إلى PDF
    if 'export' in request.GET:
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="shortage_report.pdf"'

        p = canvas.Canvas(response, pagesize=A4)
        width, height = A4
        y = height - 50

        p.setFont("Helvetica-Bold", 14)
        p.drawString(180, y, "🚨 Sinastar Shortage Report")
        y -= 40

        p.setFont("Helvetica", 11)
        for item in items:
            text = f"{item.material.name} ({item.type}) - Addition: {item.addition} / Min: {item.minimum_stock} / Deficit: {item.deficit}"
            p.drawString(40, y, text)
            y -= 20
            if y < 50:
                p.showPage()
                p.setFont("Helvetica", 11)
                y = height - 50

        p.save()
        return response

    return render(request, 'sinastar_inventory_shortage.html', {'items': items})

