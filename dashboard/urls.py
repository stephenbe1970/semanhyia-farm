from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('buy-vip/<str:vip_name>/', views.buy_vip_view, name='buy_vip'),
    path('income/', views.income_view, name='income'),
    path('team/', views.team_view, name='team'),
    path('team/details/', views.team_details_view, name='team_details'),
    path('mine/', views.mine_view, name='mine'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('recharge/', views.recharge_view, name='recharge'),
    path('withdraw/', views.withdraw_view, name='withdraw'),
    # Use only one path for your records page to keep navigation clean
    path('account-details/', views.account_records_view, name='account_records'),
    path('bank-management/', views.bank_management_view, name='bank_management'),
    path('about/', views.about_view, name='about_us'),
    path('rules/', views.rules_view, name='platform_rules'),
    path('service/', views.service_view, name='customer_service'),
    path('logout/', views.logout_view, name='logout'),
    path('admin-login/', views.admin_login_view, name='admin_login'),
    path('admin-panel/', views.admin_panel_view, name='admin_panel'),
    path('account-details/', views.account_records_view, name='account_records'),
    path('records/', views.account_records_view, name='records'),
]