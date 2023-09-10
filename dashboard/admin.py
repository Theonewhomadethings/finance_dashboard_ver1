from django.contrib import admin
from .models import UserProfile, Categories, Transaction

# Register your models here.
admin.site.register(UserProfile)
admin.site.register(Categories)
admin.site.register(Transaction)