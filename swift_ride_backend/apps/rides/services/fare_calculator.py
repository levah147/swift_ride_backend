"""
Fare calculation service for rides.
"""

from decimal import Decimal
from datetime import datetime
from typing import Dict, Optional
from django.utils import timezone
from django.conf import settings

from apps.rides.utils import calculate_distance, get_surge_multiplier


class FareCalculator:
    """
    Service for calculating ride fares with various factors.
    """
    
    # Base fare structure (in Naira)
    BASE_FARE = Decimal('200.00')
    PER_KM_RATE = Decimal('80.00')
    PER_MINUTE_RATE = Decimal('15.00')
    MINIMUM_FARE = Decimal('300.00')
    
    # Vehicle type multipliers
    VEHICLE_MULTIPLIERS = {
        'motorcycle': Decimal('0.7'),
        'tricycle': Decimal('0.8'),
        'sedan': Decimal('1.0'),
        'hatchback': Decimal('0.9'),
        'suv': Decimal('1.3'),
        'bus': Decimal('1.5'),
    }
    
    # Time-based multipliers
    PEAK_HOUR_MULTIPLIER = Decimal('1.5')
    LATE_NIGHT_MULTIPLIER = Decimal('1.3')
    WEEKEND_MULTIPLIER = Decimal('1.2')
    
    @classmethod
    def calculate_base_fare(cls, distance_km: float, duration_minutes: int) -> Decimal:
        """
        Calculate base fare without any multipliers.
        """
        distance_fare = Decimal(str(distance_km)) * cls.PER_KM_RATE
        time_fare = Decimal(str(duration_minutes)) * cls.PER_MINUTE_RATE
        
        total_fare = cls.BASE_FARE + distance_fare + time_fare
        
        return max(total_fare, cls.MINIMUM_FARE)
    
    @classmethod
    def calculate_estimated_fare(cls, pickup_lat: float, pickup_lon: float,
                               dropoff_lat: float, dropoff_lon: float,
                               vehicle_type: str = 'sedan',
                               scheduled_time: Optional[datetime] = None) -> Dict:
        """
        Calculate estimated fare with all applicable multipliers.
        """
        # Calculate distance and estimated duration
        distance_km = calculate_distance(pickup_lat, pickup_lon, dropoff_lat, dropoff_lon)
        duration_minutes = cls._estimate_duration(distance_km)
        
        # Calculate base fare
        base_fare = cls.calculate_base_fare(distance_km, duration_minutes)
        
        # Apply vehicle type multiplier
        vehicle_multiplier = cls.VEHICLE_MULTIPLIERS.get(vehicle_type, Decimal('1.0'))
        fare_with_vehicle = base_fare * vehicle_multiplier
        
        # Apply time-based multipliers
        time_multiplier = cls._get_time_multiplier(scheduled_time or timezone.now())
        fare_with_time = fare_with_vehicle * time_multiplier
        
        # Apply surge pricing
        surge_multiplier = get_surge_multiplier(pickup_lat, pickup_lon, scheduled_time)
        final_fare = fare_with_time * Decimal(str(surge_multiplier))
        
        # Round to nearest 10 Naira
        final_fare = cls._round_fare(final_fare)
        
        return {
            'base_fare': float(base_fare),
            'vehicle_multiplier': float(vehicle_multiplier),
            'time_multiplier': float(time_multiplier),
            'surge_multiplier': surge_multiplier,
            'estimated_fare': float(final_fare),
            'distance_km': distance_km,
            'duration_minutes': duration_minutes,
            'breakdown': {
                'base_charge': float(cls.BASE_FARE),
                'distance_charge': float(Decimal(str(distance_km)) * cls.PER_KM_RATE),
                'time_charge': float(Decimal(str(duration_minutes)) * cls.PER_MINUTE_RATE),
                'vehicle_adjustment': float(fare_with_vehicle - base_fare),
                'time_adjustment': float(fare_with_time - fare_with_vehicle),
                'surge_adjustment': float(final_fare - fare_with_time),
            }
        }
    
    @classmethod
    def calculate_cancellation_fee(cls, ride_status: str, time_since_booking: int) -> Decimal:
        """
        Calculate cancellation fee based on ride status and timing.
        """
        if ride_status in ['requested', 'searching']:
            return Decimal('0.00')  # No fee for early cancellation
        
        elif ride_status == 'accepted':
            if time_since_booking < 5:  # Less than 5 minutes
                return Decimal('0.00')
            else:
                return Decimal('50.00')  # Small fee
        
        elif ride_status in ['driver_assigned', 'driver_arrived']:
            return Decimal('100.00')  # Higher fee
        
        else:
            return Decimal('0.00')  # No cancellation for rides in progress
    
    @classmethod
    def calculate_waiting_fee(cls, waiting_minutes: int) -> Decimal:
        """
        Calculate waiting fee for drivers.
        """
        if waiting_minutes <= 5:
            return Decimal('0.00')  # Free waiting time
        
        # Charge for waiting time beyond 5 minutes
        chargeable_minutes = waiting_minutes - 5
        waiting_rate = Decimal('20.00')  # 20 Naira per minute
        
        return Decimal(str(chargeable_minutes)) * waiting_rate
    
    @classmethod
    def calculate_toll_fee(cls, route_data: Dict) -> Decimal:
        """
        Calculate toll fees based on route data.
        """
        # This would integrate with mapping services to detect toll roads
        # For now, return a simple calculation based on distance
        
        toll_roads_km = route_data.get('toll_distance_km', 0)
        if toll_roads_km > 0:
            toll_rate = Decimal('50.00')  # 50 Naira per km on toll roads
            return Decimal(str(toll_roads_km)) * toll_rate
        
        return Decimal('0.00')
    
    @classmethod
    def calculate_airport_fee(cls, pickup_location: str, dropoff_location: str) -> Decimal:
        """
        Calculate airport pickup/dropoff fee.
        """
        airport_keywords = ['airport', 'international airport', 'domestic airport']
        
        is_airport_pickup = any(keyword in pickup_location.lower() for keyword in airport_keywords)
        is_airport_dropoff = any(keyword in dropoff_location.lower() for keyword in airport_keywords)
        
        if is_airport_pickup or is_airport_dropoff:
            return Decimal('200.00')  # Airport fee
        
        return Decimal('0.00')
    
    @classmethod
    def calculate_night_fee(cls, pickup_time: datetime) -> Decimal:
        """
        Calculate night service fee.
        """
        hour = pickup_time.hour
        
        # Night hours: 11 PM to 5 AM
        if hour >= 23 or hour <= 5:
            return Decimal('100.00')  # Night service fee
        
        return Decimal('0.00')
    
    @classmethod
    def calculate_total_fare(cls, base_fare: Decimal, additional_fees: Dict) -> Decimal:
        """
        Calculate total fare including all additional fees.
        """
        total = base_fare
        
        for fee_name, fee_amount in additional_fees.items():
            total += Decimal(str(fee_amount))
        
        return cls._round_fare(total)
    
    @classmethod
    def calculate_driver_earnings(cls, total_fare: Decimal, commission_rate: float = 0.20) -> Dict:
        """
        Calculate driver earnings after platform commission.
        """
        commission = total_fare * Decimal(str(commission_rate))
        driver_earnings = total_fare - commission
        
        return {
            'total_fare': float(total_fare),
            'commission_rate': commission_rate,
            'commission_amount': float(commission),
            'driver_earnings': float(driver_earnings)
        }
    
    @classmethod
    def calculate_refund_amount(cls, original_fare: Decimal, cancellation_reason: str,
                              time_since_booking: int) -> Decimal:
        """
        Calculate refund amount based on cancellation reason and timing.
        """
        if cancellation_reason == 'driver_no_show':
            return original_fare  # Full refund
        
        elif cancellation_reason == 'rider_cancelled':
            cancellation_fee = cls.calculate_cancellation_fee('accepted', time_since_booking)
            return max(Decimal('0.00'), original_fare - cancellation_fee)
        
        elif cancellation_reason == 'system_error':
            return original_fare  # Full refund
        
        else:
            return Decimal('0.00')  # No refund
    
    @classmethod
    def _estimate_duration(cls, distance_km: float) -> int:
        """
        Estimate ride duration based on distance.
        """
        # Average speed in city traffic (km/h)
        avg_speed = 25
        
        # Calculate time in hours, then convert to minutes
        time_hours = distance_km / avg_speed
        time_minutes = time_hours * 60
        
        # Add buffer time for stops, traffic lights, etc.
        buffer_minutes = max(5, distance_km * 2)
        
        return int(time_minutes + buffer_minutes)
    
    @classmethod
    def _get_time_multiplier(cls, ride_time: datetime) -> Decimal:
        """
        Get time-based multiplier for fare calculation.
        """
        hour = ride_time.hour
        weekday = ride_time.weekday()
        
        multiplier = Decimal('1.0')
        
        # Peak hours (7-9 AM, 5-7 PM on weekdays)
        if weekday < 5 and ((7 <= hour <= 9) or (17 <= hour <= 19)):
            multiplier = cls.PEAK_HOUR_MULTIPLIER
        
        # Late night (11 PM - 5 AM)
        elif hour >= 23 or hour <= 5:
            multiplier = cls.LATE_NIGHT_MULTIPLIER
        
        # Weekend premium (Friday evening to Sunday)
        elif weekday >= 4:
            multiplier = cls.WEEKEND_MULTIPLIER
        
        return multiplier
    
    @classmethod
    def _round_fare(cls, fare: Decimal) -> Decimal:
        """
        Round fare to nearest 10 Naira.
        """
        # Round to nearest 10
        rounded = (fare / 10).quantize(Decimal('1')) * 10
        return rounded
    
    @classmethod
    def get_fare_estimate_range(cls, pickup_lat: float, pickup_lon: float,
                              dropoff_lat: float, dropoff_lon: float,
                              vehicle_type: str = 'sedan') -> Dict:
        """
        Get fare estimate range (min and max possible fares).
        """
        # Calculate base estimate
        base_estimate = cls.calculate_estimated_fare(
            pickup_lat, pickup_lon, dropoff_lat, dropoff_lon, vehicle_type
        )
        
        # Calculate minimum fare (no surge, off-peak)
        distance_km = base_estimate['distance_km']
        duration_minutes = base_estimate['duration_minutes']
        
        min_fare = cls.calculate_base_fare(distance_km, duration_minutes)
        min_fare *= cls.VEHICLE_MULTIPLIERS.get(vehicle_type, Decimal('1.0'))
        min_fare = cls._round_fare(min_fare)
        
        # Calculate maximum fare (with maximum surge)
        max_fare = min_fare * cls.PEAK_HOUR_MULTIPLIER * Decimal('3.0')  # Max surge
        max_fare = cls._round_fare(max_fare)
        
        return {
            'min_fare': float(min_fare),
            'max_fare': float(max_fare),
            'estimated_fare': base_estimate['estimated_fare'],
            'distance_km': distance_km,
            'duration_minutes': duration_minutes
        }
