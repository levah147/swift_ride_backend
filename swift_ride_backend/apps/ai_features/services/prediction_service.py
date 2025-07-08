from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
import json
from decimal import Decimal
import math
import random

from ..models import PredictionResult, AIModel
from apps.rides.models import Ride
from apps.analytics.models import UserAnalytics, RideAnalytics

User = get_user_model()

logger = logging.getLogger(__name__)


class PredictionService:
    """AI-powered prediction service"""
    
    def __init__(self):
        self.model_version = "1.0.0"
    
    def predict_demand(
        self, 
        location: Dict[str, float], 
        time_range: Dict[str, datetime],
        context: Dict[str, Any] = None
    ) -> PredictionResult:
        """Predict ride demand for a specific location and time"""
        
        if context is None:
            context = {}
        
        try:
            # Get historical data for the location and time
            historical_rides = Ride.objects.filter(
                pickup_latitude__range=[location['lat'] - 0.01, location['lat'] + 0.01],
                pickup_longitude__range=[location['lng'] - 0.01, location['lng'] + 0.01],
                created_at__time__range=[
                    time_range['start'].time(),
                    time_range['end'].time()
                ]
            ).count()
            
            # Simple demand prediction based on historical data
            base_demand = historical_rides / 30  # Average per day
            
            # Apply contextual factors
            demand_multiplier = 1.0
            
            # Weekend factor
            if time_range['start'].weekday() >= 5:  # Saturday or Sunday
                demand_multiplier *= 1.2
            
            # Rush hour factor
            hour = time_range['start'].hour
            if hour in [7, 8, 9, 17, 18, 19]:  # Rush hours
                demand_multiplier *= 1.5
            
            # Weather factor (if provided in context)
            weather = context.get('weather', {})
            if weather.get('condition') == 'rain':
                demand_multiplier *= 1.3
            elif weather.get('condition') == 'snow':
                demand_multiplier *= 1.6
            
            predicted_demand = int(base_demand * demand_multiplier)
            confidence = min(0.9, historical_rides / 100)  # Higher confidence with more data
            
            # Create prediction result
            model = self._get_or_create_model('demand_forecast')
            
            prediction = PredictionResult.objects.create(
                model=model,
                prediction_type='demand_forecast',
                input_data={
                    'location': location,
                    'time_range': {
                        'start': time_range['start'].isoformat(),
                        'end': time_range['end'].isoformat()
                    },
                    'context': context
                },
                prediction_value={
                    'predicted_demand': predicted_demand,
                    'demand_multiplier': demand_multiplier,
                    'base_demand': base_demand
                },
                confidence_score=confidence,
                context=context
            )
            
            return prediction
            
        except Exception as e:
            # Log error and return default prediction
            logger.error(f"Error predicting demand: {str(e)}")
            
            # Return default prediction
            model = self._get_or_create_model('demand_forecast')
            return PredictionResult.objects.create(
                model=model,
                prediction_type='demand_forecast',
                input_data={
                    'location': location,
                    'time_range': time_range,
                    'context': context
                },
                prediction_value={'predicted_demand': 5, 'confidence': 'low'},
                confidence_score=0.3,
                context=context or {}
            )
    
    def predict_price(
        self, 
        pickup_location: Dict[str, float],
        destination_location: Dict[str, float],
        time: datetime,
        vehicle_type: str = 'economy',
        context: Dict[str, Any] = None
    ) -> PredictionResult:
        """Predict optimal price for a ride"""
        
        if context is None:
            context = {}
        
        try:
            # Calculate base distance (simplified)
            lat_diff = destination_location['lat'] - pickup_location['lat']
            lng_diff = destination_location['lng'] - pickup_location['lng']
            distance_km = math.sqrt(lat_diff**2 + lng_diff**2) * 111  # Rough conversion to km
            
            # Base pricing
            base_rates = {
                'economy': 1.5,
                'premium': 2.5,
                'luxury': 4.0,
                'shared': 1.0
            }
            
            base_price = distance_km * base_rates.get(vehicle_type, 1.5)
            
            # Dynamic pricing factors
            price_multiplier = 1.0
            
            # Time-based pricing
            hour = time.hour
            if hour in [7, 8, 9, 17, 18, 19]:  # Rush hours
                price_multiplier *= 1.3
            elif hour >= 22 or hour <= 5:  # Night hours
                price_multiplier *= 1.2
            
            # Weekend pricing
            if time.weekday() >= 5:
                price_multiplier *= 1.1
            
            # Weather factor
            weather = context.get('weather', {})
            if weather.get('condition') in ['rain', 'snow']:
                price_multiplier *= 1.2
            
            # Demand factor (simplified)
            current_demand = context.get('current_demand', 1.0)
            if current_demand > 1.5:
                price_multiplier *= 1.4
            elif current_demand < 0.7:
                price_multiplier *= 0.9
            
            predicted_price = round(base_price * price_multiplier, 2)
            confidence = 0.8  # Base confidence for price prediction
            
            model = self._get_or_create_model('price_optimization')
            
            prediction = PredictionResult.objects.create(
                model=model,
                prediction_type='price_optimization',
                input_data={
                    'pickup_location': pickup_location,
                    'destination_location': destination_location,
                    'time': time.isoformat(),
                    'vehicle_type': vehicle_type,
                    'context': context
                },
                prediction_value={
                    'predicted_price': predicted_price,
                    'base_price': base_price,
                    'price_multiplier': price_multiplier,
                    'distance_km': distance_km,
                    'pricing_factors': {
                        'time_factor': hour in [7, 8, 9, 17, 18, 19] or hour >= 22 or hour <= 5,
                        'weekend_factor': time.weekday() >= 5,
                        'weather_factor': weather.get('condition') in ['rain', 'snow'],
                        'demand_factor': current_demand
                    }
                },
                confidence_score=confidence,
                context=context
            )
            
            return prediction
            
        except Exception as e:
            logger.error(f"Error predicting price: {str(e)}")
            
            # Return default prediction
            model = self._get_or_create_model('price_optimization')
            return PredictionResult.objects.create(
                model=model,
                prediction_type='price_optimization',
                input_data={
                    'pickup_location': pickup_location,
                    'destination_location': destination_location,
                    'time': time.isoformat(),
                    'vehicle_type': vehicle_type
                },
                prediction_value={'predicted_price': 15.0, 'confidence': 'low'},
                confidence_score=0.3,
                context=context or {}
            )
    
    def predict_churn(self, user: User, context: Dict[str, Any] = None) -> PredictionResult:
        """Predict user churn probability"""
        
        if context is None:
            context = {}
        
        try:
            # Calculate churn indicators
            now = timezone.now()
            
            # Recent activity
            last_ride = user.rides_as_passenger.order_by('-created_at').first()
            days_since_last_ride = (now - last_ride.created_at).days if last_ride else 365
            
            # Ride frequency
            rides_last_30_days = user.rides_as_passenger.filter(
                created_at__gte=now - timedelta(days=30)
            ).count()
            
            rides_last_90_days = user.rides_as_passenger.filter(
                created_at__gte=now - timedelta(days=90)
            ).count()
            
            # User engagement
            total_rides = user.rides_as_passenger.count()
            account_age_days = (now - user.date_joined).days
            
            # Calculate churn probability
            churn_score = 0.0
            
            # Days since last ride factor
            if days_since_last_ride > 60:
                churn_score += 0.4
            elif days_since_last_ride > 30:
                churn_score += 0.2
            elif days_since_last_ride > 14:
                churn_score += 0.1
            
            # Ride frequency factor
            if rides_last_30_days == 0:
                churn_score += 0.3
            elif rides_last_30_days < 2:
                churn_score += 0.15
            
            # Declining usage pattern
            if rides_last_90_days > 0:
                recent_frequency = rides_last_30_days / 30
                overall_frequency = rides_last_90_days / 90
                if recent_frequency < overall_frequency * 0.5:
                    churn_score += 0.2
            
            # Account age factor (new users might churn more)
            if account_age_days < 30 and total_rides < 3:
                churn_score += 0.15
            
            churn_probability = min(1.0, churn_score)
            confidence = 0.75 if total_rides > 5 else 0.6
            
            # Determine risk level
            if churn_probability >= 0.7:
                risk_level = 'high'
            elif churn_probability >= 0.4:
                risk_level = 'medium'
            else:
                risk_level = 'low'
            
            model = self._get_or_create_model('churn_prediction')
            
            prediction = PredictionResult.objects.create(
                model=model,
                prediction_type='churn_prediction',
                input_data={
                    'user_id': user.id,
                    'days_since_last_ride': days_since_last_ride,
                    'rides_last_30_days': rides_last_30_days,
                    'rides_last_90_days': rides_last_90_days,
                    'total_rides': total_rides,
                    'account_age_days': account_age_days,
                    'context': context
                },
                prediction_value={
                    'churn_probability': churn_probability,
                    'risk_level': risk_level,
                    'contributing_factors': {
                        'inactivity': days_since_last_ride > 30,
                        'low_frequency': rides_last_30_days < 2,
                        'declining_usage': rides_last_30_days < rides_last_90_days / 3,
                        'new_user_risk': account_age_days < 30 and total_rides < 3
                    },
                    'recommendations': self._get_churn_prevention_recommendations(churn_probability, risk_level)
                },
                confidence_score=confidence,
                context=context
            )
            
            return prediction
            
        except Exception as e:
            logger.error(f"Error predicting churn for user {user.id}: {str(e)}")
            
            # Return default prediction
            model = self._get_or_create_model('churn_prediction')
            return PredictionResult.objects.create(
                model=model,
                prediction_type='churn_prediction',
                input_data={'user_id': user.id, 'context': context},
                prediction_value={'churn_probability': 0.3, 'risk_level': 'medium'},
                confidence_score=0.4,
                context=context or {}
            )
    
    def _get_churn_prevention_recommendations(self, churn_probability: float, risk_level: str) -> List[str]:
        """Get recommendations for preventing user churn"""
        
        recommendations = []
        
        if risk_level == 'high':
            recommendations.extend([
                "Send personalized discount offer (30-50% off next ride)",
                "Reach out with customer support call",
                "Offer loyalty program enrollment",
                "Send win-back email campaign"
            ])
        elif risk_level == 'medium':
            recommendations.extend([
                "Send targeted promotion email",
                "Offer ride credit or bonus",
                "Recommend new features",
                "Send satisfaction survey"
            ])
        else:
            recommendations.extend([
                "Continue regular engagement",
                "Offer referral incentives",
                "Share app updates and improvements"
            ])
        
        return recommendations
    
    def _get_or_create_model(self, model_type: str) -> AIModel:
        """Get or create an AI model for predictions"""
        
        model, created = AIModel.objects.get_or_create(
            name=f"{model_type}_model",
            model_type=model_type.split('_')[0],
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
