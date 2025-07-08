"""
Common constants for Swift Ride project.
"""

# User Types
USER_TYPE_CHOICES = [
    ('rider', 'Rider'),
    ('driver', 'Driver'),
    ('both', 'Both'),
]

# Ride Status
RIDE_STATUS_CHOICES = [
    ('requested', 'Requested'),
    ('accepted', 'Accepted'),
    ('driver_arrived', 'Driver Arrived'),
    ('in_progress', 'In Progress'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
    ('no_show', 'No Show'),
]

# Payment Status
PAYMENT_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('processing', 'Processing'),
    ('completed', 'Completed'),
    ('failed', 'Failed'),
    ('refunded', 'Refunded'),
    ('cancelled', 'Cancelled'),
]

# Payment Methods
PAYMENT_METHOD_CHOICES = [
    ('cash', 'Cash'),
    ('card', 'Card'),
    ('wallet', 'Wallet'),
    ('bank_transfer', 'Bank Transfer'),
    ('ussd', 'USSD'),
]

# Vehicle Types
VEHICLE_TYPE_CHOICES = [
    ('sedan', 'Sedan'),
    ('suv', 'SUV'),
    ('hatchback', 'Hatchback'),
    ('bus', 'Bus'),
    ('motorcycle', 'Motorcycle'),
    ('tricycle', 'Tricycle'),
]

# Document Types
DOCUMENT_TYPE_CHOICES = [
    ('drivers_license', "Driver's License"),
    ('vehicle_registration', 'Vehicle Registration'),
    ('insurance', 'Insurance'),
    ('nin', 'National ID (NIN)'),
    ('passport', 'Passport'),
    ('vehicle_inspection', 'Vehicle Inspection'),
]

# Verification Status
VERIFICATION_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('under_review', 'Under Review'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('expired', 'Expired'),
]

# Notification Types
NOTIFICATION_TYPE_CHOICES = [
    ('ride_request', 'Ride Request'),
    ('ride_accepted', 'Ride Accepted'),
    ('ride_cancelled', 'Ride Cancelled'),
    ('ride_completed', 'Ride Completed'),
    ('payment_received', 'Payment Received'),
    ('payment_failed', 'Payment Failed'),
    ('driver_arrived', 'Driver Arrived'),
    ('emergency_alert', 'Emergency Alert'),
    ('promotion', 'Promotion'),
    ('system', 'System'),
]

# Emergency Types
EMERGENCY_TYPE_CHOICES = [
    ('accident', 'Accident'),
    ('breakdown', 'Vehicle Breakdown'),
    ('medical', 'Medical Emergency'),
    ('security', 'Security Issue'),
    ('harassment', 'Harassment'),
    ('other', 'Other'),
]

# Review Types
REVIEW_TYPE_CHOICES = [
    ('rider_to_driver', 'Rider to Driver'),
    ('driver_to_rider', 'Driver to Rider'),
]

# Languages
LANGUAGE_CHOICES = [
    ('en', 'English'),
    ('yo', 'Yoruba'),
    ('ha', 'Hausa'),
    ('ig', 'Igbo'),
]

# Nigerian States
NIGERIAN_STATES = [
    ('abia', 'Abia'),
    ('adamawa', 'Adamawa'),
    ('akwa_ibom', 'Akwa Ibom'),
    ('anambra', 'Anambra'),
    ('bauchi', 'Bauchi'),
    ('bayelsa', 'Bayelsa'),
    ('benue', 'Benue'),
    ('borno', 'Borno'),
    ('cross_river', 'Cross River'),
    ('delta', 'Delta'),
    ('ebonyi', 'Ebonyi'),
    ('edo', 'Edo'),
    ('ekiti', 'Ekiti'),
    ('enugu', 'Enugu'),
    ('gombe', 'Gombe'),
    ('imo', 'Imo'),
    ('jigawa', 'Jigawa'),
    ('kaduna', 'Kaduna'),
    ('kano', 'Kano'),
    ('katsina', 'Katsina'),
    ('kebbi', 'Kebbi'),
    ('kogi', 'Kogi'),
    ('kwara', 'Kwara'),
    ('lagos', 'Lagos'),
    ('nasarawa', 'Nasarawa'),
    ('niger', 'Niger'),
    ('ogun', 'Ogun'),
    ('ondo', 'Ondo'),
    ('osun', 'Osun'),
    ('oyo', 'Oyo'),
    ('plateau', 'Plateau'),
    ('rivers', 'Rivers'),
    ('sokoto', 'Sokoto'),
    ('taraba', 'Taraba'),
    ('yobe', 'Yobe'),
    ('zamfara', 'Zamfara'),
    ('fct', 'Federal Capital Territory'),
]

# Time Constants
SECONDS_IN_MINUTE = 60
MINUTES_IN_HOUR = 60
HOURS_IN_DAY = 24
DAYS_IN_WEEK = 7
DAYS_IN_MONTH = 30
DAYS_IN_YEAR = 365

# Distance Constants (in kilometers)
MAX_RIDE_DISTANCE = 500
DEFAULT_SEARCH_RADIUS = 10
MAX_SEARCH_RADIUS = 50

# Price Constants (in Naira)
MINIMUM_FARE = 200
BASE_FARE = 300
PRICE_PER_KM = 50
PRICE_PER_MINUTE = 10
CANCELLATION_FEE = 100

# Rating Constants
MIN_RATING = 1
MAX_RATING = 5
DEFAULT_RATING = 5

# File Upload Constants
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif']
ALLOWED_DOCUMENT_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png']

# Cache Keys
CACHE_KEY_USER_LOCATION = 'user_location:{user_id}'
CACHE_KEY_DRIVER_STATUS = 'driver_status:{driver_id}'
CACHE_KEY_RIDE_REQUEST = 'ride_request:{request_id}'
CACHE_KEY_NEARBY_DRIVERS = 'nearby_drivers:{lat}:{lng}'

# API Rate Limits
RATE_LIMIT_LOGIN = 5  # per minute
RATE_LIMIT_OTP = 3    # per minute
RATE_LIMIT_GENERAL = 100  # per minute

# OTP Constants
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 5
MAX_OTP_ATTEMPTS = 3

# WebSocket Events
WS_RIDE_REQUEST = 'ride_request'
WS_RIDE_ACCEPTED = 'ride_accepted'
WS_RIDE_CANCELLED = 'ride_cancelled'
WS_DRIVER_LOCATION = 'driver_location'
WS_RIDE_COMPLETED = 'ride_completed'
WS_MESSAGE_RECEIVED = 'message_received'
WS_EMERGENCY_ALERT = 'emergency_alert'

# Error Codes
ERROR_INVALID_CREDENTIALS = 'invalid_credentials'
ERROR_USER_NOT_FOUND = 'user_not_found'
ERROR_PHONE_NOT_VERIFIED = 'phone_not_verified'
ERROR_INVALID_OTP = 'invalid_otp'
ERROR_OTP_EXPIRED = 'otp_expired'
ERROR_RIDE_NOT_FOUND = 'ride_not_found'
ERROR_DRIVER_NOT_AVAILABLE = 'driver_not_available'
ERROR_PAYMENT_FAILED = 'payment_failed'
ERROR_INSUFFICIENT_FUNDS = 'insufficient_funds'
