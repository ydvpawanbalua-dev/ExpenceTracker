
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
import calendar

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db.models import Sum
from django.shortcuts import render, redirect
from django.utils import timezone

from .models import Expense


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = UserCreationForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'Account created successfully!')
        return redirect('dashboard')

    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect('dashboard')

    return render(request, 'login.html', {'form': form})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('login')

    return redirect('dashboard')


@login_required
def dashboard(request):
    user_expenses = Expense.objects.filter(user=request.user)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        amount = request.POST.get('amount', '').strip()
        category = request.POST.get('category', '').strip()
        date_text = request.POST.get('date', '').strip()
        notes = request.POST.get('notes', '').strip()

        if not title or not category or not date_text:
            messages.error(
                request,
                'Please fill in the title, category, and date.'
            )
            return redirect('dashboard')

        if len(category) > 50:
            messages.error(
                request,
                'Category must be 50 characters or fewer.'
            )
            return redirect('dashboard')

        try:
            amount_value = Decimal(amount)

            if not amount_value.is_finite() or amount_value <= 0:
                raise InvalidOperation

        except (InvalidOperation, ValueError, TypeError):
            messages.error(
                request,
                'Enter a valid amount greater than zero.'
            )
            return redirect('dashboard')

        try:
            try:
                expense_date = datetime.strptime(
                    date_text, '%d-%m-%Y'
                ).date()
            except ValueError:
                expense_date = datetime.strptime(
                    date_text, '%Y-%m-%d'
                ).date()

        except ValueError:
            messages.error(
                request,
                'Enter date in DD-MM-YYYY format, e.g. 27-10-2026.'
            )
            return redirect('dashboard')

        Expense.objects.create(
            user=request.user,
            title=title,
            amount=amount_value,
            category=category,
            date=expense_date,
            notes=notes,
        )

        messages.success(request, 'Expense added successfully!')
        return redirect('dashboard')

    today = timezone.localdate()

    # Current week: Monday to Sunday
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    # Current month: first day to last day
    month_start = today.replace(day=1)
    last_day = calendar.monthrange(today.year, today.month)[1]
    month_end = today.replace(day=last_day)

    total = user_expenses.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    today_total = user_expenses.filter(
        date=today
    ).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    weekly_expenses = user_expenses.filter(
        date__gte=week_start,
        date__lte=week_end
    )

    weekly_total = weekly_expenses.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    monthly_expenses = user_expenses.filter(
        date__gte=month_start,
        date__lte=month_end
    )

    monthly_total = monthly_expenses.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    # Which card did the user click?
    period = request.GET.get('period', '')

    if period == 'week':
        expenses = weekly_expenses.order_by('-date', '-id')
        history_title = 'This Week: All Expenses'
        history_tag = 'WEEKLY REPORT'

    elif period == 'month':
        expenses = monthly_expenses.order_by('-date', '-id')
        history_title = 'This Month: All Expenses'
        history_tag = 'MONTHLY REPORT'

    else:
        expenses = user_expenses.order_by('-date', '-id')[:20]
        history_title = 'Recent expenses'
        history_tag = 'HISTORY'

    return render(request, 'dashboard.html', {
        'expenses': expenses,
        'total': total,
        'today_total': today_total,
        'weekly_total': weekly_total,
        'monthly_total': monthly_total,
        'history_title': history_title,
        'history_tag': history_tag,
        'period': period,
    })
