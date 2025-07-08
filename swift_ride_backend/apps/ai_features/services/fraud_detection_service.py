from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta
from typing import Dict, List, Any, Optional, Tuple
import logging
import json
from decimal import Decimal 

from ..models import FraudAlert, AIModel
from apps.rides.models import Ride
from apps.payments.models import Payment, Transaction

User = get_user_model()
logger = logging.getLogger(__name__)


class FraudDetectionService:
    """AI-powered fraud detection service"""
    
    def __init__(self):
        self.model_version = "1.0.0"
        self.risk_thresholds = {
            'low': 0.3,
            'medium': 0.6,
            'high': 0.8,
            'critical': 0.95
        }
    
    def detect_payment_fraud(
        self, 
        payment_data: Dict[str, Any],
        user: User = None
    ) -> Dict[str, Any]:
        """Detect potential payment fraud"""
        
        try:
            risk_score = 0.0
            risk_factors = []
            
            # Amount-based risk assessment
            amount = Decimal(str(payment_data.get('amount', 0)))
            if amount > 500:  # High amount transactions
                risk_score += 0.3
                risk_factors.append('high_amount')
            elif amount > 1000:  # Very high amount
                risk_score += 0.5
                risk_factors.append('very_high_amount')
            
            # User behavior analysis
            if user:
                # Check for unusual spending patterns
                recent_payments = Payment.objects.filter(
                    user=user,
                    created_at__gte=timezone.now() - timedelta(days=7)
                ).aggregate(
                    total_amount=Sum('amount'),
                    payment_count=Count('id'),
                    avg_amount=Avg('amount')
                )
                
                avg_amount = recent_payments['avg_amount'] or 0
                if avg_amount > 0 and amount > avg_amount * 3:
                    risk_score += 0.2
                    risk_factors.append('unusual_amount_pattern')
                
                # Check payment frequency
                payment_count = recent_payments['payment_count'] or 0
                if payment_count > 20:  # Too many payments in short time
                    risk_score += 0.3
                    risk_factors.append('high_frequency_payments')
            
            # Payment method risk
            payment_method = payment_data.get('payment_method', '')
            if payment_method in ['new_card', 'unknown']:
                risk_score += 0.1
                risk_factors.append('new_payment_method')
            
            # Location-based risk
            location = payment_data.get('location', {})
            if location:
                # Check if payment location is far from user's usual locations
                if user and self._is_unusual_location(user, location):
                    risk_score += 0.2
                    risk_factors.append('unusual_location')
            
            # Time-based risk
            current_hour = timezone.now().hour
            if current_hour < 6 or current_hour > 23:  # Late night transactions
                risk_score += 0.1
                risk_factors.append('unusual_time')
            
            # Normalize risk score
            risk_score = min(1.0, risk_score)
            
            # Determine severity
            severity = self._calculate_severity(risk_score)
            
            # Create fraud alert if risk is significant
            if risk_score > self.risk_thresholds['medium']:
                model = self._get_or_create_model('fraud_detection')
                
                alert = FraudAlert.objects.create(
                    model=model,
                    user=user,
                    alert_type='payment_fraud',
                    severity=severity,
                    title=f"Suspicious Payment Activity",
                    description=f"Payment of ${amount} flagged for review",
                    detection_data={
                        'payment_data': payment_data,
                        'risk_factors': risk_factors,
                        'analysis_timestamp': timezone.now().isoformat()
                    },
                    risk_score=risk_score,
                    confidence_score=0.8
                )
                
                return {
                    'fraud_detected': True,
                    'risk_score': risk_score,
                    'severity': severity,
                    'risk_factors': risk_factors,
                    'alert_id': alert.id,
                    'recommended_action': self._get_recommended_action(risk_score)
                }
            
            return {
                'fraud_detected': False,
                'risk_score': risk_score,
                'severity': 'low',
                'risk_factors': risk_factors
            }
            
        except Exception as e:
            logger.error(f"Error detecting payment fraud: {str(e)}")
            return {
                'fraud_detected': False,
                'error': str(e),
                'risk_score': 0.0
            }
    
    def detect_account_fraud(self, user: User) -> Dict[str, Any]:
        """Detect potential account fraud or suspicious behavior"""
        
        try:
            risk_score = 0.0
            risk_factors = []
            
            # Account age analysis
            account_age = (timezone.now() - user.date_joined).days
            if account_age < 1:  # Very new account
                risk_score += 0.2
                risk_factors.append('new_account')
            
            # Profile completeness
            profile_score = 0
            if user.first_name and user.last_name:
                profile_score += 1
            if user.phone_number:
                profile_score += 1
            if hasattr(user, 'profile') and user.profile.profile_picture:
                profile_score += 1
            
            if profile_score < 2:  # Incomplete profile
                risk_score += 0.1
                risk_factors.append('incomplete_profile')
            
            # Activity patterns
            total_rides = user.rides_as_passenger.count()
            if total_rides == 0 and account_age > 30:
                risk_score += 0.2
                risk_factors.append('no_activity')
            
            # Multiple account detection (simplified)
            similar_accounts = User.objects.filter(
                phone_number=user.phone_number
            ).exclude(id=user.id).count()
            
            if similar_accounts > 0:
                risk_score += 0.4
                risk_factors.append('multiple_accounts')
            
            # Rapid successive actions
            recent_actions = user.rides_as_passenger.filter(
                created_at__gte=timezone.now() - timedelta(hours=1)
            ).count()
            
            if recent_actions > 10:  # Too many rides in short time
                risk_score += 0.3
                risk_factors.append('rapid_actions')
            
            # Normalize risk score
            risk_score = min(1.0, risk_score)
            severity = self._calculate_severity(risk_score)
            
            # Create alert if needed
            if risk_score > self.risk_thresholds['medium']:
                model = self._get_or_create_model('fraud_detection')
                
                alert = FraudAlert.objects.create(
                    model=model,
                    user=user,
                    alert_type='account_fraud',
                    severity=severity,
                    title=f"Suspicious Account Activity",
                    description=f"Account {user.email} flagged for review",
                    detection_data={
                        'user_data': {
                            'account_age_days': account_age,
                            'total_rides': total_rides,
                            'profile_completeness': profile_score
                        },
                        'risk_factors': risk_factors
                    },
                    risk_score=risk_score,
                    confidence_score=0.7
                )
                
                return {
                    'fraud_detected': True,
                    'risk_score': risk_score,
                    'severity': severity,
                    'risk_factors': risk_factors,
                    'alert_id': alert.id
                }
            
            return {
                'fraud_detected': False,
                'risk_score': risk_score,
                'severity': 'low',
                'risk_factors': risk_factors
            }
            
        except Exception as e:
            logger.error(f"Error detecting account fraud for user {user.id}: {str(e)}")
            return {
                'fraud_detected': False,
                'error': str(e),
                'risk_score': 0.0
            }
    
    def detect_ride_fraud(self, ride_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect potential ride fraud"""
        
        try:
            risk_score = 0.0
            risk_factors = []
            
            # Distance and time analysis
            distance = ride_data.get('distance_km', 0)
            duration = ride_data.get('duration_minutes', 0)
            
            if distance > 0 and duration > 0:
                speed = (distance / duration) * 60  # km/h
                if speed > 120:  # Unrealistic speed
                    risk_score += 0.4
                    risk_factors.append('unrealistic_speed')
                elif speed < 5:  # Too slow
                    risk_score += 0.2
                    risk_factors.append('unusually_slow')
            
            # Route analysis
            pickup_location = ride_data.get('pickup_location', {})
            destination_location = ride_data.get('destination_location', {})
            
            if pickup_location and destination_location:
                # Check if pickup and destination are the same
                lat_diff = abs(pickup_location.get('lat', 0) - destination_location.get('lat', 0))
                lng_diff = abs(pickup_location.get('lng', 0) - destination_location.get('lng', 0))
                
                if lat_diff < 0.001 and lng_diff < 0.001:  # Same location
                    risk_score += 0.3
                    risk_factors.append('same_pickup_destination')
            
            # Fare analysis
            fare = ride_data.get('fare_amount', 0)
            if distance > 0:
                fare_per_km = fare / distance
                if fare_per_km > 10:  # Very high fare per km
                    risk_score += 0.2
                    risk_factors.append('high_fare_rate')
                elif fare_per_km < 0.5:  # Very low fare per km
                    risk_score += 0.3
                    risk_factors.append('low_fare_rate')
            
            # Time-based analysis
            ride_time = ride_data.get('created_at')
            if ride_time:
                hour = ride_time.hour if hasattr(ride_time, 'hour') else 12
                if hour < 4 or hour > 23:  # Very late/early rides
                    risk_score += 0.1
                    risk_factors.append('unusual_ride_time')
            
            # Frequency analysis
            user_id = ride_data.get('user_id')
            if user_id:
                recent_rides = Ride.objects.filter(
                    passenger_id=user_id,
                    created_at__gte=timezone.now() - timedelta(hours=1)
                ).count()
                
                if recent_rides > 5:  # Too many rides in short time
                    risk_score += 0.3
                    risk_factors.append('high_frequency_rides')
            
            # Normalize risk score
            risk_score = min(1.0, risk_score)
            severity = self._calculate_severity(risk_score)
            
            # Create alert if needed
            if risk_score > self.risk_thresholds['medium']:
                model = self._get_or_create_model('fraud_detection')
                
                alert = FraudAlert.objects.create(
                    model=model,
                    user_id=user_id,
                    alert_type='ride_fraud',
                    severity=severity,
                    title=f"Suspicious Ride Activity",
                    description=f"Ride flagged for unusual patterns",
                    detection_data={
                        'ride_data': ride_data,
                        'risk_factors': risk_factors
                    },
                    risk_score=risk_score,
                    confidence_score=0.75
                )
                
                return {
                    'fraud_detected': True,
                    'risk_score': risk_score,
                    'severity': severity,
                    'risk_factors': risk_factors,
                    'alert_id': alert.id
                }
            
            return {
                'fraud_detected': False,
                'risk_score': risk_score,
                'severity': 'low',
                'risk_factors': risk_factors
            }
            
        except Exception as e:
            logger.error(f"Error detecting ride fraud: {str(e)}")
            return {
                'fraud_detected': False,
                'error': str(e),
                'risk_score': 0.0
            }
    
    def analyze_user_trust_score(self, user: User) -> Dict[str, Any]:
        """Calculate comprehensive trust score for a user"""
        
        try:
            trust_score = 1.0  # Start with full trust
            trust_factors = []
            
            # Account verification factors
            if user.email_verified:
                trust_factors.append('email_verified')
            else:
                trust_score -= 0.1
            
            if user.phone_verified:
                trust_factors.append('phone_verified')
            else:
                trust_score -= 0.1
            
            # Activity history
            total_rides = user.rides_as_passenger.count()
            completed_rides = user.rides_as_passenger.filter(status='completed').count()
            
            if total_rides > 0:
                completion_rate = completed_rides / total_rides
                if completion_rate > 0.9:
                    trust_factors.append('high_completion_rate')
                elif completion_rate < 0.7:
                    trust_score -= 0.2
                    trust_factors.append('low_completion_rate')
            
            # Rating analysis
            avg_rating = user.rides_as_passenger.filter(
                passenger_rating__isnull=False
            ).aggregate(avg_rating=Avg('passenger_rating'))['avg_rating']
            
            if avg_rating:
                if avg_rating >= 4.5:
                    trust_factors.append('high_rating')
                elif avg_rating < 3.0:
                    trust_score -= 0.3
                    trust_factors.append('low_rating')
            
            # Payment history
            failed_payments = Payment.objects.filter(
                user=user,
                status='failed'
            ).count()
            
            total_payments = Payment.objects.filter(user=user).count()
            
            if total_payments > 0:
                payment_success_rate = (total_payments - failed_payments) / total_payments
                if payment_success_rate < 0.8:
                    trust_score -= 0.2
                    trust_factors.append('payment_issues')
            
            # Fraud history
            fraud_alerts = FraudAlert.objects.filter(
                user=user,
                status__in=['open', 'investigating']
            ).count()
            
            if fraud_alerts > 0:
                trust_score -= 0.4
                trust_factors.append('active_fraud_alerts')
            
            # Account age bonus
            account_age_days = (timezone.now() - user.date_joined).days
            if account_age_days > 365:  # Account older than 1 year
                trust_score += 0.1
                trust_factors.append('established_account')
            
            # Normalize trust score
            trust_score = max(0.0, min(1.0, trust_score))
            
            # Determine trust level
            if trust_score >= 0.8:
                trust_level = 'high'
            elif trust_score >= 0.6:
                trust_level = 'medium'
            elif trust_score >= 0.4:
                trust_level = 'low'
            else:
                trust_level = 'very_low'
            
            return {
                'trust_score': round(trust_score, 3),
                'trust_level': trust_level,
                'trust_factors': trust_factors,
                'metrics': {
                    'total_rides': total_rides,
                    'completion_rate': round(completion_rate, 3) if total_rides > 0 else 0,
                    'average_rating': round(avg_rating, 2) if avg_rating else None,
                    'payment_success_rate': round(payment_success_rate, 3) if total_payments > 0 else 0,
                    'active_fraud_alerts': fraud_alerts,
                    'account_age_days': account_age_days
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing trust score for user {user.id}: {str(e)}")
            return {
                'trust_score': 0.5,
                'trust_level': 'unknown',
                'error': str(e)
            }
    
    def get_fraud_alerts(
        self, 
        alert_type: str = None,
        severity: str = None,
        status: str = None,
        limit: int = 50
    ) -> List[FraudAlert]:
        """Get fraud alerts with optional filtering"""
        
        queryset = FraudAlert.objects.all()
        
        if alert_type:
            queryset = queryset.filter(alert_type=alert_type)
        
        if severity:
            queryset = queryset.filter(severity=severity)
        
        if status:
            queryset = queryset.filter(status=status)
        
        return list(queryset.order_by('-created_at')[:limit])
    
    def _is_unusual_location(self, user: User, location: Dict[str, float]) -> bool:
        """Check if location is unusual for the user"""
        
        try:
            # Get user's recent ride locations
            recent_rides = user.rides_as_passenger.filter(
                created_at__gte=timezone.now() - timedelta(days=30),
                pickup_latitude__isnull=False,
                pickup_longitude__isnull=False
            )[:20]
            
            if not recent_rides:
                return False  # No history to compare
            
            # Calculate average distance from usual locations
            total_distance = 0
            for ride in recent_rides:
                lat_diff = abs(float(ride.pickup_latitude) - location['lat'])
                lng_diff = abs(float(ride.pickup_longitude) - location['lng'])
                distance = (lat_diff + lng_diff) * 111  # Rough km conversion
                total_distance += distance
            
            avg_distance = total_distance / len(recent_rides)
            
            # Consider unusual if more than 50km from average location
            return avg_distance > 50
            
        except Exception:
            return False
    
    def _calculate_severity(self, risk_score: float) -> str:
        """Calculate severity level based on risk score"""
        
        if risk_score >= self.risk_thresholds['critical']:
            return 'critical'
        elif risk_score >= self.risk_thresholds['high']:
            return 'high'
        elif risk_score >= self.risk_thresholds['medium']:
            return 'medium'
        else:
            return 'low'
    
    def _get_recommended_action(self, risk_score: float) -> str:
        """Get recommended action based on risk score"""
        
        if risk_score >= self.risk_thresholds['critical']:
            return 'block_transaction'
        elif risk_score >= self.risk_thresholds['high']:
            return 'require_verification'
        elif risk_score >= self.risk_thresholds['medium']:
            return 'manual_review'
        else:
            return 'monitor'
    
    def _get_or_create_model(self, model_type: str) -> AIModel:
        """Get or create an AI model for fraud detection"""
        
        model, created = AIModel.objects.get_or_create(
            name=f"{model_type}_model",
            model_type='classification',
            version=self.model_version,
            defaults={
                'description': f'AI model for {model_type}',
                'framework': 'custom',
                'status': 'active',
                'config': {},
                'hyperparameters': {}
            }
        )
        
        return model
