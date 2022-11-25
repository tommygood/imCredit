import datetime
from django.db import models
from django.contrib import admin

class excelData(models.Model) :
    excel_data = models.FileField(upload_to='Excel/', blank=False, null=False)
    name = models.CharField(max_length = 15, blank=True, null=True) # 使用者名稱
    password = models.CharField(max_length = 100, default = "", blank=True, null=True) # 密碼

class userLec(models.Model) :
    all_data = models.CharField(max_length=5000, blank = True)

@admin.register(excelData)
class excelDataAdmin(admin.ModelAdmin):
    list_display = [field.name for field in excelData._meta.fields]

@admin.register(userLec)
class LecAdmin(admin.ModelAdmin):
    list_display = [field.name for field in userLec._meta.fields]
