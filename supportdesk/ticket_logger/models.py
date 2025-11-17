from django.db import models

from django.db import models
import uuid


# Staffs / Staff
class Staff(models.Model):
    ROLE_CHOICES = (
        ('Lead', 'lead'),
        ('Associate', 'associate'),
    )
    first_name = models.CharField(max_length=255)
    lastname = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)  # Added password field
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)


    class Meta:
        db_table = "staff" # Explicity define the name of table 


    def __str__(self):
        return f"{self.full_name} ({self.role})"


# Issue Categories

class IssueType(models.Model):
    # Predefined IT-related issue types
    ISSUE_CHOICES = [
    ('Password Reset', 'password_reset'),
    ('Network Down', 'network_down'),
    ('Software Install', 'software_install'),
    ('Hardware Failure', 'hardware_failure'),
    ('Email Issue', 'email_issue'),
    ('Printer Issue', 'printer_issue'),
    ('Security Incident', 'security_incident'),
    ('Application Bug', 'application_bug'),
    ('Server Down', 'server_down'),
    ('Other', 'other'),
    ]

    name = models.CharField(max_length=100,choices=ISSUE_CHOICES,unique=True)
    description = models.TextField(blank=True,null=True)

    class Meta:
        db_table = "issue_type" # Explicity define the name of table 

    
    def __str__(self):
        return self.name
    



class Issue(models.Model):
    STATUS_CHOICES = (
    ('New', 'new'),
    ('Assigned', 'assigned'),
    ('In Progress', 'in_progress'),
    ('Resolved', 'resolved'),
    ('Closed', 'closed'),
    )

    # Public submitter info
    ticket_number = models.CharField(max_length=30, unique=True, editable=False) 
    submitter_fullname = models.CharField(max_length=255)
    submitter_email = models.EmailField()
    submitter_department = models.CharField(max_length=100)

    category = models.ForeignKey(IssueType, on_delete=models.CASCADE)
    description = models.TextField()
    attachment = models.CharField(max_length=500,blank=True,null=True,help_text="Path to the file in object storage")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='New')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        db_table = "issue" # Explicity define the name of table 

    # Automatically generate ticket number, e.g., "TCK-<UUID4>"
    def save(self, *args, **kwargs):
        if not self.ticket_number: # ensure ticket does not change when update is made on issue model
            # Automatically generate ticket number, e.g., "TCK-<UUID4>"
            self.ticket_number = f"TCK-{uuid.uuid4().hex[:8].upper()}"
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Issue #{self.id} - {self.category.name} ({self.status})"
    
    
class IssueAssignment(models.Model):
    issue = models.ForeignKey(Issue,on_delete=models.CASCADE,related_name='assignments')
    assigned_to = models.ForeignKey(Staff,on_delete=models.CASCADE,related_name='assigned_issues')
    
    assigned_by = models.ForeignKey(
        Staff,on_delete=models.CASCADE,blank=True,null=True,related_name='assigned_by_me',help_text="Staff who performed the assignment (lead)")
    
    assigned_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True, null=True, help_text="Optional notes about the assignment")
    is_current = models.BooleanField(default=True)  # Marks whether this assignment is the current active assignment

    class Meta:
        db_table = "issue_assignment"  # correct spelling

    
    # Update is_current to false automatically when a new assignment for the same issue is created and saved with is_current=True
    def save(self, *args, **kwargs):
        if self.is_current:
            # Set previous assignments for the same issue to False
            IssueAssignment.objects.filter(issue=self.issue, is_current=True).update(is_current=False)
        super().save(*args, **kwargs)


    def __str__(self):
        return f"Issue {self.issue.id} assigned to {self.assigned_to.Staffname} by {self.assigned_by or 'System'}"
    
    

class IssueHistoryTrack(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='activity_logs')
    performed_by = models.ForeignKey(
        Staff, on_delete=models.CASCADE, blank=True, null=True
    )  # Null for public actions
    action = models.CharField(max_length=100, blank=True)  # e.g., "Status changed to in_progress"
    comment = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "issue_history_track" # Explicity define the name of table 

    def __str__(self):
        return f"{self.issue} - {self.action} by {self.performed_by or 'Public'}"


