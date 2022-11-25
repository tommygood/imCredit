from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('IMCreditCount', views.Credit),
    path('update', views.update),
    path('creditUp', views.creditUp),
    path('rest', views.rest),
    path('same', views.Same),
    path('tongs', views.Tongs),
    path('college', views.College),
    path('department', views.Department),
    path('profession', views.Profession),
    path('free', views.Free),
    path('addData', views.addData),
]

