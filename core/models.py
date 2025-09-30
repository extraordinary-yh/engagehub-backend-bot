from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class Track(models.Model):
    """Career tracks for students: Tech, Consulting, Finance"""
    TRACK_CHOICES = [
        ('tech', 'Tech'),
        ('consulting', 'Consulting'),
        ('finance', 'Finance'),
    ]
    
    name = models.CharField(max_length=20, choices=TRACK_CHOICES, unique=True)
    display_name = models.CharField(max_length=50, help_text="Display name for UI")
    description = models.TextField(blank=True, help_text="Description of the track")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tracks'
        ordering = ['name']
    
    def __str__(self):
        return self.display_name

class User(AbstractUser):
    """Extended user model with role-based access"""
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('student', 'Student'),
        ('company', 'Company'),
        ('university', 'University'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    track = models.ForeignKey(Track, on_delete=models.SET_NULL, null=True, blank=True, help_text="Career track for students")
    company = models.CharField(max_length=100, blank=True, null=True)
    university = models.CharField(max_length=100, blank=True, null=True)
    major = models.CharField(max_length=100, blank=True, null=True, help_text="User's major/field of study")
    graduation_year = models.IntegerField(blank=True, null=True, help_text="Expected graduation year")
    display_name = models.CharField(max_length=100, blank=True, null=True, help_text="Display name for UI (defaults to username if not set)")
    discord_id = models.CharField(max_length=50, blank=True, null=True)
    
    # Discord verification fields
    discord_username_unverified = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text="Discord username provided during registration (unverified)"
    )
    discord_verified = models.BooleanField(
        default=False,
        help_text="Whether the Discord account has been verified via bot"
    )
    discord_verified_at = models.DateTimeField(
        blank=True, 
        null=True,
        help_text="When Discord verification was completed"
    )
    
    total_points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Media Consent Fields
    media_consent = models.BooleanField(
        default=None, 
        null=True, 
        blank=True,
        help_text="User's consent to be featured in EngageHub media materials"
    )
    media_consent_date = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Date when consent decision was made"
    )
    media_consent_ip = models.GenericIPAddressField(
        null=True, 
        blank=True,
        help_text="IP address when consent decision was made"
    )
    media_consent_user_agent = models.TextField(
        null=True, 
        blank=True,
        help_text="User agent string when consent decision was made"
    )
    
    # Onboarding Completion
    onboarding_completed = models.BooleanField(
        default=False,
        help_text="Whether user has completed the onboarding flow"
    )
    onboarding_completed_date = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Date when onboarding was completed"
    )
    
    class Meta:
        db_table = 'users'
    
    def __str__(self):
        return f"{self.username} ({self.role})"

class Activity(models.Model):
    """Points-earning activities"""
    ACTIVITY_TYPES = [
        ('resume_upload', 'Resume Upload'),
        ('resume_review_request', 'Resume Review Request'),
        ('event_attendance', 'Event Attendance'),
        ('resource_share', 'Resource Share'),
        ('like_interaction', 'Like/Interaction'),
        ('linkedin_post', 'LinkedIn Post'),
        ('discord_activity', 'Discord Activity'),
        ('job_lead_post', 'Job Lead Post'),
        ('thoughtful_reply', 'Thoughtful Reply'),
        ('resume_feedback_provide', 'Resume Feedback Provide'),
        ('study_group_lead', 'Study Group Lead'),
        ('resource_walkthrough', 'Resource Walkthrough'),
        ('mock_interview_host', 'Mock Interview Host'),
        ('teach_share_session', 'Teach & Share Session'),
        ('peer_mentor', 'Peer Mentor'),
        ('mini_event_organize', 'Mini Event Organize'),
        ('professional_referral', 'Professional Referral'),
        ('exclusive_resource', 'Exclusive Resource'),
        ('external_workshop', 'External Workshop'),
    ]
    
    CATEGORY_CHOICES = [
        ('engagement', 'Community Engagement'),
        ('professional', 'Professional Development'),
        ('social', 'Social Media'),
        ('events', 'Events & Networking'),
        ('content', 'Content Creation'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=100)
    activity_type = models.CharField(max_length=25, choices=ACTIVITY_TYPES)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    points_value = models.IntegerField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'activities'
        verbose_name_plural = 'Activities'
    
    def __str__(self):
        return f"{self.name} ({self.points_value} pts)"

class PointsLog(models.Model):
    """Log of all points earned by users"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='points_logs')
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    points_earned = models.IntegerField()
    details = models.TextField(blank=True)

    timestamp = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'points_log'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user.username} earned {self.points_earned} pts for {self.activity.name}"

class Incentive(models.Model):
    """Rewards that students can redeem with points"""
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('unlocked', 'Unlocked'),
        ('redeemed', 'Redeemed'),
    ]
    
    CATEGORY_CHOICES = [
        ('merchandise', 'Merchandise'),
        ('gift_cards', 'Gift Cards'),
        ('experiences', 'Experiences'),
        ('services', 'Services'),
        ('digital', 'Digital Rewards'),
        ('other', 'Other'),
    ]
    
    TIER_CHOICES = [
        ('tier1', 'Tier 1 (Foundational Rewards)'),
        ('tier2', 'Tier 2 (Premium Resources & Scaled Access)'),
        ('tier3', 'Tier 3 (High-Value Human Interaction)'),
        ('tier4', 'Tier 4 (Elite & Bespoke Rewards)'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    points_required = models.IntegerField()
    sponsor = models.CharField(max_length=100, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    tier = models.CharField(max_length=10, choices=TIER_CHOICES, default='tier1')
    image_url = models.URLField(blank=True, null=True, help_text="URL to reward image")
    stock_available = models.IntegerField(default=0, help_text="Number of items available")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'incentives'
    
    def __str__(self):
        return f"{self.name} ({self.points_required} pts)"

class Redemption(models.Model):
    """Log of incentive redemptions"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='redemptions')
    incentive = models.ForeignKey(Incentive, on_delete=models.CASCADE)
    points_spent = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    delivery_details = models.JSONField(default=dict, help_text="Delivery address and contact info")
    tracking_info = models.CharField(max_length=255, blank=True, null=True)
    estimated_delivery = models.DateField(blank=True, null=True)
    admin_notes = models.TextField(blank=True)
    redeemed_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'redemptions'
        ordering = ['-redeemed_at']
    
    def __str__(self):
        return f"{self.user.username} redeemed {self.incentive.name}"

class UserStatus(models.Model):
    """User warnings and suspension tracking"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='status')
    warnings = models.IntegerField(default=0)
    points_suspended = models.BooleanField(default=False)
    suspension_end = models.DateTimeField(blank=True, null=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_status'
        verbose_name_plural = 'User Statuses'
    
    def __str__(self):
        return f"{self.user.username} - {self.warnings} warnings"

class UserIncentiveUnlock(models.Model):
    """Tracks when a user unlocks a given incentive threshold.

    This enables per-user unlock status on the website and allows
    notification deduplication if needed.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='unlocked_incentives')
    incentive = models.ForeignKey(Incentive, on_delete=models.CASCADE, related_name='user_unlocks')
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_incentive_unlocks'
        unique_together = ('user', 'incentive')
        ordering = ['-unlocked_at']

    def __str__(self):
        return f"{self.user.username} unlocked {self.incentive.name}"

class DiscordLinkCode(models.Model):
    """One-time code to link a logged-in website user with a Discord account."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discord_link_codes')
    code = models.CharField(max_length=6, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'discord_link_codes'
        indexes = [
            models.Index(fields=['code']),
        ]

    def __str__(self):
        status = 'used' if self.used_at else 'active'
        return f"LinkCode({self.code}) for {self.user.username} [{status}]"

class Professional(models.Model):
    """Professional reviewers for resume review system"""
    name = models.CharField(max_length=100)
    email = models.EmailField()
    specialties = models.TextField(help_text="Industries or specializations (e.g., Tech, Finance, Consulting)")
    bio = models.TextField(blank=True, help_text="Professional background and experience")
    availability = models.JSONField(default=dict, help_text="Availability preferences and schedule")
    is_active = models.BooleanField(default=True)
    total_reviews = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00, help_text="Average rating from students")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'professionals'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.specialties}"

class ReviewRequest(models.Model):
    """Resume review requests from students"""
    STATUS_CHOICES = [
        ('pending', 'Pending Match'),
        ('matched', 'Matched with Professional'),
        ('scheduled', 'Review Scheduled'),
        ('completed', 'Review Completed'),
        ('cancelled', 'Cancelled'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='review_requests')
    professional = models.ForeignKey(Professional, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_reviews')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Form submission data
    form_data = models.JSONField(default=dict, help_text="Data from Google Form submission")
    target_industry = models.CharField(max_length=100, blank=True)
    target_role = models.CharField(max_length=100, blank=True)
    experience_level = models.CharField(max_length=50, blank=True)
    
    # Scheduling
    preferred_times = models.JSONField(default=list, help_text="Student's preferred time slots")
    scheduled_time = models.DateTimeField(null=True, blank=True)
    session_duration = models.IntegerField(default=30, help_text="Duration in minutes")
    
    # Review details
    review_notes = models.TextField(blank=True, help_text="Professional's feedback notes")
    student_feedback = models.TextField(blank=True, help_text="Student's feedback about the review")
    rating = models.IntegerField(null=True, blank=True, choices=[(i, i) for i in range(1, 6)], help_text="Student rating (1-5)")
    
    # Timestamps
    submission_date = models.DateTimeField(auto_now_add=True)
    matched_date = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    
    # Admin notes
    admin_notes = models.TextField(blank=True)

    class Meta:
        db_table = 'review_requests'
        ordering = ['-submission_date']

    def __str__(self):
        professional_name = self.professional.name if self.professional else "Unassigned"
        return f"{self.student.username} - {professional_name} ({self.status})"
    
    def save(self, *args, **kwargs):
        # Update timestamps based on status changes
        if self.pk:  # Only for updates, not new records
            old_instance = ReviewRequest.objects.get(pk=self.pk)
            if old_instance.status != self.status:
                if self.status == 'matched' and not self.matched_date:
                    self.matched_date = timezone.now()
                elif self.status == 'completed' and not self.completed_date:
                    self.completed_date = timezone.now()
                    # Update professional's total reviews
                    if self.professional:
                        self.professional.total_reviews += 1
                        self.professional.save()
        super().save(*args, **kwargs)

class ScheduledSession(models.Model):
    """Scheduled meetings between students and professionals"""
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]

    review_request = models.OneToOneField(ReviewRequest, on_delete=models.CASCADE, related_name='scheduled_session')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_sessions')
    professional = models.ForeignKey(Professional, on_delete=models.CASCADE, related_name='professional_sessions')
    
    # Session details
    scheduled_time = models.DateTimeField(help_text="Scheduled meeting time")
    duration_minutes = models.IntegerField(default=30, help_text="Session duration in minutes")
    meeting_link = models.URLField(blank=True, help_text="Video call link (Zoom, Google Meet, etc.)")
    calendar_event_id = models.CharField(max_length=255, blank=True, help_text="Google Calendar event ID")
    
    # Status and notes
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    admin_notes = models.TextField(blank=True, help_text="Admin notes about the session")
    session_notes = models.TextField(blank=True, help_text="Notes from the actual session")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'scheduled_sessions'
        ordering = ['-scheduled_time']

    def __str__(self):
        return f"{self.student.username} <-> {self.professional.name} at {self.scheduled_time}"
    
    def save(self, *args, **kwargs):
        # Update related review request status
        if self.pk is None:  # New session
            self.review_request.status = 'scheduled'
            self.review_request.scheduled_time = self.scheduled_time
            self.review_request.save()
        super().save(*args, **kwargs)

class ProfessionalAvailability(models.Model):
    """Professional availability responses from Google Forms"""
    professional = models.ForeignKey(Professional, on_delete=models.CASCADE, related_name='availability_responses')
    form_response_id = models.CharField(max_length=255, unique=True, help_text="Google Form response ID")
    
    # Form data
    form_data = models.JSONField(default=dict, help_text="Complete form response data")
    availability_slots = models.JSONField(default=list, help_text="Parsed availability time slots")
    preferred_days = models.JSONField(default=list, help_text="Preferred days of week")
    time_zone = models.CharField(max_length=50, default='UTC', help_text="Professional's timezone")
    
    # Availability periods
    start_date = models.DateField(help_text="Start of availability period")
    end_date = models.DateField(help_text="End of availability period")
    
    # Metadata
    submission_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, help_text="Additional notes from professional")

    class Meta:
        db_table = 'professional_availability'
        ordering = ['-submission_date']

    def __str__(self):
        return f"{self.professional.name} - {self.start_date} to {self.end_date}"

class ResourceSubmission(models.Model):
    """User-submitted resources for admin review and potential points"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resource_submissions')
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    points_awarded = models.IntegerField(default=0)
    admin_notes = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_resources')
    
    class Meta:
        db_table = 'resource_submissions'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['status', '-submitted_at'], name='idx_resource_status_submitted'),
            models.Index(fields=['user', 'status'], name='idx_resource_user_status'),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.description[:50]}... ({self.status})"


class EventSubmission(models.Model):
    """User-submitted event attendance for admin review and potential points"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_submissions')
    event_details = models.TextField(blank=True, default="User claims to have attended an event")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    points_awarded = models.IntegerField(default=0)
    admin_notes = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_events')
    
    class Meta:
        db_table = 'event_submissions'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['status', '-submitted_at'], name='idx_event_status_submitted'),
            models.Index(fields=['user', 'status'], name='idx_event_user_status'),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Event ({self.status})"


class LinkedInSubmission(models.Model):
    """User-submitted LinkedIn updates for admin review and potential points"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='linkedin_submissions')
    linkedin_url = models.TextField(blank=True, default="User claims to have posted a LinkedIn update")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    points_awarded = models.IntegerField(default=0)
    admin_notes = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_linkedin')
    
    class Meta:
        db_table = 'linkedin_submissions'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['status', '-submitted_at'], name='idx_linkedin_status_submitted'),
            models.Index(fields=['user', 'status'], name='idx_linkedin_user_status'),
        ]
    
    def __str__(self):
        return f"{self.user.username} - LinkedIn Update ({self.status})"


class JobLeadSubmission(models.Model):
    """User-submitted job/internship leads for admin review and potential points"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_lead_submissions')
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    points_awarded = models.IntegerField(default=0)
    admin_notes = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_job_leads')
    
    class Meta:
        db_table = 'job_lead_submissions'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['status', '-submitted_at'], name='idx_joblead_status_sub'),
            models.Index(fields=['user', 'status'], name='idx_joblead_user_status'),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Job Lead ({self.status})"


class ThoughtfulReplySubmission(models.Model):
    """User-submitted thoughtful replies for admin review and potential points"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='thoughtful_reply_submissions')
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    points_awarded = models.IntegerField(default=0)
    admin_notes = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_thoughtful_replies')
    
    class Meta:
        db_table = 'thoughtful_reply_submissions'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['status', '-submitted_at'], name='idx_reply_status_sub'),
            models.Index(fields=['user', 'status'], name='idx_reply_user_status'),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Thoughtful Reply ({self.status})"


class ResumeFeedbackSubmission(models.Model):
    """User-submitted resume feedback for admin review and potential points"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resume_feedback_submissions')
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    points_awarded = models.IntegerField(default=0)
    admin_notes = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_resume_feedback')
    
    class Meta:
        db_table = 'resume_feedback_submissions'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['status', '-submitted_at'], name='idx_feedback_status_sub'),
            models.Index(fields=['user', 'status'], name='idx_feedback_user_status'),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Resume Feedback ({self.status})"


class StudyGroupSubmission(models.Model):
    """User-submitted study group leadership for admin review and potential points"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='study_group_submissions')
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    points_awarded = models.IntegerField(default=0)
    admin_notes = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_study_groups')
    
    class Meta:
        db_table = 'study_group_submissions'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['status', '-submitted_at'], name='idx_study_status_sub'),
            models.Index(fields=['user', 'status'], name='idx_study_user_status'),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Study Group ({self.status})"


class ResourceWalkthroughSubmission(models.Model):
    """User-submitted resource walkthroughs for admin review and potential points"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resource_walkthrough_submissions')
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    points_awarded = models.IntegerField(default=0)
    admin_notes = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_resource_walkthroughs')
    
    class Meta:
        db_table = 'resource_walkthrough_submissions'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['status', '-submitted_at'], name='idx_walkthrough_status_sub'),
            models.Index(fields=['user', 'status'], name='idx_walkthrough_user_status'),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Resource Walkthrough ({self.status})"


class MockInterviewSubmission(models.Model):
    """User-submitted mock interview hosting for admin review and potential points"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mock_interview_submissions')
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    points_awarded = models.IntegerField(default=0)
    admin_notes = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_mock_interviews')
    
    class Meta:
        db_table = 'mock_interview_submissions'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['status', '-submitted_at'], name='idx_mock_status_sub'),
            models.Index(fields=['user', 'status'], name='idx_mock_user_status'),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Mock Interview ({self.status})"


class TeachShareSubmission(models.Model):
    """User-submitted teach & share sessions for admin review and potential points"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teach_share_submissions')
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    points_awarded = models.IntegerField(default=0)
    admin_notes = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_teach_shares')
    
    class Meta:
        db_table = 'teach_share_submissions'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['status', '-submitted_at'], name='idx_teach_status_sub'),
            models.Index(fields=['user', 'status'], name='idx_teach_user_status'),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Teach & Share ({self.status})"


class PeerMentorSubmission(models.Model):
    """User-submitted peer mentoring for admin review and potential points"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='peer_mentor_submissions')
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    points_awarded = models.IntegerField(default=0)
    admin_notes = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_peer_mentors')
    
    class Meta:
        db_table = 'peer_mentor_submissions'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['status', '-submitted_at'], name='idx_mentor_status_sub'),
            models.Index(fields=['user', 'status'], name='idx_mentor_user_status'),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Peer Mentor ({self.status})"


class MiniEventSubmission(models.Model):
    """User-submitted mini-event organization for admin review and potential points"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mini_event_submissions')
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    points_awarded = models.IntegerField(default=0)
    admin_notes = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_mini_events')
    
    class Meta:
        db_table = 'mini_event_submissions'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['status', '-submitted_at'], name='idx_mini_status_sub'),
            models.Index(fields=['user', 'status'], name='idx_mini_user_status'),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Mini Event ({self.status})"


class ProfessionalReferralSubmission(models.Model):
    """User-submitted professional referrals for admin review and potential points"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='professional_referral_submissions')
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    points_awarded = models.IntegerField(default=0)
    admin_notes = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_professional_referrals')
    
    class Meta:
        db_table = 'professional_referral_submissions'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['status', '-submitted_at'], name='idx_referral_status_sub'),
            models.Index(fields=['user', 'status'], name='idx_referral_user_status'),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Professional Referral ({self.status})"


class ExclusiveResourceSubmission(models.Model):
    """User-submitted exclusive resources for admin review and potential points"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exclusive_resource_submissions')
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    points_awarded = models.IntegerField(default=0)
    admin_notes = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_exclusive_resources')
    
    class Meta:
        db_table = 'exclusive_resource_submissions'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['status', '-submitted_at'], name='idx_exclusive_status_sub'),
            models.Index(fields=['user', 'status'], name='idx_exclusive_user_status'),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Exclusive Resource ({self.status})"


class ExternalWorkshopSubmission(models.Model):
    """User-submitted external workshops for admin review and potential points"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='external_workshop_submissions')
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    points_awarded = models.IntegerField(default=0)
    admin_notes = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_external_workshops')
    
    class Meta:
        db_table = 'external_workshop_submissions'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['status', '-submitted_at'], name='idx_workshop_status_sub'),
            models.Index(fields=['user', 'status'], name='idx_workshop_user_status'),
        ]
    
    def __str__(self):
        return f"{self.user.username} - External Workshop ({self.status})"


class UserPreferences(models.Model):
    """User preferences for notifications and display settings"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    
    # Email notifications
    email_notifications = models.JSONField(default=dict, help_text="Email notification preferences")
    
    # Privacy settings
    privacy_settings = models.JSONField(default=dict, help_text="Privacy and display preferences")
    
    # Display preferences
    display_preferences = models.JSONField(default=dict, help_text="UI display preferences")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_preferences'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Preferences for {self.user.username}"


class DiscordEventLog(models.Model):
    """Logs raw, individual events from the Discord server."""
    EVENT_CHOICES = [
        ('message', 'Message Sent'),
        ('reaction_add', 'Reaction Added'),
        ('voice_join', 'Voice Channel Join'),
    ]

    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES, help_text="The type of event that occurred.")
    user_id = models.CharField(max_length=50, help_text="Discord user ID of the user who triggered the event.")
    channel_id = models.CharField(max_length=50, null=True, blank=True, help_text="Discord channel ID where the event occurred.")
    message_id = models.CharField(max_length=50, null=True, blank=True, help_text="Discord message ID relevant to the event.")
    emoji = models.CharField(max_length=100, null=True, blank=True, help_text="Emoji used in a reaction.")
    timestamp = models.DateTimeField(auto_now_add=True, help_text="Timestamp of when the event was logged.")
    metadata = models.JSONField(null=True, blank=True, help_text="Additional context for the event (e.g., message content).")

    class Meta:
        db_table = 'discord_event_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['event_type', 'timestamp']),
            models.Index(fields=['user_id']),
        ]

    def __str__(self):
        return f"{self.event_type} by {self.user_id} at {self.timestamp}"


class PartnerMetrics(models.Model):
    """Stores aggregated daily KPI metrics for the partner dashboard."""
    date = models.DateField(unique=True, help_text="The date for which these metrics are calculated.")
    total_active_users = models.IntegerField(default=0, help_text="Total unique users who performed any action.")
    total_messages_sent = models.IntegerField(default=0, help_text="Total number of messages sent by users.")

    # Brand Equity Metrics
    brand_mentions_company_a = models.IntegerField(default=0, help_text="Mentions of 'AcmeCorp'.")
    event_attendees_company_a = models.IntegerField(default=0, help_text="Attendees for company A's events.")

    # Talent Pipeline Metrics
    engaged_students = models.IntegerField(default=0, help_text="Students showing high engagement.")
    resume_ready_students = models.IntegerField(default=0, help_text="Students who have uploaded resumes.")
    interview_prepped_students = models.IntegerField(default=0, help_text="Students who have participated in interview prep.")

    class Meta:
        db_table = 'partner_metrics'
        ordering = ['-date']
        verbose_name_plural = "Partner Metrics"

    def __str__(self):
        return f"Metrics for {self.date}"


class RedemptionNotification(models.Model):
    """Queue for Discord redemption notifications"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]
    
    discord_id = models.CharField(max_length=50)
    reward_name = models.CharField(max_length=255)
    points_spent = models.IntegerField()
    remaining_points = models.IntegerField()
    redemption_id = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        db_table = 'redemption_notifications'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Redemption notification for {self.discord_id} - {self.reward_name}"
