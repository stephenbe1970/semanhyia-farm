from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

class Users(models.Model):
    mobile = models.TextField(primary_key=True)
    password = models.TextField(blank=True, null=True)
    invitation_code = models.TextField(unique=True, blank=True, null=True)
    referred_by = models.TextField(blank=True, null=True)
    balance = models.FloatField(default=0.0)
    bank_details = models.TextField(blank=True, null=True)
    real_name = models.TextField(blank=True, null=True)
    # ADD THIS LINE
    is_staff = models.BooleanField(default=False) 

    class Meta:
        managed = True
        db_table = 'users'

class Deposits(models.Model):
    id = models.AutoField(primary_key=True)
    user_mobile = models.TextField(blank=True, null=True)
    amount = models.FloatField(blank=True, null=True)
    status = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'deposits'

class Withdrawals(models.Model):
    id = models.AutoField(primary_key=True)
    user_mobile = models.TextField(blank=True, null=True)
    amount = models.FloatField(blank=True, null=True)
    status = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'withdrawals'

class Transactions(models.Model):
    id = models.AutoField(primary_key=True)
    user_mobile = models.TextField(blank=True, null=True)
    type = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    amount = models.FloatField(blank=True, null=True)
    status = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True, null=True)
    
    # REMOVE auto_now_add=True and use null=True, blank=True
    last_credited = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = True
        db_table = 'transactions'


class UserBankAccount(models.Model):
    user = models.ForeignKey('dashboard.Users', on_delete=models.CASCADE)
    real_name = models.CharField(max_length=100)
    network_name = models.CharField(max_length=50)
    account_number = models.CharField(max_length=50)