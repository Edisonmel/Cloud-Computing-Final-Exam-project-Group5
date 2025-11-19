from django.shortcuts import render, redirect,get_object_or_404
from django.contrib import messages
from .models import Issue, IssueType,IssueAssignment,Staff
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password, check_password
from functools import wraps
from django.core.mail import send_mail,EmailMessage
from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
import os
# from supportdesk.settings import EMAIL_HOST_USER




def create_issue(request):
    categories = IssueType.objects.all()

    if request.method == "POST":
        form_data = {
            "submitter_fullname": request.POST.get("submitter_fullname", "").strip(),
            "submitter_email": request.POST.get("submitter_email", "").strip(),
            "submitter_department": request.POST.get("submitter_department", "").strip(),
            "category": request.POST.get("category", ""),
            "description": request.POST.get("description", "").strip(),
            "attachment": request.FILES.get("attachment")
        }

        # Basic server-side validation
        required = ["submitter_fullname", "submitter_email", "submitter_department", "category", "description"]
        missing = [field for field in required if not form_data[field]]

        if missing:
            messages.error(request, "Please fill all required fields.")
            return render(request, "public/create_issue.html", {"categories": categories, "form_data": form_data})
        
        
        ## Save the Uploaded file on File system
        attachment = form_data["attachment"]
        
        if attachment:
            
            # STATIC ROOT for the app
            upload_dir = os.path.join(settings.BASE_DIR, "ticket_logger", "static", "uploads")
            os.makedirs(upload_dir, exist_ok=True)

            # Full file path
            file_path = os.path.join(upload_dir, attachment.name)

            # Save the uploaded file manually
            with open(file_path, "wb+") as dest:
                for chunk in attachment.chunks():
                    dest.write(chunk)

            # Save the relative static path (used in templates)
            saved_path = f"uploads/{attachment.name}"

        # Create Issue
        new_issue = Issue.objects.create(
                    submitter_fullname=form_data["submitter_fullname"],
                    submitter_email=form_data["submitter_email"],
                    submitter_department=form_data["submitter_department"],
                    category_id=form_data["category"],
                    description=form_data["description"],
                    attachment = saved_path
)

        # get ticket number for the created issue
        ticket_number = new_issue.ticket_number

        messages.success(
        request,
        f""" Thank you {form_data["submitter_fullname"]} for submitting your issue. 
        Please ticket number has been sent to your email. Use for further follow up
        """
        )
        
        # Prepare email content
        # Prepare email content
        subject = "Acknowledge Receipt of Ticket"
        message = (
            f"Thank you! Your issue has been submitted successfully. "
            f"Your ticket number is {ticket_number}. Please keep it for further follow-up."
        )

        recipient_list = [form_data["submitter_email"]]  # Must be a list
        EMAIL_HOST_USER = "edisonwacavan2015@gmail.com"  # Must be a string

        # Send email
        send_mail(
            subject,
            message,
            EMAIL_HOST_USER,
            recipient_list,
            fail_silently=False,
        )


        return redirect("create_issue")

    return render(request, "public/create_issue.html", {
        "categories": categories,
        "form_data": {}
    })



def login_staff(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            user = Staff.objects.get(email=email)
        except Staff.DoesNotExist:
            messages.error(request, "Email not found. Please try again.")
            return redirect("login_staff")

        # Validate hashed password
        if check_password(password, user.password):
            
            # Store user in session
            request.session["user_id"] = user.id
            request.session["user_first_name"] = user.first_name

            # Print to console (for debugging)
            print(f"User ID stored in session: {request.session['user_id']}")
            print(f"User first name stored in session: {request.session['user_first_name']}")

            messages.success(request, f"Welcome back, {user.first_name}!")
            return redirect("dashboard")  # Change to your own page
        
        else:
            messages.error(request, "Incorrect password. Please try again.")
            return redirect("auth/login")

    return render(request, "auth/login.html")

def staff_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if "user_id" not in request.session:
            return redirect("login_staff")
        return view_func(request, *args, **kwargs)
    return wrapper


def logout_staff(request):
    request.session.flush()
    return redirect("login_staff")

# auth helper
def get_logged_in_Staff(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None  # No user in session
    try:
        return Staff.objects.get(id=user_id)
    except Staff.DoesNotExist:
        return None  # User id in session does not exist in DB
    

@staff_login_required
def register_staff(request):

    logged_in_staff = get_logged_in_Staff(request)  # <--- rename variable

    if request.method == "POST":
        firstname = request.POST.get("fistname")
        lastname = request.POST.get("lastname")
        email = request.POST.get("email")
        password = request.POST.get("password")
        role =  request.POST.get("role")

        print(firstname,lastname,email,password,role)

        # Save user with hashed password
        Staff.objects.create(
            first_name = firstname,
            lastname = lastname,
            email=email,
            password=make_password(password),   # Hash the password here
            role = role
        )

        messages.success(request, "New User created successfully")
        return redirect("dashboard")  # Change to your url name

    return render(request, "auth/register.html",{"Staff": logged_in_staff})

@staff_login_required
def all_users(request):
    """
    Display all registered users, excluding their password.
    """
    users = Staff.objects.all()
    
    context = {
       
    }
    return render(request, "dashboard/all_users.html", {
                  "Staff": get_logged_in_Staff(request),
                    "users": users
                    })

# DASHBOARD VIEW
@staff_login_required
def dashboard(request):
    """ 
        Rules:
        Lead: sees all issues, can assign
        Associate: sees only assigned issues
    """
    logged_in_staff = get_logged_in_Staff(request)  # <--- rename variable

    if logged_in_staff.role == "Lead":
        issues = Issue.objects.all().order_by("-created_at")
        associates = Staff.objects.filter(role="Associate")  # <--- Staff is still the model
    else:
        issues = Issue.objects.filter(assignments__assigned_to=logged_in_staff, assignments__is_current=True)
        associates = None

    # ---- Summary Statistics ----
    stats = {
        "total": Issue.objects.count(),
        "new": Issue.objects.filter(status="New").count(),
        "assigned": Issue.objects.filter(status="Assigned").count(),
        "in_progress": Issue.objects.filter(status="In progress").count(),
        "resolved": Issue.objects.filter(status="Resolved").count(),
        "closed": Issue.objects.filter(status="Closed").count(),
    }

    return render(request, "dashboard/dashboard.html", {
        "Staff": logged_in_staff,
        "issues": issues,
        "associates": associates,
        "stats": stats
    })


# ASSIGN ISSUE VIEW (Lead Only)
@staff_login_required
def assign_issue(request, issue_id):

    logged_in_staff = get_logged_in_Staff(request)

    if logged_in_staff.role != "Lead":
        messages.error(request, "You are not authorized to perform this action.")
        return redirect("dashboard")

    if request.method != "POST":
        messages.error(request, "Invalid request.")
        return redirect("dashboard")

    associate_id = request.POST.get("assigned_to")
    note = request.POST.get("note")

    # # Use Staff model — NOT the logged-in staff instance
    # from .models import User as Staff  

    try:
        assigned_to = Staff.objects.get(id=associate_id, role="Associate")
    except Staff.DoesNotExist:
        messages.error(request, "Selected staff does not exist.")
        return redirect("dashboard")

    # Close existing assignments
    IssueAssignment.objects.filter(issue_id=issue_id, is_current=True).update(is_current=False)

    # Create new assignment
    IssueAssignment.objects.create(
        issue_id=issue_id,
        assigned_to=assigned_to,
        assigned_by=logged_in_staff,
        note=note,
        is_current=True
    )

    # Update status
    Issue.objects.filter(id=issue_id).update(status="Assigned")

    messages.success(request, f"Issue assigned successfully to {assigned_to.first_name}.")
    return redirect("dashboard")


@staff_login_required
def update_ticket_status(request, issue_id):
    staff = get_logged_in_Staff(request)

    if request.method == "POST":
        new_status = request.POST.get("status")

        # Validate allowed statuses
        if new_status not in ["In progress", "Resolved","Closed"]:
            messages.error(request, "Invalid status selected.")
            return redirect("dashboard")

        # Find the issue
        try:
            issue = Issue.objects.get(id=issue_id)
        except Issue.DoesNotExist:
            messages.error(request, "Issue not found.")
            return redirect("dashboard")

        # Check if status is unchanged
        if issue.status == new_status:
            messages.warning(
                request,
                f"Ticket {issue.ticket_number} is already marked as '{new_status}'. Pick Different Status."
            )
            return redirect("dashboard")

        # Apply update
        issue.status = new_status
        issue.save()

        messages.success(
            request,
            f"Successfully changed the status of Ticket {issue.ticket_number} to '{new_status}'."
        )
        return redirect("dashboard")

    # Fallback
    return redirect("dashboard")

@staff_login_required
def edit_user(request, user_id):
    user = get_object_or_404(Staff, id=user_id)

    if request.method == "POST":
        user.first_name = request.POST.get("fistname")
        user.lastname = request.POST.get("lastname")
        user.email = request.POST.get("email")
        user.role = request.POST.get("role")

        user.save()
        messages.success(request, f"User '{user.first_name}' updated successfully.")
        return redirect("all_users")

    return render(request, "auth/edit_user.html", {"user": user})


def delete_user(request, user_id):
    user = get_object_or_404(Staff, id=user_id)

    user.delete()
    messages.success(request, "User deleted successfully.")
    return redirect("all_users")




