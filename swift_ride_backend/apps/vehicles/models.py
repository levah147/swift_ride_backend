"""
Vehicle models for Swift Ride project.
"""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator

from apps.common.models import BaseModel, SoftDeleteModel
from apps.common.utils import get_file_path


class VehicleType(BaseModel):
    """
    Model for different types of vehicles.
    """
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    base_fare = models.DecimalField(max_digits=10, decimal_places=2)
    per_km_rate = models.DecimalField(max_digits=10, decimal_places=2)
    per_minute_rate = models.DecimalField(max_digits=10, decimal_places=2)
    capacity = models.PositiveSmallIntegerField(default=4)
    icon = models.ImageField(upload_to='vehicle_types/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']


class Vehicle(BaseModel, SoftDeleteModel):
    """
    Model for vehicles owned by drivers.
    """
    class VerificationStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        APPROVED = 'approved', _('Approved')
        REJECTED = 'rejected', _('Rejected')
        SUSPENDED = 'suspended', _('Suspended')
    
    class FuelType(models.TextChoices):
        PETROL = 'petrol', _('Petrol')
        DIESEL = 'diesel', _('Diesel')
        ELECTRIC = 'electric', _('Electric')
        HYBRID = 'hybrid', _('Hybrid')
        CNG = 'cng', _('CNG')
        LPG = 'lpg', _('LPG')
    
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vehicles'
    )
    vehicle_type = models.ForeignKey(
        VehicleType,
        on_delete=models.CASCADE,
        related_name='vehicles'
    )
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.PositiveSmallIntegerField()
    color = models.CharField(max_length=30)
    license_plate = models.CharField(
        max_length=20,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Z0-9\-\s]+$',
                message='License plate must contain only letters, numbers, hyphens, and spaces'
            )
        ]
    )
    vin_number = models.CharField(
        max_length=17,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[A-HJ-NPR-Z0-9]{17}$',
                message='VIN must be 17 characters long and contain only valid characters'
            )
        ]
    )
    fuel_type = models.CharField(
        max_length=10,
        choices=FuelType.choices,
        default=FuelType.PETROL
    )
    engine_capacity = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Engine capacity in liters"
    )
    mileage = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Current mileage in kilometers"
    )
    verification_status = models.CharField(
        max_length=10,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )
    is_active = models.BooleanField(default=True)
    is_eco_friendly = models.BooleanField(default=False)
    
    # Vehicle photos
    front_photo = models.ImageField(
        upload_to=get_file_path,
        null=True,
        blank=True,
        help_text="Front view of the vehicle"
    )
    back_photo = models.ImageField(
        upload_to=get_file_path,
        null=True,
        blank=True,
        help_text="Back view of the vehicle"
    )
    side_photo = models.ImageField(
        upload_to=get_file_path,
        null=True,
        blank=True,
        help_text="Side view of the vehicle"
    )
    interior_photo = models.ImageField(
        upload_to=get_file_path,
        null=True,
        blank=True,
        help_text="Interior view of the vehicle"
    )
    
    # Verification details
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='verified_vehicles',
        null=True,
        blank=True
    )
    rejection_reason = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.make} {self.model} ({self.license_plate})"
    
    @property
    def is_verified(self):
        return self.verification_status == self.VerificationStatus.APPROVED
    
    @property
    def display_name(self):
        return f"{self.year} {self.make} {self.model}"
    
    @property
    def has_valid_documents(self):
        """Check if vehicle has all required valid documents."""
        required_docs = ['registration', 'insurance']
        for doc_type in required_docs:
            if not self.documents.filter(
                document_type=doc_type,
                is_verified=True,
                expiry_date__gt=models.functions.Now()
            ).exists():
                return False
        return True
    
    class Meta:
        ordering = ['-created_at']


class VehicleDocument(BaseModel):
    """
    Model for vehicle documents (registration, insurance, etc.).
    """
    class DocumentType(models.TextChoices):
        REGISTRATION = 'registration', _('Vehicle Registration')
        INSURANCE = 'insurance', _('Insurance Certificate')
        ROADWORTHINESS = 'roadworthiness', _('Roadworthiness Certificate')
        PERMIT = 'permit', _('Commercial Permit')
        INSPECTION = 'inspection', _('Vehicle Inspection')
        OTHER = 'other', _('Other Document')
    
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices
    )
    document_number = models.CharField(max_length=100)
    document_file = models.FileField(upload_to=get_file_path)
    issue_date = models.DateField()
    expiry_date = models.DateField()
    issuing_authority = models.CharField(max_length=100)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='verified_documents',
        null=True,
        blank=True
    )
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.get_document_type_display()} - {self.vehicle}"
    
    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now().date() > self.expiry_date
    
    @property
    def days_until_expiry(self):
        from django.utils import timezone
        delta = self.expiry_date - timezone.now().date()
        return delta.days
    
    class Meta:
        unique_together = ['vehicle', 'document_type']
        ordering = ['-created_at']


class Insurance(BaseModel):
    """
    Model for vehicle insurance details.
    """
    class InsuranceType(models.TextChoices):
        THIRD_PARTY = 'third_party', _('Third Party')
        COMPREHENSIVE = 'comprehensive', _('Comprehensive')
        COMMERCIAL = 'commercial', _('Commercial')
    
    vehicle = models.OneToOneField(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='insurance'
    )
    insurance_type = models.CharField(
        max_length=15,
        choices=InsuranceType.choices
    )
    policy_number = models.CharField(max_length=100, unique=True)
    insurance_company = models.CharField(max_length=100)
    premium_amount = models.DecimalField(max_digits=10, decimal_places=2)
    coverage_amount = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    certificate_file = models.FileField(upload_to=get_file_path)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Insurance - {self.vehicle} ({self.policy_number})"
    
    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now().date() > self.end_date
    
    @property
    def days_until_expiry(self):
        from django.utils import timezone
        delta = self.end_date - timezone.now().date()
        return delta.days
    
    class Meta:
        ordering = ['-created_at']


class Inspection(BaseModel):
    """
    Model for vehicle inspections.
    """
    class InspectionType(models.TextChoices):
        INITIAL = 'initial', _('Initial Inspection')
        PERIODIC = 'periodic', _('Periodic Inspection')
        MAINTENANCE = 'maintenance', _('Maintenance Inspection')
        ACCIDENT = 'accident', _('Post-Accident Inspection')
    
    class InspectionStatus(models.TextChoices):
        SCHEDULED = 'scheduled', _('Scheduled')
        IN_PROGRESS = 'in_progress', _('In Progress')
        PASSED = 'passed', _('Passed')
        FAILED = 'failed', _('Failed')
        CANCELLED = 'cancelled', _('Cancelled')
    
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='inspections'
    )
    inspection_type = models.CharField(
        max_length=15,
        choices=InspectionType.choices
    )
    status = models.CharField(
        max_length=15,
        choices=InspectionStatus.choices,
        default=InspectionStatus.SCHEDULED
    )
    scheduled_date = models.DateTimeField()
    completed_date = models.DateTimeField(null=True, blank=True)
    inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='conducted_inspections',
        null=True,
        blank=True
    )
    inspection_center = models.CharField(max_length=100, null=True, blank=True)
    
    # Inspection checklist
    exterior_condition = models.CharField(max_length=20, null=True, blank=True)
    interior_condition = models.CharField(max_length=20, null=True, blank=True)
    engine_condition = models.CharField(max_length=20, null=True, blank=True)
    brake_condition = models.CharField(max_length=20, null=True, blank=True)
    tire_condition = models.CharField(max_length=20, null=True, blank=True)
    lights_condition = models.CharField(max_length=20, null=True, blank=True)
    
    overall_score = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    recommendations = models.TextField(blank=True, null=True)
    next_inspection_date = models.DateField(null=True, blank=True)
    
    # Inspection photos
    inspection_photos = models.JSONField(default=list, blank=True)
    
    def __str__(self):
        return f"{self.get_inspection_type_display()} - {self.vehicle} ({self.scheduled_date.date()})"
    
    @property
    def is_passed(self):
        return self.status == self.InspectionStatus.PASSED
    
    class Meta:
        ordering = ['-scheduled_date']


class VehicleMaintenanceRecord(BaseModel):
    """
    Model for vehicle maintenance records.
    """
    class MaintenanceType(models.TextChoices):
        ROUTINE = 'routine', _('Routine Maintenance')
        REPAIR = 'repair', _('Repair')
        EMERGENCY = 'emergency', _('Emergency Repair')
        UPGRADE = 'upgrade', _('Upgrade')
    
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='maintenance_records'
    )
    maintenance_type = models.CharField(
        max_length=15,
        choices=MaintenanceType.choices
    )
    description = models.TextField()
    service_provider = models.CharField(max_length=100)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    mileage_at_service = models.PositiveIntegerField()
    service_date = models.DateField()
    next_service_date = models.DateField(null=True, blank=True)
    next_service_mileage = models.PositiveIntegerField(null=True, blank=True)
    receipt_file = models.FileField(upload_to=get_file_path, null=True, blank=True)
    
    def __str__(self):
        return f"{self.get_maintenance_type_display()} - {self.vehicle} ({self.service_date})"
    
    class Meta:
        ordering = ['-service_date']
