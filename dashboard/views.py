from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from .forms import CustomPasswordChangeForm, UploadFileForm
from django.contrib.auth import update_session_auth_hash
import pandas as pd
from zipfile import ZipFile
from .models import Transaction, Categories
from django.db.models import Sum, F
from django.core.serializers.json import DjangoJSONEncoder
import json
import csv
from openpyxl import Workbook

# Create your views here.

def loginPage(request):
    page = 'login'
    if request.user.is_authenticated:
        return redirect("index")  # Redirecting to the 'index' view as per your previous code

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        try:
            user = User.objects.get(username=username)

        except User.DoesNotExist:
            messages.error(request, "User does not exist")
        
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("dashboard:index")
        else:
            messages.error(request, "Username OR password is incorrect.")

    return render(request, 'dashboard/login.html') 

@login_required
def logoutUser(request):
    logout(request)
    return redirect('dashboard:login') 

@login_required
def index(request):
    # Fetching income data
    incomes = Transaction.objects.filter(user=request.user, type="Income") \
                .values('category__name', 'transaction_date', 'description', 'title') \
                .annotate(total=Sum('amount'))

    # Fetching expense data
    expenses = Transaction.objects.filter(user=request.user, type="Expense") \
                .values('category__name', 'transaction_date', 'description', 'title') \
                .annotate(total=Sum('amount'))

    # Convert Decimals to string
    for item in incomes:
        item['total'] = str(item['total'])

    for item in expenses:
        item['total'] = str(item['total'])

    # Convert data to JSON string
    incomes_json = json.dumps(list(incomes), cls=DjangoJSONEncoder)
    expenses_json = json.dumps(list(expenses), cls=DjangoJSONEncoder)

    context = {
        "incomes_json": incomes_json,
        "expenses_json": expenses_json
    }

    return render(request, "dashboard/index.html", context)



def register(request):
    # Redirecting authenticated users away from the registration page
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard:index')
            else:
                messages.error(request, "There was an error with your registration. Please try again.")
    else:
        form = UserCreationForm()
    return render(request, 'dashboard/register.html', {'form': form})


@login_required
def change_password(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important, to update the session with the new password
            messages.success(request, 'Your password was successfully updated!')
            return redirect('dashboard:index')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = CustomPasswordChangeForm(request.user)
    return render(request, 'dashboard/password_change.html', {'form': form})

@login_required
def upload_transaction_data(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            data_file = request.FILES['file']
            file_extension = data_file.name.split('.')[-1].lower()

            df = None

            # Handle Excel files
            if file_extension == 'xlsx':
                df = pd.read_excel(data_file, engine='openpyxl')

            # Handle CSV files
            elif file_extension == 'csv':
                df = pd.read_csv(data_file)

            # Handle ZIP files
            elif file_extension == 'zip':
                with ZipFile(data_file, 'r') as zip_ref:
                    # Assuming there's only one file in the ZIP archive
                    with zip_ref.open(zip_ref.namelist()[0]) as file:
                        inner_file_extension = zip_ref.namelist()[0].split('.')[-1].lower()
                        if inner_file_extension == 'xlsx':
                            df = pd.read_excel(file, engine='openpyxl')
                        elif inner_file_extension == 'csv':
                            df = pd.read_csv(file)
                        else:
                            messages.error(request, "Unsupported file format inside ZIP.")
                            return redirect('dashboard:upload')

            else:
                messages.error(request, "Unsupported file format.")
                return redirect('dashboard:upload')

            # Handling the dataframe
            if df is not None:
                # Delete all transactions associated with the user
                Transaction.objects.filter(user=request.user).delete()

                for _, row in df.iterrows():
                    # Create or get the category
                    category_name = row['Category']
                    category, created = Categories.objects.get_or_create(name=category_name)

                    # Create the transaction
                    transaction = Transaction(
                        user=request.user,
                        title=row['Title'],
                        amount=row['Amount'],
                        category=category,
                        transaction_date=row['Date'],
                        description=row['Description'],
                        type=row['Type']
                    )
                    transaction.save()

                messages.success(request, "Data uploaded successfully!")
                return redirect('dashboard:index')  # Redirect to the index page after successful upload
            else:
                messages.error(request, "Failed to read data.")
                return redirect('dashboard:upload')

    else:
        form = UploadFileForm()

    return render(request, 'dashboard/upload.html', {'form': form})

@login_required
def export_data(request):
    # Define the response content type and headers
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="user_data.xlsx"'

    # Get user's data
    transactions = Transaction.objects.filter(user=request.user).order_by('-transaction_date')
    
    wb = Workbook()
    ws = wb.active

    ws.append(['Title', 'Type', 'Amount', 'Description', 'Date'])

    for transaction in transactions:
        ws.append([transaction.title, transaction.type, transaction.amount, transaction.description, transaction.transaction_date])

    wb.save(response)

    return response

