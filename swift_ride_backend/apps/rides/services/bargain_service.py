"""
Service for handling bargain operations.
"""

from datetime import timedelta
from django.utils import timezone

from apps.rides.models import Ride, BargainOffer, RideHistory


class BargainService:
    """
    Service for handling bargain operations.
    """
    
    @staticmethod
    def make_offer(ride, offered_by, amount, message=None, expires_in_minutes=5):
        """
        Make a bargain offer.
        """
        # Determine offer type
        if offered_by == ride.rider:
            offer_type = BargainOffer.OfferType.RIDER
        else:
            offer_type = BargainOffer.OfferType.DRIVER
            
        # Set expiry time
        expiry_time = timezone.now() + timedelta(minutes=expires_in_minutes)
        
        # Create offer
        offer = BargainOffer.objects.create(
            ride=ride,
            offered_by=offered_by,
            offer_type=offer_type,
            amount=amount,
            message=message,
            expiry_time=expiry_time
        )
        
        # Log in ride history
        RideHistory.objects.create(
            ride=ride,
            event_type=RideHistory.EventType.BARGAIN,
            data={
                'offer_id': str(offer.id),
                'offer_type': offer_type,
                'amount': str(amount),
                'message': message
            }
        )
        
        return offer
    
    @staticmethod
    def accept_offer(offer):
        """
        Accept a bargain offer.
        """
        if offer.is_expired:
            return False, "Offer has expired"
            
        # Update offer status
        offer.status = BargainOffer.OfferStatus.ACCEPTED
        offer.save()
        
        # Update ride
        ride = offer.ride
        ride.final_fare = offer.amount
        ride.status = Ride.RideStatus.ACCEPTED
        
        # If driver offer was accepted, assign driver to ride
        if offer.offer_type == BargainOffer.OfferType.DRIVER:
            ride.driver = offer.offered_by
        
        ride.save()
        
        # Log in ride history
        RideHistory.objects.create(
            ride=ride,
            event_type=RideHistory.EventType.STATUS_CHANGE,
            previous_status=Ride.RideStatus.BARGAINING,
            new_status=Ride.RideStatus.ACCEPTED,
            data={
                'offer_id': str(offer.id),
                'final_fare': str(offer.amount)
            }
        )
        
        # Set all other pending offers for this ride to expired
        BargainOffer.objects.filter(
            ride=ride,
            status=BargainOffer.OfferStatus.PENDING
        ).exclude(id=offer.id).update(
            status=BargainOffer.OfferStatus.EXPIRED
        )
        
        return True, "Offer accepted successfully"
    
    @staticmethod
    def reject_offer(offer):
        """
        Reject a bargain offer.
        """
        if offer.is_expired:
            return False, "Offer has expired"
            
        # Update offer status
        offer.status = BargainOffer.OfferStatus.REJECTED
        offer.save()
        
        # Log in ride history
        RideHistory.objects.create(
            ride=offer.ride,
            event_type=RideHistory.EventType.BARGAIN,
            data={
                'offer_id': str(offer.id),
                'action': 'rejected'
            }
        )
        
        return True, "Offer rejected successfully"
    
    @staticmethod
    def counter_offer(original_offer, amount, message=None):
        """
        Make a counter offer.
        """
        if original_offer.is_expired:
            return None, "Original offer has expired"
            
        # Determine counter offer type (opposite of original)
        if original_offer.offer_type == BargainOffer.OfferType.RIDER:
            offer_type = BargainOffer.OfferType.DRIVER
            offered_by = original_offer.ride.driver
        else:
            offer_type = BargainOffer.OfferType.RIDER
            offered_by = original_offer.ride.rider
            
        # Set expiry time
        expiry_time = timezone.now() + timedelta(minutes=5)
        
        # Update original offer status
        original_offer.status = BargainOffer.OfferStatus.COUNTERED
        original_offer.save()
        
        # Create counter offer
        counter = BargainOffer.objects.create(
            ride=original_offer.ride,
            offered_by=offered_by,
            offer_type=offer_type,
            amount=amount,
            message=message,
            expiry_time=expiry_time
        )
        
        # Link counter offer to original
        counter.counter_offer = original_offer
        counter.save()
        
        # Log in ride history
        RideHistory.objects.create(
            ride=original_offer.ride,
            event_type=RideHistory.EventType.BARGAIN,
            data={
                'original_offer_id': str(original_offer.id),
                'counter_offer_id': str(counter.id),
                'amount': str(amount),
                'message': message
            }
        )
        
        return counter, "Counter offer created successfully"
