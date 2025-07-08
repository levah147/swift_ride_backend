from celery import shared_task
from django.utils import timezone
from django.db.models import Count, Avg, Sum, F
from datetime import timedelta, date
from apps.location.models import (
    Route, LocationHistory, LocationAnalytics, PopularDestination,
    Place, TrafficCondition
)


@shared_task
def cleanup_expired_routes():
    """Clean up expired route cache entries"""
    expired_routes = Route.objects.filter(expires_at__lt=timezone.now())
    count = expired_routes.count()
    expired_routes.delete()
    
    return f"Cleaned up {count} expired routes"


@shared_task
def cleanup_old_location_history():
    """Clean up old location history (older than 30 days)"""
    cutoff_date = timezone.now() - timedelta(days=30)
    
    old_locations = LocationHistory.objects.filter(created_at__lt=cutoff_date)
    count = old_locations.count()
    old_locations.delete()
    
    return f"Cleaned up {count} old location records"


@shared_task
def update_popular_destinations():
    """Update popular destinations based on recent activity"""
    from django.db.models import Q
    
    # Calculate for the last 30 days
    start_date = timezone.now() - timedelta(days=30)
    
    # Get places with significant activity
    active_places = Place.objects.filter(
        Q(pickup_count__gt=0) | Q(dropoff_count__gt=0),
        is_active=True
    ).annotate(
        total_activity=F('pickup_count') + F('dropoff_count')
    ).filter(total_activity__gte=10)
    
    for place in active_places:
        # Calculate weekly and monthly visits
        weekly_start = timezone.now() - timedelta(days=7)
        
        # This would typically come from ride data
        weekly_visits = place.pickup_count + place.dropoff_count  # Simplified
        monthly_visits = weekly_visits * 4  # Simplified calculation
        
        # Calculate score based on various factors
        score = (
            (weekly_visits * 2) +  # Recent activity weight
            (place.search_count * 0.5) +  # Search popularity
            (10 if place.is_verified else 0)  # Verification bonus
        )
        
        # Update or create popular destination record
        PopularDestination.objects.update_or_create(
            place=place,
            destination_type='frequent',
            season='all_year',
            defaults={
                'score': score,
                'weekly_visits': weekly_visits,
                'monthly_visits': monthly_visits,
                'is_active': True,
                'last_updated': timezone.now()
            }
        )
    
    return f"Updated popular destinations for {active_places.count()} places"


@shared_task
def calculate_location_analytics():
    """Calculate daily location analytics"""
    yesterday = timezone.now().date() - timedelta(days=1)
    
    # Calculate analytics for each city
    from apps.location.models import City
    
    cities = City.objects.filter(service_available=True)
    
    for city in cities:
        calculate_city_analytics.delay(city.id, yesterday.isoformat())


@shared_task
def calculate_city_analytics(city_id, date_str):
    """Calculate analytics for a specific city and date"""
    from apps.location.models import City
    from datetime import datetime
    
    try:
        city = City.objects.get(id=city_id)
        target_date = datetime.fromisoformat(date_str).date()
        
        # Get rides for this city and date
        from apps.rides.models import Ride
        
        city_rides = Ride.objects.filter(
            pickup_city=city,
            created_at__date=target_date,
            status='completed'
        )
        
        # Calculate metrics
        total_pickups = city_rides.count()
        total_dropoffs = city_rides.filter(destination_city=city).count()
        unique_users = city_rides.values('rider').distinct().count()
        
        # Calculate revenue metrics
        revenue_data = city_rides.aggregate(
            total_revenue=Sum('final_fare'),
            average_fare=Avg('final_fare')
        )
        
        # Update or create analytics record
        LocationAnalytics.objects.update_or_create(
            city=city,
            date=target_date,
            defaults={
                'total_pickups': total_pickups,
                'total_dropoffs': total_dropoffs,
                'unique_users': unique_users,
                'total_revenue': revenue_data['total_revenue'] or 0,
                'average_fare': revenue_data['average_fare'] or 0
            }
        )
        
        return f"Analytics calculated for {city.name} on {target_date}"
        
    except Exception as e:
        return f"Error calculating analytics: {str(e)}"


@shared_task
def update_traffic_conditions():
    """Update traffic conditions for active routes"""
    # This would integrate with traffic APIs like Google Traffic or Mapbox
    
    active_routes = Route.objects.filter(
        expires_at__gt=timezone.now(),
        usage_count__gt=0
    )
    
    updated_count = 0
    
    for route in active_routes:
        try:
            # Mock traffic update (in real implementation, call traffic API)
            traffic_severity = 'moderate'  # Would come from API
            speed_kmh = 25  # Would come from API
            delay_minutes = 5  # Would come from API
            
            # Update or create traffic condition
            TrafficCondition.objects.update_or_create(
                route=route,
                defaults={
                    'severity': traffic_severity,
                    'speed_kmh': speed_kmh,
                    'delay_minutes': delay_minutes,
                    'expires_at': timezone.now() + timedelta(minutes=15),
                    'is_active': True
                }
            )
            
            updated_count += 1
            
        except Exception:
            continue  # Skip failed updates
    
    return f"Updated traffic conditions for {updated_count} routes"


@shared_task
def cleanup_expired_traffic_conditions():
    """Clean up expired traffic conditions"""
    expired_conditions = TrafficCondition.objects.filter(
        expires_at__lt=timezone.now()
    )
    
    count = expired_conditions.count()
    expired_conditions.delete()
    
    return f"Cleaned up {count} expired traffic conditions"


@shared_task
def update_place_statistics():
    """Update place usage statistics from ride data"""
    from apps.rides.models import Ride
    
    # Get recent rides (last 24 hours)
    recent_rides = Ride.objects.filter(
        created_at__gte=timezone.now() - timedelta(hours=24),
        status='completed'
    )
    
    # Update pickup counts
    pickup_stats = {}
    dropoff_stats = {}
    
    for ride in recent_rides:
        # Find nearest places for pickup and dropoff
        pickup_places = Place.objects.filter(
            latitude__range=(ride.pickup_latitude - 0.001, ride.pickup_latitude + 0.001),
            longitude__range=(ride.pickup_longitude - 0.001, ride.pickup_longitude + 0.001)
        )
        
        dropoff_places = Place.objects.filter(
            latitude__range=(ride.destination_latitude - 0.001, ride.destination_latitude + 0.001),
            longitude__range=(ride.destination_longitude - 0.001, ride.destination_longitude + 0.001)
        )
        
        # Update pickup counts
        for place in pickup_places:
            pickup_stats[place.id] = pickup_stats.get(place.id, 0) + 1
        
        # Update dropoff counts
        for place in dropoff_places:
            dropoff_stats[place.id] = dropoff_stats.get(place.id, 0) + 1
    
    # Apply updates
    for place_id, count in pickup_stats.items():
        Place.objects.filter(id=place_id).update(
            pickup_count=F('pickup_count') + count
        )
    
    for place_id, count in dropoff_stats.items():
        Place.objects.filter(id=place_id).update(
            dropoff_count=F('dropoff_count') + count
        )
    
    return f"Updated statistics for {len(pickup_stats)} pickup places and {len(dropoff_stats)} dropoff places"


@shared_task
def generate_location_insights():
    """Generate location insights and recommendations"""
    insights = []
    
    # Find underserved areas
    from apps.location.models import ServiceZone
    
    zones = ServiceZone.objects.filter(is_active=True)
    
    for zone in zones:
        # Calculate demand vs supply ratio
        recent_rides = zone.city.rides_as_pickup.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        # Find available drivers in zone
        available_drivers = 0  # Would calculate from driver locations
        
        if recent_rides > 0 and available_drivers < recent_rides * 0.1:
            insights.append({
                'type': 'underserved_area',
                'zone': zone.name,
                'city': zone.city.name,
                'demand': recent_rides,
                'supply': available_drivers,
                'recommendation': 'Increase driver incentives in this area'
            })
    
    # Store insights (would typically save to database or send notifications)
    return f"Generated {len(insights)} location insights"
