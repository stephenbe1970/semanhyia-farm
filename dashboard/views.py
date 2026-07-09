from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum
from .models import Deposits, Users, Transactions, Withdrawals, UserBankAccount
from django.db import transaction
from django.contrib.admin.views.decorators import staff_member_required
import random
import string
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import user_passes_test
from django.utils import timezone
from django.http import JsonResponse


def dashboard_view(request):
    user_mobile = request.session.get('user_mobile')
    if not user_mobile:
        return redirect('login')
    
    user = Users.objects.filter(mobile=user_mobile).first()
    if not user:
        return redirect('login')
    
    now = timezone.now()
    VIP_RATES = {"VIP1": 20, "VIP2": 35, "VIP3": 72, "VIP4": 110, "VIP5": 185, 
                 "VIP6": 400, "VIP7": 600, "VIP8": 1200, "VIP9": 2000, "VIP10": 2700}

    # Process pending income
    purchases = Transactions.objects.filter(user_mobile=user_mobile, type='purchase', status='completed')
    
    total_added = 0
    with transaction.atomic():
        for p in purchases:
            vip_name = p.description.replace("Purchased ", "")
            daily_rate = VIP_RATES.get(vip_name, 0)
            
            # Use last_credited if it exists; otherwise, default to the original purchase timestamp
            last_check = p.last_credited if p.last_credited else p.timestamp
            
            if last_check:
                # Ensure last_check is timezone aware
                if timezone.is_naive(last_check):
                    last_check = timezone.make_aware(last_check)
                
                # Calculate elapsed time in seconds
                elapsed_seconds = (now - last_check).total_seconds()
                
                # Check if at least 24 hours (86,400 seconds) have passed
                if elapsed_seconds >= 86400:
                    # Calculate how many 24-hour cycles have passed
                    cycles_passed = int(elapsed_seconds // 86400)
                    total_added += (cycles_passed * daily_rate)
                    
                    # Update last_credited to exactly the last 24-hour mark 
                    # to prevent losing partial time for the next day
                    p.last_credited = last_check + timezone.timedelta(days=cycles_passed)
                    p.save()
        
        if total_added > 0:
            user.balance += total_added
            user.save()
            # Optional: Log the income credit in Transactions
            Transactions.objects.create(
                user_mobile=user_mobile, 
                amount=total_added, 
                type='income', 
                description=f"Daily income for {purchases.count()} products",
                status='completed',
                timestamp=now
            )

    admin_count = Transactions.objects.filter(type='withdrawal', status='pending').count() if user.is_staff else 0

    vips = [
        {"name": "VIP1", "price": "GHS 120", "daily": "GHS 20 Daily income", "total": "GHS 3,600 Total income", "cycle": "Cycle: 180 days", "cost": 120.0, "disabled": False},
        {"name": "VIP2", "price": "GHS 200", "daily": "GHS 35 Daily income", "total": "GHS 6,300 Total income", "cycle": "Cycle: 180 days", "cost": 200.0, "disabled": False},
        {"name": "VIP3", "price": "GHS 400", "daily": "GHS 72 Daily income", "total": "GHS 12,960 Total income", "cycle": "Cycle: 180 days", "cost": 400.0, "disabled": False},
        {"name": "VIP4", "price": "GHS 600", "daily": "GHS 110 Daily income", "total": "GHS 19,800 Total income", "cycle": "Cycle: 180 days", "cost": 600.0, "disabled": False},
        {"name": "VIP5", "price": "GHS 1000", "daily": "GHS 185 Daily income", "total": "GHS 33,300 Total income", "cycle": "Cycle: 180 days", "cost": 1000.0, "disabled": True},
        {"name": "VIP6", "price": "GHS 2000", "daily": "GHS 400 Daily income", "total": "GHS 72,000 Total income", "cycle": "Cycle: 180 days", "cost": 2000.0, "disabled": True},
        {"name": "VIP7", "price": "GHS 3000", "daily": "GHS 600 Daily income", "total": "GHS 108,000 Total income", "cycle": "Cycle: 180 days", "cost": 3000.0, "disabled": True},
        {"name": "VIP8", "price": "GHS 5000", "daily": "GHS 1200 Daily income", "total": "GHS 216,000 Total income", "cycle": "Cycle: 180 days", "cost": 5000.0, "disabled": True},
        {"name": "VIP9", "price": "GHS 8000", "daily": "GHS 2000 Daily income", "total": "GHS 360,000 Total income", "cycle": "Cycle: 180 days", "cost": 8000.0, "disabled": True},
        {"name": "VIP10", "price": "GHS 10000", "daily": "GHS 2700 Daily income", "total": "GHS 486,000 Total income", "cycle": "Cycle: 180 days", "cost": 10000.0, "disabled": True},
    ]

    return render(request, 'dashboard.html', {'user': user, 'balance': user.balance, 'admin_count': admin_count, 'vips': vips, 'user_mobile': user_mobile})
    
def buy_vip_view(request, vip_name):
    if request.method == 'POST':
        user_mobile = request.session.get('user_mobile', '0505162314')
        
        # 1. Map your VIP names to their specific costs
        vip_costs = {
            "VIP1": 120.0, "VIP2": 200.0, "VIP3": 400.0, "VIP4": 600.0
        }
        
        cost = vip_costs.get(vip_name, 0)
        user = Users.objects.filter(mobile=user_mobile).first()

        # 2. Form Validation: Check if user exists and has enough balance
        if not user:
            messages.error(request, "User account not found.")
            return redirect('dashboard')

        if user.balance >= cost:
            try:
                with transaction.atomic():
                    # Deduct balance
                    user.balance -= cost
                    user.save()
                    
                    # Save transaction record to database
                    Transactions.objects.create(
                        user_mobile=user_mobile,
                        amount=cost,
                        type='purchase',
                        description=f"Purchased {vip_name}",
                        status='completed'
                    )
                messages.success(request, f"Successfully purchased {vip_name}!")
            except Exception as e:
                messages.error(request, "An error occurred during purchase.")
        else:
            # Notify user if they cannot afford it
            messages.error(request, "Insufficient balance.")
            
        return redirect('dashboard')
    
    return redirect('dashboard')
def generate_unique_code():
    """Generates a random 6-character uppercase alphanumeric code."""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        # Ensure the code is truly unique in the database
        if not Users.objects.filter(invitation_code=code).exists():
            return code

def register_view(request):
    # Capture referral code from URL (e.g., /register/?ref=TQ6SMP)
    referral_code = request.GET.get('ref')

    if request.method == 'POST':
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        repeat_password = request.POST.get('repeat_password')

        # 1. Validation: Check if passwords match
        if password != repeat_password:
            messages.error(request, "Passwords do not match.")
            return redirect(f'/register/?ref={referral_code or ""}')

        # 2. Validation: Check if mobile is already registered
        if Users.objects.filter(mobile=mobile).exists():
            messages.error(request, "This mobile number is already registered.")
            return redirect(f'/register/?ref={referral_code or ""}')

        # 3. Create the user and the transaction record
        new_user = Users.objects.create(
            mobile=mobile,
            password=password,
            balance=50.0,
            invitation_code=generate_unique_code(),
            referred_by=referral_code
        )
        
        # Add a record to Transactions so it shows in Account Records
        Transactions.objects.create(
            user_mobile=mobile,
            amount=50.0,
            type='bonus',
            status='completed',
            description="Registration Bonus"
        )

        messages.success(request, "Account created! You have received a 50 GHS bonus. Please log in.")
        return redirect('login')

    return render(request, 'register.html', {'ref_code': referral_code})

    return render(request, 'register.html')
def login_view(request):
    if request.method == 'POST':
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        
        # Check if user exists
        user = Users.objects.filter(mobile=mobile, password=password).first()
        
        if user:
            # Successfully found user
            request.session['user_mobile'] = user.mobile # Ensure this matches
            return redirect('dashboard')
        else:
            # User not found or wrong password
            messages.error(request, "Invalid mobile number or password.")
            return redirect('login') # Stay on login but show error
            
    return render(request, 'login.html')

def recharge_view(request):
    user_mobile = request.session.get('user_mobile')
    
    # 1. Ensure user is logged in
    if not user_mobile: 
        return redirect('login')
    
    # 2. Handle POST request (Form Submission)
    if request.method == 'POST':
        amount = request.POST.get('amount')
        try:
            val = float(amount)
            if val >= 120:
                Deposits.objects.create(
                    user_mobile=user_mobile, 
                    amount=val, 
                    status='pending', 
                    timestamp=timezone.now()
                )
                messages.success(request, "Recharge request submitted successfully! Pending approval.")
            else:
                messages.error(request, "Minimum recharge amount is GHS 120.")
        except (ValueError, TypeError):
            messages.error(request, "Invalid amount entered.")
        
        return redirect('recharge')

    # 3. Handle GET request (Page Loading)
    try:
        user = Users.objects.get(mobile=user_mobile)
        # Fetch last successful deposit for display
        last_dep = Deposits.objects.filter(user_mobile=user_mobile, status='completed').last()
        last_recharge = last_dep.amount if last_dep else 0.0
    except Users.DoesNotExist:
        return redirect('login')
    
    context = {
        'balance': user.balance,
        'last_recharge': last_recharge
    }
    
    return render(request, 'recharge.html', context)

@staff_member_required
def confirm_recharge_view(request, deposit_id):
    try:
        deposit = Deposits.objects.get(id=deposit_id)
        if deposit.status == 'pending':
            with transaction.atomic():
                user = Users.objects.get(mobile=deposit.user_mobile)
                user.balance += deposit.amount
                user.save()
                
                deposit.status = 'completed'
                deposit.save()
                messages.success(request, f"Confirmed recharge for {user.mobile}")
    except (Deposits.DoesNotExist, Users.DoesNotExist):
        messages.error(request, "Transaction or User not found.")
            
    return redirect('admin_deposit_list')

def withdraw_view(request):
    user_mobile = request.session.get('user_mobile')
    user = Users.objects.filter(mobile=user_mobile).first()
    
    # Calculate Total Withdrawn (for the template variable)
    total_withdrawn = Withdrawals.objects.filter(
        user_mobile=user_mobile, status='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0.0

    # Get Bank Info
    bank_info = UserBankAccount.objects.filter(user=user).first()

    if request.method == 'POST':
        amount = float(request.POST.get('amount', 0))
        # Ensure user has enough balance and meets minimum withdrawal
        if amount >= 20 and user.balance >= amount:
            with transaction.atomic():
                user.balance -= amount
                user.save()
                Withdrawals.objects.create(user_mobile=user_mobile, amount=amount, status='pending', timestamp=timezone.now())
                Transactions.objects.create(user_mobile=user_mobile, amount=amount, type='withdrawal', status='pending', timestamp=timezone.now())
            messages.success(request, "Withdrawal request submitted successfully.")
            return redirect('withdraw')
        else:
            messages.error(request, "Insufficient funds or amount less than GHS 20.")
            
    return render(request, 'withdraw.html', {
        'balance': user.balance,
        'total_withdrawn': total_withdrawn,
        'bank_info': bank_info
    })
from django.shortcuts import render, redirect
from django.utils import timezone
from .models import Transactions

def income_view(request):
    mobile = request.session.get('user_mobile')
    if not mobile:
        return redirect('login')
    
    # Filter only for purchases
    purchases = Transactions.objects.filter(user_mobile=mobile, type='purchase').order_by('-timestamp')
    now = timezone.now()
    
    # Complete list of VIP daily rates
    VIP_DATA = {
        "VIP1": 20, 
        "VIP2": 35, 
        "VIP3": 72, 
        "VIP4": 110, 
        "VIP5": 185, 
        "VIP6": 400, 
        "VIP7": 600, 
        "VIP8": 1200, 
        "VIP9": 2000, 
        "VIP10": 2700
    }
    
    total_interest_earned = 0
    
    for p in purchases:
        # Extracts VIP name from description (e.g., "Purchased VIP1" -> "VIP1")
        vip_name = p.description.replace("Purchased ", "")
        daily_rate = VIP_DATA.get(vip_name, 0)
        
        # Determine the start time for the 24-hour cycle
        start_date = p.last_credited if p.last_credited else p.timestamp
        
        if start_date:
            # Make sure it's timezone aware
            if timezone.is_naive(start_date):
                start_date = timezone.make_aware(start_date)
            
            # Calculate elapsed time and pay based on 24-hour cycles
            elapsed_seconds = (now - start_date).total_seconds()
            if elapsed_seconds >= 86400: # 86400 seconds = 24 hours
                cycles = int(elapsed_seconds // 86400)
                total_interest_earned += (cycles * daily_rate)

    return render(request, 'income.html', {
        'purchases': purchases, 
        'quantity_purchased': purchases.count(), 
        'total_earned': total_interest_earned 
    })

def team_details_view(request):
    mobile = request.session.get('user_mobile')
    if not mobile:
        return redirect('login')
    
    team_members = Users.objects.filter(referred_by=mobile)
    
    context = {
        'team_members': team_members,
    }
    return render(request, 'team_details.html', context)

# --- ADD THIS HELPER FUNCTION AT THE TOP LEVEL ---
def get_total_investment(mobile_list):
    """Calculates the sum of all 'purchase' transactions for a list of mobiles."""
    return Transactions.objects.filter(
        user_mobile__in=mobile_list, 
        type='purchase'
    ).aggregate(Sum('amount'))['amount__sum'] or 0

# --- REPLACE YOUR OLD team_view WITH THIS ONE ---
def team_view(request):
    user_mobile = request.session.get('user_mobile')
    if not user_mobile:
        return redirect('login')

    user = Users.objects.filter(mobile=user_mobile).first()
    if not user:
        return redirect('login')
    
    # 1. Get current user's invite code
    user_code = user.invitation_code 
    
    # 2. Get L1, L2, L3 members
    l1 = Users.objects.filter(referred_by=user_code)
    l1_mobiles = l1.values_list('mobile', flat=True)
    l1_codes = l1.values_list('invitation_code', flat=True)
    
    l2 = Users.objects.filter(referred_by__in=l1_codes)
    l2_mobiles = l2.values_list('mobile', flat=True)
    l2_codes = l2.values_list('invitation_code', flat=True)
    
    l3 = Users.objects.filter(referred_by__in=l2_codes)
    l3_mobiles = l3.values_list('mobile', flat=True)
    
    # 3. Calculate Income using the helper function
    l1_inc = get_total_investment(l1_mobiles)
    l2_inc = get_total_investment(l2_mobiles)
    l3_inc = get_total_investment(l3_mobiles)
    
    context = {
        'invitation_code': user_code,
        'l1_count': l1.count(), 'l1_income': l1_inc * 0.30,
        'l2_count': l2.count(), 'l2_income': l2_inc * 0.02,
        'l3_count': l3.count(), 'l3_income': l3_inc * 0.01,
        'total_guests': l1.count() + l2.count() + l3.count(),
        'total_commission': (l1_inc * 0.30) + (l2_inc * 0.02) + (l3_inc * 0.01)
    }
    return render(request, 'team.html', context)

def mine_view(request):
    mobile = request.session.get('user_mobile')
    if not mobile: return redirect('login')
    
    user = Users.objects.filter(mobile=mobile).first()
    total_accumulated = Transactions.objects.filter(
        user_mobile=mobile, type='purchase'
    ).aggregate(Sum('amount'))['amount__sum'] or 0.0
    
    context = {
        'user': user,
        'mobile': mobile,
        'total_accumulated': total_accumulated,
        'balance': user.balance if user else 0.0,
    }
    return render(request, 'mine.html', context)

def account_records_view(request):
    # Retrieve the current user's mobile (adjust based on your login logic)
    user_mobile = request.session.get('user_mobile')
    
    payments = Transactions.objects.filter(user_mobile=user_mobile, type='purchase').order_by('-timestamp')
    withdrawals = Transactions.objects.filter(user_mobile=user_mobile, type='withdrawal').order_by('-timestamp')
    
    return render(request, 'account_records.html', {
        'payments': payments, 
        'withdrawals': withdrawals
    })

def bank_management_view(request):
    # 1. Get mobile from session to match your other views
    mobile = request.session.get('user_mobile')
    if not mobile:
        return redirect('login')
    
    # 2. Fetch your custom user
    user = Users.objects.filter(mobile=mobile).first()
    if not user:
        return redirect('login')
    
    # 3. Get or initialize bank info
    try:
        # Note: Your UserBankAccount model must link to 'Users', not 'User'
        bank_info = UserBankAccount.objects.get(user=user)
    except UserBankAccount.DoesNotExist:
        bank_info = None

    if request.method == 'POST':
        real_name = request.POST.get('real_name')
        network = request.POST.get('network_name')
        acc_num = request.POST.get('account_number')
        
        # Save or update using the custom 'user' object
        UserBankAccount.objects.update_or_create(
            user=user,
            defaults={'real_name': real_name, 'network_name': network, 'account_number': acc_num}
        )
        return redirect('mine') 
        
    return render(request, 'bank_management.html', {'bank_info': bank_info})
def about_view(request):
    return render(request, 'about.html') # Or just return HttpResponse("About page")

def rules_view(request):
    vips = [
        {"name": "VIP1", "price": "120", "daily": "20", "cycle": "180 days", "total": "3,600"},
        {"name": "VIP2", "price": "200", "daily": "35", "cycle": "180 days", "total": "6,300"},
        {"name": "VIP3", "price": "400", "daily": "72", "cycle": "180 days", "total": "12,960"},
        {"name": "VIP4", "price": "600", "daily": "110", "cycle": "180 days", "total": "19,800"},
        {"name": "VIP5", "price": "1,000", "daily": "185", "cycle": "180 days", "total": "33,300"},
        {"name": "VIP6", "price": "2,000", "daily": "400", "cycle": "180 days", "total": "72,000"},
        {"name": "VIP7", "price": "3,000", "daily": "600", "cycle": "180 days", "total": "108,000"},
        {"name": "VIP8", "price": "5,000", "daily": "1,200", "cycle": "180 days", "total": "216,000"},
        {"name": "VIP9", "price": "8,000", "daily": "2,000", "cycle": "180 days", "total": "360,000"},
        {"name": "VIP10", "price": "10,000", "daily": "2,700", "cycle": "180 days", "total": "486,000"},
    ]
    return render(request, 'rules.html', {'vips': vips})

def service_view(request):
    return render(request, 'service.html')

def buy_vip_view(request, vip_name):
    if request.method == 'POST':
        user_mobile = request.session.get('user_mobile')
        # Map your VIP prices
        vip_costs = {"VIP1": 120.0, "VIP2": 200.0, "VIP3": 400.0, "VIP4": 600.0}
        cost = vip_costs.get(vip_name, 0)
        user = Users.objects.filter(mobile=user_mobile).first()

        if not user or user.balance < cost:
            return JsonResponse({'status': 'error', 'message': 'Insufficient balance'})

        try:
            with transaction.atomic():
                user.balance -= cost
                user.save()
                Transactions.objects.create(
                    user_mobile=user_mobile, amount=cost, 
                    type='purchase', description=f"Purchased {vip_name}", status='completed'
                )
            return JsonResponse({'status': 'success', 'message': 'Purchase successful'})
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'An error occurred'})
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

def logout_view(request):
    request.session.flush() # This clears the entire session data (including mobile number)
    return redirect('login')

# ... (all your other views)

@staff_member_required
def admin_panel_view(request):
    # 1. Handle POST actions for both deposits and withdrawals
    if request.method == 'POST':
        action = request.POST.get('action') 
        
        # Handle Deposit Actions
        if 'deposit_id' in request.POST:
            dep_id = request.POST.get('deposit_id')
            deposit = get_object_or_404(Deposits, id=dep_id)
            if action == 'approve_dep':
                with transaction.atomic():
                    user = Users.objects.get(mobile=deposit.user_mobile)
                    user.balance += deposit.amount
                    user.save()
                    deposit.status = 'completed'
                    deposit.save()
            elif action == 'reject_dep':
                deposit.status = 'rejected'
                deposit.save()

        # Handle Withdrawal Actions
        elif 'withdraw_id' in request.POST:
            with_id = request.POST.get('withdraw_id')
            withdrawal = get_object_or_404(Withdrawals, id=with_id)
            if action == 'approve_with':
                withdrawal.status = 'completed'
                withdrawal.save()
            elif action == 'reject_with':
                with transaction.atomic():
                    user = Users.objects.get(mobile=withdrawal.user_mobile)
                    user.balance += withdrawal.amount
                    user.save()
                    withdrawal.status = 'rejected'
                    withdrawal.save()
        
        return redirect('admin_panel')

    # 2. GET request: Fetch all pending data for the dashboard
    context = {
        'deposits': Deposits.objects.filter(status='pending').order_by('-timestamp'),
        'withdrawals': Withdrawals.objects.filter(status='pending').order_by('-timestamp'),
    }
    return render(request, 'admin_panel.html', context)

def admin_login_view(request):
    if request.method == 'POST':
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        user = authenticate(request, mobile=mobile, password=password)
        if user and user.is_staff:
            login(request, user)
            return redirect('admin_panel') # Changed to redirect to admin_panel
        else:
            return render(request, 'admin_login.html', {'error': 'Invalid credentials'})
    return render(request, 'admin_login.html')
    
def buy_vip_view(request, vip_name):
    if request.method == 'POST':
        user_mobile = request.session.get('user_mobile', '0505162314')
        
        # 1. Map your VIP names to their specific costs
        vip_costs = {
            "VIP1": 120.0, "VIP2": 200.0, "VIP3": 400.0, "VIP4": 600.0
        }
        
        cost = vip_costs.get(vip_name, 0)
        user = Users.objects.filter(mobile=user_mobile).first()

        # 2. Form Validation: Check if user exists and has enough balance
        if not user:
            messages.error(request, "User account not found.")
            return redirect('dashboard')

        if user.balance >= cost:
            try:
                with transaction.atomic():
                    # Deduct balance
                    user.balance -= cost
                    user.save()
                    
                    # Save transaction record to database
                    Transactions.objects.create(
                        user_mobile=user_mobile,
                        amount=cost,
                        type='purchase',
                        description=f"Purchased {vip_name}",
                        status='completed'
                    )
                messages.success(request, f"Successfully purchased {vip_name}!")
            except Exception as e:
                messages.error(request, "An error occurred during purchase.")
        else:
            # Notify user if they cannot afford it
            messages.error(request, "Insufficient balance.")
            
        return redirect('dashboard')
    
    return redirect('dashboard')
def generate_unique_code():
    """Generates a random 6-character uppercase alphanumeric code."""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        # Ensure the code is truly unique in the database
        if not Users.objects.filter(invitation_code=code).exists():
            return code

def register_view(request):
    # Capture referral code from URL (e.g., /register/?ref=TQ6SMP)
    referral_code = request.GET.get('ref')

    if request.method == 'POST':
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        repeat_password = request.POST.get('repeat_password')

        # 1. Validation: Check if passwords match
        if password != repeat_password:
            messages.error(request, "Passwords do not match.")
            return redirect(f'/register/?ref={referral_code or ""}')

        # 2. Validation: Check if mobile is already registered
        if Users.objects.filter(mobile=mobile).exists():
            messages.error(request, "This mobile number is already registered.")
            return redirect(f'/register/?ref={referral_code or ""}')

        # 3. Create the user and the transaction record
        new_user = Users.objects.create(
            mobile=mobile,
            password=password,
            balance=50.0,
            invitation_code=generate_unique_code(),
            referred_by=referral_code
        )
        
        # Add a record to Transactions so it shows in Account Records
        Transactions.objects.create(
            user_mobile=mobile,
            amount=50.0,
            type='bonus',
            status='completed',
            description="Registration Bonus"
        )

        messages.success(request, "Account created! You have received a 50 GHS bonus. Please log in.")
        return redirect('login')

    return render(request, 'register.html', {'ref_code': referral_code})

    return render(request, 'register.html')
def login_view(request):
    if request.method == 'POST':
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        
        # Check if user exists
        user = Users.objects.filter(mobile=mobile, password=password).first()
        
        if user:
            # Successfully found user
            request.session['user_mobile'] = user.mobile # Ensure this matches
            return redirect('dashboard')
        else:
            # User not found or wrong password
            messages.error(request, "Invalid mobile number or password.")
            return redirect('login') # Stay on login but show error
            
    return render(request, 'login.html')

def recharge_view(request):
    user_mobile = request.session.get('user_mobile')
    
    # 1. Ensure user is logged in
    if not user_mobile: 
        return redirect('login')
    
    # 2. Handle POST request (Form Submission)
    if request.method == 'POST':
        amount = request.POST.get('amount')
        try:
            val = float(amount)
            if val >= 120:
                Deposits.objects.create(
                    user_mobile=user_mobile, 
                    amount=val, 
                    status='pending', 
                    timestamp=timezone.now()
                )
                messages.success(request, "Recharge request submitted successfully! Pending approval.")
            else:
                messages.error(request, "Minimum recharge amount is GHS 120.")
        except (ValueError, TypeError):
            messages.error(request, "Invalid amount entered.")
        
        return redirect('recharge')

    # 3. Handle GET request (Page Loading)
    try:
        user = Users.objects.get(mobile=user_mobile)
        # Fetch last successful deposit for display
        last_dep = Deposits.objects.filter(user_mobile=user_mobile, status='completed').last()
        last_recharge = last_dep.amount if last_dep else 0.0
    except Users.DoesNotExist:
        return redirect('login')
    
    context = {
        'balance': user.balance,
        'last_recharge': last_recharge
    }
    
    return render(request, 'recharge.html', context)

@staff_member_required
def confirm_recharge_view(request, deposit_id):
    try:
        deposit = Deposits.objects.get(id=deposit_id)
        if deposit.status == 'pending':
            with transaction.atomic():
                user = Users.objects.get(mobile=deposit.user_mobile)
                user.balance += deposit.amount
                user.save()
                
                deposit.status = 'completed'
                deposit.save()
                messages.success(request, f"Confirmed recharge for {user.mobile}")
    except (Deposits.DoesNotExist, Users.DoesNotExist):
        messages.error(request, "Transaction or User not found.")
            
    return redirect('admin_deposit_list')

def withdraw_view(request):
    user_mobile = request.session.get('user_mobile')
    if not user_mobile:
        return redirect('login')
        
    user = Users.objects.filter(mobile=user_mobile).first()
    bank_info = UserBankAccount.objects.filter(user=user).first()
    
    # 1. Fetch withdrawal history for the template
    # We filter by 'withdrawal' type to get the list for the UI
    withdrawals = Transactions.objects.filter(
        user_mobile=user_mobile, 
        type='withdrawal'
    ).order_by('-timestamp')
    
    # 2. Calculate Total Withdrawn (only completed ones)
    total_withdrawn = Transactions.objects.filter(
        user_mobile=user_mobile, 
        type='withdrawal', 
        status='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0.0

    if request.method == 'POST':
        amount = float(request.POST.get('amount', 0))
        
        if amount >= 20 and user.balance >= amount:
            with transaction.atomic():
                user.balance -= amount
                user.save()
                
                # Record in Withdrawals model
                Withdrawals.objects.create(
                    user_mobile=user_mobile, 
                    amount=amount, 
                    status='pending', 
                    timestamp=timezone.now()
                )
                
                # Record in Transactions model (this is what your UI displays)
                Transactions.objects.create(
                    user_mobile=user_mobile, 
                    amount=amount, 
                    type='withdrawal', 
                    status='pending', 
                    timestamp=timezone.now()
                )
            messages.success(request, "Withdrawal request submitted successfully.")
            return redirect('withdraw')
        else:
            messages.error(request, "Insufficient funds or amount less than GHS 20.")
            
    return render(request, 'withdraw.html', {
        'balance': user.balance,
        'total_withdrawn': total_withdrawn,
        'bank_info': bank_info,
        'withdrawals': withdrawals # Pass the history to the template
    })
    return render(request, 'withdraw.html', {
        'balance': user.balance,
        'total_withdrawn': total_withdrawn,
        'bank_info': bank_info,
        'withdrawals': withdrawals # Pass the history to the template
    })

def team_details_view(request):
    mobile = request.session.get('user_mobile')
    if not mobile:
        return redirect('login')
    
    team_members = Users.objects.filter(referred_by=mobile)
    
    context = {
        'team_members': team_members,
    }
    return render(request, 'team_details.html', context)

# --- ADD THIS HELPER FUNCTION AT THE TOP LEVEL ---
def get_total_investment(mobile_list):
    """Calculates the sum of all 'purchase' transactions for a list of mobiles."""
    return Transactions.objects.filter(
        user_mobile__in=mobile_list, 
        type='purchase'
    ).aggregate(Sum('amount'))['amount__sum'] or 0

# --- REPLACE YOUR OLD team_view WITH THIS ONE ---
def team_view(request):
    user_mobile = request.session.get('user_mobile')
    if not user_mobile:
        return redirect('login')

    user = Users.objects.filter(mobile=user_mobile).first()
    if not user:
        return redirect('login')
    
    # 1. Get current user's invite code
    user_code = user.invitation_code 
    
    # 2. Get L1, L2, L3 members
    l1 = Users.objects.filter(referred_by=user_code)
    l1_mobiles = l1.values_list('mobile', flat=True)
    l1_codes = l1.values_list('invitation_code', flat=True)
    
    l2 = Users.objects.filter(referred_by__in=l1_codes)
    l2_mobiles = l2.values_list('mobile', flat=True)
    l2_codes = l2.values_list('invitation_code', flat=True)
    
    l3 = Users.objects.filter(referred_by__in=l2_codes)
    l3_mobiles = l3.values_list('mobile', flat=True)
    
    # 3. Calculate Income using the helper function
    l1_inc = get_total_investment(l1_mobiles)
    l2_inc = get_total_investment(l2_mobiles)
    l3_inc = get_total_investment(l3_mobiles)
    
    context = {
        'invitation_code': user_code,
        'l1_count': l1.count(), 'l1_income': l1_inc * 0.30,
        'l2_count': l2.count(), 'l2_income': l2_inc * 0.02,
        'l3_count': l3.count(), 'l3_income': l3_inc * 0.01,
        'total_guests': l1.count() + l2.count() + l3.count(),
        'total_commission': (l1_inc * 0.30) + (l2_inc * 0.02) + (l3_inc * 0.01)
    }
    return render(request, 'team.html', context)

def mine_view(request):
    mobile = request.session.get('user_mobile')
    if not mobile: return redirect('login')
    
    user = Users.objects.filter(mobile=mobile).first()
    total_accumulated = Transactions.objects.filter(
        user_mobile=mobile, type='purchase'
    ).aggregate(Sum('amount'))['amount__sum'] or 0.0
    
    context = {
        'user': user,
        'mobile': mobile,
        'total_accumulated': total_accumulated,
        'balance': user.balance if user else 0.0,
    }
    return render(request, 'mine.html', context)

def account_records_view(request):
    # Retrieve the current user's mobile (adjust based on your login logic)
    user_mobile = request.session.get('user_mobile')
    
    payments = Transactions.objects.filter(user_mobile=user_mobile, type='purchase').order_by('-timestamp')
    withdrawals = Transactions.objects.filter(user_mobile=user_mobile, type='withdrawal').order_by('-timestamp')
    
    return render(request, 'account_records.html', {
        'payments': payments, 
        'withdrawals': withdrawals
    })

def bank_management_view(request):
    # 1. Get mobile from session to match your other views
    mobile = request.session.get('user_mobile')
    if not mobile:
        return redirect('login')
    
    # 2. Fetch your custom user
    user = Users.objects.filter(mobile=mobile).first()
    if not user:
        return redirect('login')
    
    # 3. Get or initialize bank info
    try:
        # Note: Your UserBankAccount model must link to 'Users', not 'User'
        bank_info = UserBankAccount.objects.get(user=user)
    except UserBankAccount.DoesNotExist:
        bank_info = None

    if request.method == 'POST':
        real_name = request.POST.get('real_name')
        network = request.POST.get('network_name')
        acc_num = request.POST.get('account_number')
        
        # Save or update using the custom 'user' object
        UserBankAccount.objects.update_or_create(
            user=user,
            defaults={'real_name': real_name, 'network_name': network, 'account_number': acc_num}
        )
        return redirect('mine') 
        
    return render(request, 'bank_management.html', {'bank_info': bank_info})
def about_view(request):
    return render(request, 'about.html') # Or just return HttpResponse("About page")

def rules_view(request):
    vips = [
        {"name": "VIP1", "price": "120", "daily": "20", "cycle": "180 days", "total": "3,600"},
        {"name": "VIP2", "price": "200", "daily": "35", "cycle": "180 days", "total": "6,300"},
        {"name": "VIP3", "price": "400", "daily": "72", "cycle": "180 days", "total": "12,960"},
        {"name": "VIP4", "price": "600", "daily": "110", "cycle": "180 days", "total": "19,800"},
        {"name": "VIP5", "price": "1,000", "daily": "185", "cycle": "180 days", "total": "33,300"},
        {"name": "VIP6", "price": "2,000", "daily": "400", "cycle": "180 days", "total": "72,000"},
        {"name": "VIP7", "price": "3,000", "daily": "600", "cycle": "180 days", "total": "108,000"},
        {"name": "VIP8", "price": "5,000", "daily": "1,200", "cycle": "180 days", "total": "216,000"},
        {"name": "VIP9", "price": "8,000", "daily": "2,000", "cycle": "180 days", "total": "360,000"},
        {"name": "VIP10", "price": "10,000", "daily": "2,700", "cycle": "180 days", "total": "486,000"},
    ]
    return render(request, 'rules.html', {'vips': vips})

def service_view(request):
    return render(request, 'service.html')

def buy_vip_view(request, vip_name):
    if request.method == 'POST':
        user_mobile = request.session.get('user_mobile')
        # Map your VIP prices
        vip_costs = {"VIP1": 120.0, "VIP2": 200.0, "VIP3": 400.0, "VIP4": 600.0}
        cost = vip_costs.get(vip_name, 0)
        user = Users.objects.filter(mobile=user_mobile).first()

        if not user or user.balance < cost:
            return JsonResponse({'status': 'error', 'message': 'Insufficient balance'})

        try:
            with transaction.atomic():
                user.balance -= cost
                user.save()
                Transactions.objects.create(
                    user_mobile=user_mobile, amount=cost, 
                    type='purchase', description=f"Purchased {vip_name}", status='completed'
                )
            return JsonResponse({'status': 'success', 'message': 'Purchase successful'})
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'An error occurred'})
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

def logout_view(request):
    request.session.flush() # This clears the entire session data (including mobile number)
    return redirect('login')

# ... (all your other views)

@staff_member_required
def admin_panel_view(request):
    # 1. Handle POST actions for both deposits and withdrawals
    if request.method == 'POST':
        action = request.POST.get('action') 
        
        # Handle Deposit Actions
        if 'deposit_id' in request.POST:
            dep_id = request.POST.get('deposit_id')
            deposit = get_object_or_404(Deposits, id=dep_id)
            if action == 'approve_dep':
                with transaction.atomic():
                    user = Users.objects.get(mobile=deposit.user_mobile)
                    user.balance += deposit.amount
                    user.save()
                    deposit.status = 'completed'
                    deposit.save()
            elif action == 'reject_dep':
                deposit.status = 'rejected'
                deposit.save()

        # Handle Withdrawal Actions
        elif 'withdraw_id' in request.POST:
            with_id = request.POST.get('withdraw_id')
            withdrawal = get_object_or_404(Withdrawals, id=with_id)
            
            # Sync with Transactions model
            # We match by timestamp and mobile, as these are unique for each request
            txn = Transactions.objects.filter(
                user_mobile=withdrawal.user_mobile, 
                timestamp=withdrawal.timestamp, 
                type='withdrawal'
            ).first()

            if action == 'approve_with':
                with transaction.atomic():
                    withdrawal.status = 'completed'
                    withdrawal.save()
                    if txn:
                        txn.status = 'completed'
                        txn.save()
            
            elif action == 'reject_with':
                with transaction.atomic():
                    user = Users.objects.get(mobile=withdrawal.user_mobile)
                    user.balance += withdrawal.amount
                    user.save()
                    withdrawal.status = 'rejected'
                    withdrawal.save()
                    if txn:
                        txn.status = 'rejected'
                        txn.save()
        
        return redirect('admin_panel')

    # 2. GET request: Fetch all pending data
    context = {
        'deposits': Deposits.objects.filter(status='pending').order_by('-timestamp'),
        'withdrawals': Withdrawals.objects.filter(status='pending').order_by('-timestamp'),
    }
    return render(request, 'admin_panel.html', context)

def admin_login_view(request):
    if request.method == 'POST':
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        user = authenticate(request, mobile=mobile, password=password)
        if user and user.is_staff:
            login(request, user)
            return redirect('admin_panel') # Changed to redirect to admin_panel
        else:
            return render(request, 'admin_login.html', {'error': 'Invalid credentials'})
    return render(request, 'admin_login.html')

def account_records_view(request):
    user_mobile = request.session.get('user_mobile')
    
    # Make sure you are fetching the Deposits for the current user
    payments = Deposits.objects.filter(user_mobile=user_mobile).order_by('-timestamp')
    withdrawals = Transactions.objects.filter(user_mobile=user_mobile, type='withdrawal').order_by('-timestamp')
    
    return render(request, 'account_records.html', {
        'payments': payments,      # MUST be named 'payments' to match the template
        'withdrawals': withdrawals
    })