from django.contrib.auth import get_user_model
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from typing import Dict, List, Any, Optional
import logging
import random

from ..models import Recommendation, AIModel
from apps.rides.models import Ride
from apps.promotions.models import Promotion
from apps.vehicles.models import Vehicle

User = get_user_model()
logger = logging.getLogger(__name__)


class RecommendationService:
    """AI-powered recommendation service"""
    
    def __init__(self):
        self.model_version = "1.0.0"
    
    def generate_recommendations(
        self, 
        user: User, 
        recommendation_type: str = None,
        context: Dict[str, Any] = None,
        limit: int = 5
    ) -> List[Recommendation]:
        """Generate personalized recommendations for a user"""
        
        if context is None:
            context = {}
        
        recommendations = []
        
        try:
            # Get or create recommendation model
            model = self._get_or_create_model('recommendation_engine')
            
            # Generate different types of recommendations
            if recommendation_type is None or recommendation_type == 'driver':
                recommendations.extend(self._recommend_drivers(user, model, context, limit))
            
            if recommendation_type is None or recommendation_type == 'destination':
                recommendations.extend(self._recommend_destinations(user, model, context, limit))
            
            if recommendation_type is None or recommendation_type == 'promotion':
                recommendations.extend(self._recommend_promotions(user, model, context, limit))
            
            if recommendation_type is None or recommendation_type == 'vehicle':
                recommendations.extend(self._recommend_vehicles(user, model, context, limit))
            
            if recommendation_type is None or recommendation_type == 'timing':
                recommendations.extend(self._recommend_timing(user, model, context, limit))
            
            if recommendation_type == 'onboarding':
                recommendations.extend(self._recommend_onboarding(user, model, context, limit))
            
            # Sort by confidence and priority
            recommendations.sort(key=lambda x: (x.priority, x.confidence_score), reverse=True)
            
            # Limit results
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Error generating recommendations for user {user.id}: {str(e)}")
            return []
    
    def _recommend_drivers(
        self, 
        user: User, 
        model: AIModel, 
        context: Dict[str, Any], 
        limit: int
    ) -> List[Recommendation]:
        """Recommend drivers based on user preferences and history"""
        
        recommendations = []
        
        try:
            # Get user's ride history to understand preferences
            user_rides = user.rides_as_passenger.filter(
                status='completed',
                driver_rating__isnull=False
            ).order_by('-created_at')[:20]
            
            if not user_rides.exists():
                return recommendations
            
            # Analyze preferred driver characteristics
            avg_rating_given = user_rides.aggregate(avg_rating=Avg('driver_rating'))['avg_rating']
            
            # Find highly rated drivers in user's area
            pickup_location = context.get('pickup_location')
            if pickup_location:
                # Get available drivers near pickup location
                available_drivers = User.objects.filter(
                    driver_profile__is_available=True,
                    driver_profile__current_latitude__range=[
                        pickup_location['lat'] - 0.01, 
                        pickup_location['lat'] + 0.01
                    ],
                    driver_profile__current_longitude__range=[
                        pickup_location['lng'] - 0.01, 
                        pickup_location['lng'] + 0.01
                    ]
                ).select_related('driver_profile')[:10]
                
                for driver in available_drivers:
                    # Calculate recommendation score
                    driver_rating = driver.driver_profile.average_rating or 4.0
                    total_rides = driver.rides_as_driver.count()
                    
                    # Confidence based on driver's experience and rating
                    confidence = min(0.9, (driver_rating / 5.0) * (min(total_rides, 100) / 100))
                    
                    if confidence > 0.6:  # Only recommend drivers with good confidence
                        recommendation = Recommendation.objects.create(
                            user=user,
                            model=model,
                            recommendation_type='driver',
                            title=f"Highly Rated Driver: {driver.get_full_name()}",
                            description=f"Driver with {driver_rating:.1f} rating and {total_rides} completed rides",
                            recommendation_data={
                                'driver_id': driver.id,
                                'driver_name': driver.get_full_name(),
                                'rating': driver_rating,
                                'total_rides': total_rides,
                                'estimated_arrival': random.randint(3, 8)  # Simplified
                            },
                            confidence_score=confidence,
                            priority=int(confidence * 10),
                            context=context,
                            expires_at=timezone.now() + timedelta(minutes=30)
                        )
                        recommendations.append(recommendation)
            
        except Exception as e:
            logger.error(f"Error recommending drivers: {str(e)}")
        
        return recommendations[:limit]
    
    def _recommend_destinations(
        self, 
        user: User, 
        model: AIModel, 
        context: Dict[str, Any], 
        limit: int
    ) -> List[Recommendation]:
        """Recommend destinations based on user history and patterns"""
        
        recommendations = []
        
        try:
            # Get user's frequent destinations
            frequent_destinations = user.rides_as_passenger.filter(
                status='completed',
                destination_latitude__isnull=False,
                destination_longitude__isnull=False
            ).values(
                'destination_latitude', 
                'destination_longitude', 
                'destination_address'
            ).annotate(
                visit_count=Count('id')
            ).order_by('-visit_count')[:10]
            
            current_time = timezone.now()
            current_hour = current_time.hour
            current_day = current_time.weekday()
            
            for dest in frequent_destinations:
                # Check if this destination is relevant for current time
                similar_time_rides = user.rides_as_passenger.filter(
                    destination_latitude=dest['destination_latitude'],
                    destination_longitude=dest['destination_longitude'],
                    created_at__hour__range=[current_hour-1, current_hour+1],
                    created_at__week_day=current_day+1  # Django uses 1-7 for weekdays
                ).count()
                
                if similar_time_rides > 0:
                    confidence = min(0.9, (dest['visit_count'] / 10) + (similar_time_rides / 5))
                    
                    recommendation = Recommendation.objects.create(
                        user=user,
                        model=model,
                        recommendation_type='destination',
                        title=f"Frequent Destination",
                        description=f"You've visited this location {dest['visit_count']} times",
                        recommendation_data={
                            'latitude': dest['destination_latitude'],
                            'longitude': dest['destination_longitude'],
                            'address': dest['destination_address'],
                            'visit_count': dest['visit_count'],
                            'time_relevance': similar_time_rides
                        },
                        confidence_score=confidence,
                        priority=dest['visit_count'],
                        context=context,
                        expires_at=timezone.now() + timedelta(hours=2)
                    )
                    recommendations.append(recommendation)
            
        except Exception as e:
            logger.error(f"Error recommending destinations: {str(e)}")
        
        return recommendations[:limit]
    
    def _recommend_promotions(
        self, 
        user: User, 
        model: AIModel, 
        context: Dict[str, Any], 
        limit: int
    ) -> List[Recommendation]:
        """Recommend relevant promotions to user"""
        
        recommendations = []
        
        try:
            # Get active promotions that user is eligible for
            active_promotions = Promotion.objects.filter(
                is_active=True,
                start_date__lte=timezone.now(),
                end_date__gte=timezone.now()
            )
            
            # Filter promotions based on user eligibility
            eligible_promotions = []
            for promotion in active_promotions:
                # Check if user has already used this promotion
                if not promotion.usage_records.filter(user=user).exists():
                    # Check user type eligibility
                    if promotion.eligible_user_types == 'all' or user.user_type in promotion.eligible_user_types:
                        eligible_promotions.append(promotion)
            
            # Rank promotions by relevance
            for promotion in eligible_promotions[:limit]:
                # Calculate relevance based on promotion value and user behavior
                discount_value = promotion.discount_amount or (promotion.discount_percentage * 20)  # Estimate value
                
                # Higher confidence for bigger discounts and newer users
                user_ride_count = user.rides_as_passenger.count()
                confidence = min(0.9, (discount_value / 50) + (max(0, 20 - user_ride_count) / 20))
                
                recommendation = Recommendation.objects.create(
                    user=user,
                    model=model,
                    recommendation_type='promotion',
                    title=f"Special Offer: {promotion.title}",
                    description=promotion.description,
                    recommendation_data={
                        'promotion_id': promotion.id,
                        'promotion_code': promotion.code,
                        'discount_amount': float(promotion.discount_amount) if promotion.discount_amount else None,
                        'discount_percentage': float(promotion.discount_percentage) if promotion.discount_percentage else None,
                        'expires_at': promotion.end_date.isoformat()
                    },
                    confidence_score=confidence,
                    priority=int(discount_value),
                    context=context,
                    expires_at=promotion.end_date
                )
                recommendations.append(recommendation)
            
        except Exception as e:
            logger.error(f"Error recommending promotions: {str(e)}")
        
        return recommendations[:limit]
    
    def _recommend_vehicles(
        self, 
        user: User, 
        model: AIModel, 
        context: Dict[str, Any], 
        limit: int
    ) -> List[Recommendation]:
        """Recommend vehicle types based on user preferences and trip context"""
        
        recommendations = []
        
        try:
            # Analyze user's vehicle preferences from ride history
            vehicle_preferences = user.rides_as_passenger.filter(
                status='completed',
                vehicle__isnull=False
            ).values('vehicle__vehicle_type').annotate(
                usage_count=Count('id'),
                avg_rating=Avg('passenger_rating')
            ).order_by('-usage_count')
            
            trip_context = context.get('trip_context', {})
            distance = trip_context.get('distance_km', 10)
            passenger_count = trip_context.get('passenger_count', 1)
            
            # Vehicle type recommendations based on context
            vehicle_recommendations = []
            
            if distance > 50:  # Long trip
                vehicle_recommendations.append({
                    'type': 'premium',
                    'reason': 'Comfortable for long trips',
                    'confidence': 0.8
                })
            elif passenger_count > 2:  # Multiple passengers
                vehicle_recommendations.append({
                    'type': 'suv',
                    'reason': 'More space for multiple passengers',
                    'confidence': 0.9
                })
            else:  # Standard trip
                vehicle_recommendations.append({
                    'type': 'economy',
                    'reason': 'Cost-effective option',
                    'confidence': 0.7
                })
            
            # Create recommendations
            for vehicle_rec in vehicle_recommendations[:limit]:
                recommendation = Recommendation.objects.create(
                    user=user,
                    model=model,
                    recommendation_type='vehicle',
                    title=f"Recommended: {vehicle_rec['type'].title()} Vehicle",
                    description=vehicle_rec['reason'],
                    recommendation_data={
                        'vehicle_type': vehicle_rec['type'],
                        'reason': vehicle_rec['reason'],
                        'trip_context': trip_context
                    },
                    confidence_score=vehicle_rec['confidence'],
                    priority=int(vehicle_rec['confidence'] * 10),
                    context=context,
                    expires_at=timezone.now() + timedelta(hours=1)
                )
                recommendations.append(recommendation)
            
        except Exception as e:
            logger.error(f"Error recommending vehicles: {str(e)}")
        
        return recommendations[:limit]
    
    def _recommend_timing(
        self, 
        user: User, 
        model: AIModel, 
        context: Dict[str, Any], 
        limit: int
    ) -> List[Recommendation]:
        """Recommend optimal timing for rides"""
        
        recommendations = []
        
        try:
            current_time = timezone.now()
            current_hour = current_time.hour
            
            # Analyze when user typically takes rides
            user_ride_patterns = user.rides_as_passenger.filter(
                status='completed'
            ).extra(
                select={'hour': 'EXTRACT(hour FROM created_at)'}
            ).values('hour').annotate(
                ride_count=Count('id')
            ).order_by('-ride_count')
            
            # Suggest optimal times based on traffic and pricing
            timing_suggestions = []
            
            if current_hour in [7, 8, 17, 18]:  # Rush hours
                timing_suggestions.append({
                    'suggestion': 'Wait 30 minutes for lower prices',
                    'reason': 'Avoid rush hour surge pricing',
                    'confidence': 0.8,
                    'wait_time': 30
                })
            elif current_hour in [22, 23, 0, 1]:  # Late night
                timing_suggestions.append({
                    'suggestion': 'Book now for night service',
                    'reason': 'Limited drivers available later',
                    'confidence': 0.7,
                    'wait_time': 0
                })
            else:
                timing_suggestions.append({
                    'suggestion': 'Good time to book',
                    'reason': 'Normal pricing and availability',
                    'confidence': 0.6,
                    'wait_time': 0
                })
            
            for timing in timing_suggestions[:limit]:
                recommendation = Recommendation.objects.create(
                    user=user,
                    model=model,
                    recommendation_type='timing',
                    title=f"Timing Suggestion",
                    description=timing['suggestion'],
                    recommendation_data={
                        'suggestion': timing['suggestion'],
                        'reason': timing['reason'],
                        'wait_time_minutes': timing['wait_time'],
                        'current_hour': current_hour
                    },
                    confidence_score=timing['confidence'],
                    priority=int(timing['confidence'] * 10),
                    context=context,
                    expires_at=timezone.now() + timedelta(minutes=60)
                )
                recommendations.append(recommendation)
            
        except Exception as e:
            logger.error(f"Error recommending timing: {str(e)}")
        
        return recommendations[:limit]
    
    def _recommend_onboarding(
        self, 
        user: User, 
        model: AIModel, 
        context: Dict[str, Any], 
        limit: int
    ) -> List[Recommendation]:
        """Generate onboarding recommendations for new users"""
        
        recommendations = []
        
        try:
            onboarding_items = [
                {
                    'title': 'Complete Your Profile',
                    'description': 'Add your photo and preferences for a better experience',
                    'action': 'complete_profile',
                    'priority': 10
                },
                {
                    'title': 'Add Payment Method',
                    'description': 'Add a payment method for seamless rides',
                    'action': 'add_payment',
                    'priority': 9
                },
                {
                    'title': 'Set Home Location',
                    'description': 'Save your home address for quick booking',
                    'action': 'set_home',
                    'priority': 8
                },
                {
                    'title': 'Invite Friends',
                    'description': 'Refer friends and earn ride credits',
                    'action': 'refer_friends',
                    'priority': 7
                },
                {
                    'title': 'Book Your First Ride',
                    'description': 'Get 20% off your first ride with code WELCOME20',
                    'action': 'first_ride',
                    'priority': 10
                }
            ]
            
            for item in onboarding_items[:limit]:
                recommendation = Recommendation.objects.create(
                    user=user,
                    model=model,
                    recommendation_type='service',
                    title=item['title'],
                    description=item['description'],
                    recommendation_data={
                        'action': item['action'],
                        'onboarding_step': True
                    },
                    confidence_score=0.9,
                    priority=item['priority'],
                    context=context,
                    expires_at=timezone.now() + timedelta(days=7)
                )
                recommendations.append(recommendation)
            
        except Exception as e:
            logger.error(f"Error generating onboarding recommendations: {str(e)}")
        
        return recommendations[:limit]
    
    def get_user_recommendations(
        self, 
        user: User, 
        recommendation_type: str = None,
        status: str = 'pending',
        limit: int = 10
    ) -> List[Recommendation]:
        """Get existing recommendations for a user"""
        
        queryset = user.ai_recommendations.filter(status=status)
        
        if recommendation_type:
            queryset = queryset.filter(recommendation_type=recommendation_type)
        
        # Filter out expired recommendations
        queryset = queryset.filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        )
        
        return list(queryset.order_by('-priority', '-confidence_score')[:limit])
    
    def track_recommendation_interaction(
        self, 
        recommendation_id: str, 
        interaction_type: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Track user interaction with recommendations"""
        
        try:
            recommendation = Recommendation.objects.get(id=recommendation_id)
            
            if interaction_type == 'shown':
                recommendation.mark_as_shown()
            elif interaction_type == 'clicked':
                recommendation.mark_as_clicked()
            elif interaction_type == 'accepted':
                recommendation.mark_as_accepted()
            elif interaction_type == 'rejected':
                recommendation.mark_as_rejected()
            
            return True
            
        except Recommendation.DoesNotExist:
            logger.error(f"Recommendation {recommendation_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error tracking recommendation interaction: {str(e)}")
            return False
    
    def get_recommendation_performance(
        self, 
        recommendation_type: str = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get performance metrics for recommendations"""
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        queryset = Recommendation.objects.filter(created_at__range=[start_date, end_date])
        
        if recommendation_type:
            queryset = queryset.filter(recommendation_type=recommendation_type)
        
        total_recommendations = queryset.count()
        shown_recommendations = queryset.filter(status__in=['shown', 'clicked', 'accepted']).count()
        clicked_recommendations = queryset.filter(status__in=['clicked', 'accepted']).count()
        accepted_recommendations = queryset.filter(status='accepted').count()
        
        # Calculate rates
        show_rate = (shown_recommendations / total_recommendations * 100) if total_recommendations > 0 else 0
        click_rate = (clicked_recommendations / shown_recommendations * 100) if shown_recommendations > 0 else 0
        acceptance_rate = (accepted_recommendations / shown_recommendations * 100) if shown_recommendations > 0 else 0
        
        return {
            'total_recommendations': total_recommendations,
            'shown_recommendations': shown_recommendations,
            'clicked_recommendations': clicked_recommendations,
            'accepted_recommendations': accepted_recommendations,
            'show_rate': round(show_rate, 2),
            'click_rate': round(click_rate, 2),
            'acceptance_rate': round(acceptance_rate, 2),
            'period_days': days
        }
    
    def _get_or_create_model(self, model_type: str) -> AIModel:
        """Get or create an AI model for recommendations"""
        
        model, created = AIModel.objects.get_or_create(
            name=f"{model_type}_model",
            model_type='recommendation',
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
