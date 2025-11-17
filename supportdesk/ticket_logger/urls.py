from django.contrib import admin
from django.urls import path
from . import views



urlpatterns = [
    path('', views.create_issue, name="create_issue"),
    path("register/", views.register_staff, name="register_staff"),
    path('login/', views.login_staff, name='login_staff'),
    path("logout/", views.logout_staff, name="logout_staff"),
    path("users/", views.all_users, name="all_users"),
    

    
    path("dashboard/", views.dashboard, name="dashboard"),
    path("assign/<int:issue_id>/", views.assign_issue, name="assign_issue"),

    path("assign_issue/<int:issue_id>/",views.assign_issue,name="assign_issue"),
    path("update_ticket_status/<int:issue_id>/",views.update_ticket_status,name="update_ticket_status"),
]

