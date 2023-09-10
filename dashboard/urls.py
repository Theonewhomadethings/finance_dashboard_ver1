from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "dashboard"
urlpatterns = [
    path("", views.index, name="index"),
    path("register/", views.register, name="register"),
    path('login/', views.loginPage , name='login'),
    path('logout/', views.logoutUser , name='logout'),
    path('change-password/', views.change_password, name='change_password'),
    path('upload/', views.upload_transaction_data, name = "upload"),
    path('export/', views.export_data, name='export_data'),
]