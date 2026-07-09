from django.contrib import admin
from .models import Deposits, Withdrawals, Users, Transactions

# Unregister if they were registered differently before
try:
    admin.site.unregister(Deposits)
    admin.site.unregister(Withdrawals)
except admin.sites.NotRegistered:
    pass

@admin.register(Deposits)
class DepositsAdmin(admin.ModelAdmin):
    list_display = ('user_mobile', 'amount', 'status', 'timestamp')
    # Adding a search field can sometimes force the admin to refresh its view
    search_fields = ('user_mobile',) 

@admin.register(Withdrawals)
class WithdrawalsAdmin(admin.ModelAdmin):
    list_display = ('user_mobile', 'amount', 'status', 'timestamp')