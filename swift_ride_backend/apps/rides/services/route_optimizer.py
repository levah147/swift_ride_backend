"""
Route optimization service for efficient ride routing.
"""

from typing import List, Dict, Tuple, Optional
from decimal import Decimal
from dataclasses import dataclass
import heapq
from django.core.cache import cache

from apps.rides.models import Ride
from apps.rides.utils import calculate_distance, calculate_bearing


@dataclass
class RoutePoint:
    """
    Represents a point in a route.
    """
    latitude: float
    longitude: float
    address: str
    point_type: str  # 'pickup', 'dropoff', 'waypoint'
    ride_id: Optional[str] = None
    estimated_time: Optional[int] = None  # minutes from start


@dataclass
class OptimizedRoute:
    """
    Represents an optimized route.
    """
    points: List[RoutePoint]
    total_distance_km: float
    total_duration_minutes: int
    efficiency_score: float
    estimated_earnings: Decimal


class RouteOptimizer:
    """
    Service for optimizing driver routes and ride assignments.
    """
    
    # Optimization parameters
    MAX_DETOUR_PERCENTAGE = 0.3  # 30% maximum detour
    MAX_ROUTE_DURATION = 480  # 8 hours maximum
    EFFICIENCY_WEIGHT_DISTANCE = 0.4
    EFFICIENCY_WEIGHT_TIME = 0.3
    EFFICIENCY_WEIGHT_EARNINGS = 0.3
    
    @classmethod
    def optimize_driver_route(cls, driver_id: str, available_rides: List[Ride],
                            current_location: Tuple[float, float] = None) -> OptimizedRoute:
        """
        Optimize route for a driver considering multiple available rides.
        """
        if not available_rides:
            return OptimizedRoute([], 0.0, 0, 0.0, Decimal('0.00'))
        
        # Get driver's current location
        if not current_location:
            current_location = cls._get_driver_location(driver_id)
        
        if not current_location:
            # Use first ride's pickup as starting point
            current_location = (
                float(available_rides[0].pickup_latitude),
                float(available_rides[0].pickup_longitude)
            )
        
        # Generate route points from available rides
        route_points = cls._generate_route_points(available_rides)
        
        # Find optimal route using nearest neighbor with improvements
        optimal_route = cls._find_optimal_route(current_location, route_points)
        
        return optimal_route
    
    @classmethod
    def suggest_ride_sequence(cls, driver_id: str, rides: List[Ride]) -> List[Dict]:
        """
        Suggest the best sequence to handle multiple rides.
        """
        if len(rides) <= 1:
            return [{'ride': ride, 'priority': 1} for ride in rides]
        
        # Get driver location
        driver_location = cls._get_driver_location(driver_id)
        
        suggestions = []
        
        for i, ride in enumerate(rides):
            # Calculate priority based on multiple factors
            priority_score = cls._calculate_ride_priority(
                ride, driver_location, rides
            )
            
            suggestions.append({
                'ride': ride,
                'priority': priority_score,
                'estimated_pickup_time': cls._estimate_pickup_time(ride, driver_location),
                'efficiency_rating': cls._calculate_efficiency_rating(ride, rides)
            })
        
        # Sort by priority (higher is better)
        suggestions.sort(key=lambda x: x['priority'], reverse=True)
        
        return suggestions
    
    @classmethod
    def find_optimal_pickup_order(cls, rides: List[Ride], 
                                driver_location: Tuple[float, float]) -> List[Ride]:
        """
        Find optimal order to pick up multiple riders (ride sharing).
        """
        if len(rides) <= 1:
            return rides
        
        # Create pickup points
        pickup_points = []
        for ride in rides:
            pickup_points.append({
                'ride': ride,
                'location': (float(ride.pickup_latitude), float(ride.pickup_longitude)),
                'urgency': cls._calculate_pickup_urgency(ride)
            })
        
        # Use traveling salesman approach for small numbers
        if len(pickup_points) <= 6:
            return cls._tsp_pickup_order(driver_location, pickup_points)
        else:
            # Use greedy nearest neighbor for larger numbers
            return cls._greedy_pickup_order(driver_location, pickup_points)
    
    @classmethod
    def calculate_route_efficiency(cls, route_points: List[RoutePoint],
                                 start_location: Tuple[float, float]) -> float:
        """
        Calculate efficiency score for a route (0-1, higher is better).
        """
        if not route_points:
            return 0.0
        
        # Calculate total distance
        total_distance = 0.0
        current_location = start_location
        
        for point in route_points:
            distance = calculate_distance(
                current_location[0], current_location[1],
                point.latitude, point.longitude
            )
            total_distance += distance
            current_location = (point.latitude, point.longitude)
        
        # Calculate direct distances (if all rides were separate)
        direct_distance = 0.0
        for point in route_points:
            if point.point_type == 'pickup':
                # Distance from start to pickup, then pickup to dropoff
                pickup_distance = calculate_distance(
                    start_location[0], start_location[1],
                    point.latitude, point.longitude
                )
                
                # Find corresponding dropoff
                dropoff_point = next(
                    (p for p in route_points 
                     if p.ride_id == point.ride_id and p.point_type == 'dropoff'),
                    None
                )
                
                if dropoff_point:
                    ride_distance = calculate_distance(
                        point.latitude, point.longitude,
                        dropoff_point.latitude, dropoff_point.longitude
                    )
                    direct_distance += pickup_distance + ride_distance
        
        # Efficiency is inverse of distance ratio
        if direct_distance > 0:
            efficiency = min(direct_distance / total_distance, 1.0)
        else:
            efficiency = 0.0
        
        return efficiency
    
    @classmethod
    def suggest_strategic_positioning(cls, driver_id: str, 
                                    historical_data: Dict = None) -> List[Dict]:
        """
        Suggest strategic positions for drivers to maximize ride opportunities.
        """
        # This would use historical data, current demand patterns, etc.
        # For now, return some common strategic locations
        
        strategic_locations = [
            {
                'name': 'Airport Terminal',
                'latitude': 6.5774,
                'longitude': 3.3213,
                'reason': 'High demand for airport rides',
                'expected_wait_time': 15,
                'demand_score': 0.9
            },
            {
                'name': 'Victoria Island Business District',
                'latitude': 6.4281,
                'longitude': 3.4219,
                'reason': 'Business hours demand',
                'expected_wait_time': 10,
                'demand_score': 0.8
            },
            {
                'name': 'Ikeja Shopping Mall',
                'latitude': 6.6018,
                'longitude': 3.3515,
                'reason': 'Shopping and entertainment hub',
                'expected_wait_time': 20,
                'demand_score': 0.7
            }
        ]
        
        # Get driver's current location
        driver_location = cls._get_driver_location(driver_id)
        
        # Calculate distance to each strategic location
        for location in strategic_locations:
            if driver_location:
                distance = calculate_distance(
                    driver_location[0], driver_location[1],
                    location['latitude'], location['longitude']
                )
                location['distance_km'] = distance
                location['travel_time_minutes'] = int(distance * 2.5)  # Rough estimate
            else:
                location['distance_km'] = 0
                location['travel_time_minutes'] = 0
        
        # Sort by demand score and distance
        strategic_locations.sort(
            key=lambda x: (x['demand_score'], -x['distance_km']), 
            reverse=True
        )
        
        return strategic_locations
    
    @classmethod
    def _generate_route_points(cls, rides: List[Ride]) -> List[RoutePoint]:
        """
        Generate route points from rides.
        """
        points = []
        
        for ride in rides:
            # Add pickup point
            points.append(RoutePoint(
                latitude=float(ride.pickup_latitude),
                longitude=float(ride.pickup_longitude),
                address=ride.pickup_location,
                point_type='pickup',
                ride_id=str(ride.id)
            ))
            
            # Add dropoff point
            points.append(RoutePoint(
                latitude=float(ride.dropoff_latitude),
                longitude=float(ride.dropoff_longitude),
                address=ride.dropoff_location,
                point_type='dropoff',
                ride_id=str(ride.id)
            ))
        
        return points
    
    @classmethod
    def _find_optimal_route(cls, start_location: Tuple[float, float],
                          route_points: List[RoutePoint]) -> OptimizedRoute:
        """
        Find optimal route using nearest neighbor with 2-opt improvements.
        """
        if not route_points:
            return OptimizedRoute([], 0.0, 0, 0.0, Decimal('0.00'))
        
        # Separate pickup and dropoff points
        pickup_points = [p for p in route_points if p.point_type == 'pickup']
        dropoff_points = [p for p in route_points if p.point_type == 'dropoff']
        
        # Start with nearest neighbor for pickups
        ordered_points = []
        current_location = start_location
        remaining_pickups = pickup_points.copy()
        
        # Add pickups in optimal order
        while remaining_pickups:
            # Find nearest pickup
            nearest_pickup = min(
                remaining_pickups,
                key=lambda p: calculate_distance(
                    current_location[0], current_location[1],
                    p.latitude, p.longitude
                )
            )
            
            ordered_points.append(nearest_pickup)
            remaining_pickups.remove(nearest_pickup)
            current_location = (nearest_pickup.latitude, nearest_pickup.longitude)
            
            # Add corresponding dropoff if it makes sense
            corresponding_dropoff = next(
                (p for p in dropoff_points if p.ride_id == nearest_pickup.ride_id),
                None
            )
            
            if corresponding_dropoff:
                # Check if we should dropoff now or later
                if cls._should_dropoff_immediately(
                    nearest_pickup, corresponding_dropoff, remaining_pickups
                ):
                    ordered_points.append(corresponding_dropoff)
                    current_location = (corresponding_dropoff.latitude, corresponding_dropoff.longitude)
        
        # Add any remaining dropoffs
        added_dropoffs = {p.ride_id for p in ordered_points if p.point_type == 'dropoff'}
        for dropoff in dropoff_points:
            if dropoff.ride_id not in added_dropoffs:
                ordered_points.append(dropoff)
        
        # Calculate route metrics
        total_distance = cls._calculate_total_distance(start_location, ordered_points)
        total_duration = cls._estimate_total_duration(total_distance, len(ordered_points))
        efficiency_score = cls.calculate_route_efficiency(ordered_points, start_location)
        estimated_earnings = cls._calculate_estimated_earnings(ordered_points)
        
        return OptimizedRoute(
            points=ordered_points,
            total_distance_km=total_distance,
            total_duration_minutes=total_duration,
            efficiency_score=efficiency_score,
            estimated_earnings=estimated_earnings
        )
    
    @classmethod
    def _calculate_ride_priority(cls, ride: Ride, driver_location: Tuple[float, float],
                               all_rides: List[Ride]) -> float:
        """
        Calculate priority score for a ride.
        """
        score = 0.0
        
        # Distance factor (closer is better)
        if driver_location:
            distance = calculate_distance(
                driver_location[0], driver_location[1],
                float(ride.pickup_latitude), float(ride.pickup_longitude)
            )
            distance_score = max(0, 1 - (distance / 20))  # Normalize to 20km max
            score += distance_score * 0.3
        
        # Fare factor (higher fare is better)
        if ride.estimated_fare:
            fare_score = min(float(ride.estimated_fare) / 2000, 1.0)  # Normalize to 2000 Naira
            score += fare_score * 0.3
        
        # Time factor (newer requests have higher priority)
        from django.utils import timezone
        age_minutes = (timezone.now() - ride.created_at).total_seconds() / 60
        time_score = max(0, 1 - (age_minutes / 60))  # Normalize to 1 hour
        score += time_score * 0.2
        
        # Route efficiency factor
        efficiency_score = cls._calculate_route_efficiency_with_ride(ride, all_rides)
        score += efficiency_score * 0.2
        
        return score
    
    @classmethod
    def _get_driver_location(cls, driver_id: str) -> Optional[Tuple[float, float]]:
        """
        Get driver's current location from cache.
        """
        from apps.rides.services.ride_tracker import RideTracker
        
        location_data = RideTracker.get_driver_location(driver_id)
        if location_data:
            return (location_data['latitude'], location_data['longitude'])
        
        return None
    
    @classmethod
    def _calculate_total_distance(cls, start_location: Tuple[float, float],
                                points: List[RoutePoint]) -> float:
        """
        Calculate total distance for a route.
        """
        total_distance = 0.0
        current_location = start_location
        
        for point in points:
            distance = calculate_distance(
                current_location[0], current_location[1],
                point.latitude, point.longitude
            )
            total_distance += distance
            current_location = (point.latitude, point.longitude)
        
        return total_distance
    
    @classmethod
    def _estimate_total_duration(cls, total_distance: float, num_stops: int) -> int:
        """
        Estimate total duration for a route.
        """
        # Base travel time (assuming 25 km/h average speed)
        travel_time = (total_distance / 25) * 60  # minutes
        
        # Add stop time (5 minutes per stop)
        stop_time = num_stops * 5
        
        return int(travel_time + stop_time)
    
    @classmethod
    def _calculate_estimated_earnings(cls, points: List[RoutePoint]) -> Decimal:
        """
        Calculate estimated earnings for a route.
        """
        # This would integrate with fare calculation
        # For now, return a simple estimate
        
        ride_ids = {p.ride_id for p in points if p.ride_id}
        estimated_earnings = len(ride_ids) * Decimal('800.00')  # Average fare
        
        return estimated_earnings
    
    @classmethod
    def _should_dropoff_immediately(cls, pickup: RoutePoint, dropoff: RoutePoint,
                                  remaining_pickups: List[RoutePoint]) -> bool:
        """
        Determine if passenger should be dropped off immediately or later.
        """
        if not remaining_pickups:
            return True
        
        # Calculate detour if we dropoff now
        pickup_to_dropoff = calculate_distance(
            pickup.latitude, pickup.longitude,
            dropoff.latitude, dropoff.longitude
        )
        
        # Find nearest remaining pickup
        nearest_pickup = min(
            remaining_pickups,
            key=lambda p: calculate_distance(
                pickup.latitude, pickup.longitude,
                p.latitude, p.longitude
            )
        )
        
        pickup_to_next = calculate_distance(
            pickup.latitude, pickup.longitude,
            nearest_pickup.latitude, nearest_pickup.longitude
        )
        
        dropoff_to_next = calculate_distance(
            dropoff.latitude, dropoff.longitude,
            nearest_pickup.latitude, nearest_pickup.longitude
        )
        
        # If detour is small, dropoff immediately
        detour = (pickup_to_dropoff + dropoff_to_next) - pickup_to_next
        return detour < 2.0  # Less than 2km detour
    
    @classmethod
    def _calculate_pickup_urgency(cls, ride: Ride) -> float:
        """
        Calculate urgency score for pickup.
        """
        from django.utils import timezone
        
        # Base urgency
        urgency = 0.5
        
        # Time-based urgency (older requests are more urgent)
        age_minutes = (timezone.now() - ride.created_at).total_seconds() / 60
        urgency += min(age_minutes / 30, 0.5)  # Max 0.5 for 30+ minutes
        
        # Fare-based urgency (higher fare = higher urgency)
        if ride.estimated_fare:
            fare_urgency = min(float(ride.estimated_fare) / 2000, 0.3)
            urgency += fare_urgency
        
        return min(urgency, 1.0)
    
    @classmethod
    def _tsp_pickup_order(cls, start_location: Tuple[float, float],
                         pickup_points: List[Dict]) -> List[Ride]:
        """
        Solve traveling salesman problem for pickup order (small instances).
        """
        # Simplified TSP using nearest neighbor
        ordered_rides = []
        current_location = start_location
        remaining_points = pickup_points.copy()
        
        while remaining_points:
            # Find nearest point considering urgency
            nearest_point = min(
                remaining_points,
                key=lambda p: (
                    calculate_distance(
                        current_location[0], current_location[1],
                        p['location'][0], p['location'][1]
                    ) / (p['urgency'] + 0.1)  # Divide by urgency to prioritize urgent rides
                )
            )
            
            ordered_rides.append(nearest_point['ride'])
            remaining_points.remove(nearest_point)
            current_location = nearest_point['location']
        
        return ordered_rides
    
    @classmethod
    def _greedy_pickup_order(cls, start_location: Tuple[float, float],
                           pickup_points: List[Dict]) -> List[Ride]:
        """
        Greedy nearest neighbor for pickup order (larger instances).
        """
        return cls._tsp_pickup_order(start_location, pickup_points)
    
    @classmethod
    def _calculate_route_efficiency_with_ride(cls, ride: Ride, all_rides: List[Ride]) -> float:
        """
        Calculate how efficiently a ride fits with other rides.
        """
        # Simplified efficiency calculation
        # In production, this would consider actual route optimization
        
        if len(all_rides) <= 1:
            return 1.0
        
        # Check if ride is in similar direction as others
        ride_bearing = calculate_bearing(
            float(ride.pickup_latitude), float(ride.pickup_longitude),
            float(ride.dropoff_latitude), float(ride.dropoff_longitude)
        )
        
        similar_direction_count = 0
        for other_ride in all_rides:
            if other_ride.id == ride.id:
                continue
            
            other_bearing = calculate_bearing(
                float(other_ride.pickup_latitude), float(other_ride.pickup_longitude),
                float(other_ride.dropoff_latitude), float(other_ride.dropoff_longitude)
            )
            
            bearing_diff = abs(ride_bearing - other_bearing)
            if bearing_diff <= 45 or bearing_diff >= 315:  # Similar direction
                similar_direction_count += 1
        
        return similar_direction_count / max(len(all_rides) - 1, 1)
    
    @classmethod
    def _estimate_pickup_time(cls, ride: Ride, driver_location: Tuple[float, float]) -> int:
        """
        Estimate time to pickup in minutes.
        """
        if not driver_location:
            return 15  # Default estimate
        
        distance = calculate_distance(
            driver_location[0], driver_location[1],
            float(ride.pickup_latitude), float(ride.pickup_longitude)
        )
        
        # Estimate time based on distance (25 km/h average speed)
        time_minutes = (distance / 25) * 60
        
        return max(int(time_minutes), 5)  # Minimum 5 minutes
    
    @classmethod
    def _calculate_efficiency_rating(cls, ride: Ride, all_rides: List[Ride]) -> float:
        """
        Calculate efficiency rating for a ride.
        """
        # This is a simplified version
        # In production, consider factors like:
        # - Distance efficiency
        # - Time efficiency  
        # - Earnings potential
        # - Route compatibility
        
        base_rating = 0.5
        
        # Distance factor
        ride_distance = calculate_distance(
            float(ride.pickup_latitude), float(ride.pickup_longitude),
            float(ride.dropoff_latitude), float(ride.dropoff_longitude)
        )
        
        if ride_distance > 5:  # Longer rides are more efficient
            base_rating += 0.2
        
        # Fare factor
        if ride.estimated_fare and ride.estimated_fare > Decimal('1000'):
            base_rating += 0.3
        
        return min(base_rating, 1.0)
