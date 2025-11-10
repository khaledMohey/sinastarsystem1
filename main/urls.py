from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Inventory
    path('inventory/', views.inventory_view, name='inventory'),
    path('inventory/add/', views.add_product, name='add_product'),
    path('inventory/edit/<int:pk>/', views.edit_product, name='edit_product'),
    path('inventory/delete/<int:pk>/', views.delete_product, name='delete_product'),
    # urls.py
    path('inventory/history/', views.material_history, name='material_history'),
    path('inventory/password/', views.inventory_password_check, name='inventory_password_check'),
    # urls.py
    path('sinastar_inventory/', views.sinastar_inventory_list, name='sinastar_inventory_list'),
    path('sinastar_inventory/add/', views.add_sinastar_inventory, name='add_sinastar_inventory'),
    path("delete-selected/", views.delete_selected_products, name="delete_selected_products"),


    
    #gded
    
    path("create_order/", views.create_order, name="create_order"),
    path("in-cafe/", views.in_cafe, name="in_cafe"),

    path("orders/", views.orders_list, name="orders_list"),
    path("orders/<int:order_id>/", views.order_detail, name="order_detail"),
    path("orders/<int:order_id>/pay/", views.pay_order, name="pay_order"),
    path("orders/<int:order_id>/edit_from_list/", views.edit_order_from_list, name="edit_order_from_list"),
    path("orders/<int:order_id>/delete_from_list/", views.delete_order_from_list, name="delete_order_from_list"),

    #takeaway
    path("takeaway/", views.takeaway, name="takeaway"),
    path("takeaway/order/", views.create_takeaway_order, name="create_takeaway_order"),
    path("pending-items/", views.pending_items, name="pending_items"),
    path("mark-item-done/<int:item_id>/", views.mark_item_done, name="mark_item_done"),
    path("waiter-items/", views.waiter_items, name="waiter_items"),
    path("waiter-items/done/<int:order_id>/", views.waiter_mark_done, name="waiter_mark_done"),

    path("qeta3/", views.qeta3, name="qeta3"),
    path("qeta3/order/", views.create_qeta3_order, name="create_qeta3_order"),
    path("check_menuitem/", views.check_menuitem, name="check_menuitem"),
    path("officer-orders/", views.officer_orders, name="officer_orders"),
    path("daily-closing/", views.daily_closing, name="daily_closing"),
    path("monthly_closing/", views.monthly_closing_list, name="monthly_closing_list"),
    path("monthly_closing/create/", views.create_monthly_closing, name="create_monthly_closing"),
    path("sinastar_inventory/history/", views.sinastar_inventory_history, name="sinastar_inventory_history"),
    path("update_addition/<int:item_id>/<str:action>/", views.update_addition, name="update_addition"),

    # urls.py
    path("extra-expenses/", views.extra_expenses_view, name="extra_expenses"),
    path("extra-expenses/delete/<int:pk>/", views.delete_expense, name="delete_expense"),
    path("orders/<int:table_number>/get/", views.get_order, name="get_order"),
    path("order/<int:order_id>/print/", views.print_order, name="print_order"),

    
    path('orders/<int:order_id>/confirm/<str:method>/', views.confirm_payment, name='confirm_payment'),
    path('order/<int:order_id>/mark-paid/', views.mark_order_paid, name='mark_order_paid'),
    

    path('redirect-user/', views.redirect_user, name='redirect_user'),
    path('update_min_stock/<int:item_id>/', views.update_min_stock, name='update_min_stock'),
    path('sinastar_inventory_shortage/', views.sinastar_inventory_shortage, name='sinastar_inventory_shortage'),


    path('get_latest_orders/', views.get_latest_orders, name='get_latest_orders'),


]   
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)