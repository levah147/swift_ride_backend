"""
Bargain handling service for ride negotiations.
"""

from decimal import Decimal
from datetime import timedelta
from typing import Tuple, Optional
from django.utils import timezone
from django.db import transaction

from apps.rides.models import Ride, BargainOffer
from apps.notifications.services.notification_service import NotificationService


class BargainHandler:
    """
    Service for handling bargain negotiations between riders and drivers.
    """
    
    # Bargain configuration
    MAX_BARGAIN_ROUNDS = 5
    OFFER_EXPIRY_MINUTES = 10
    MIN_OFFER_PERCENTAGE = 0.5  # 50% of estimated fare
    MAX_OFFER_PERCENTAGE = 2.0  # 200% of estimated fare
    
    @classmethod
    def initiate_bargaining(cls, ride: Ride) -> Tuple[bool, str]:
        """
        Initiate bargaining process for a ride.
        """
        if ride.status != Ride.RideStatus.SEARCHING:
            return False, "Ride must be in searching status to start bargaining"
        
        # Update ride status to bargaining
        ride.status = Ride.RideStatus.BARGAINING
        ride.save()
        
        # Create history entry
        from apps.rides.models import RideHistory
        RideHistory.objects.create(
            ride=ride,
            event_type=RideHistory.EventType.BARGAIN,
            description="Bargaining initiated",
            metadata={'action': 'bargaining_started'}
        )
        
        return True, "Bargaining initiated successfully"
    
    @classmethod
    def make_offer(cls, ride: Ride, offered_by, amount: Decimal, 
                  offer_type: str, notes: str = "") -> Tuple[bool, str, Optional[BargainOffer]]:
        """
        Make a bargain offer.
        """
        # Validate offer
        is_valid, error_message = cls._validate_offer(ride, offered_by, amount, offer_type)
        if not is_valid:
            return False, error_message, None
        
        # Check if user has pending offers
        pending_offers = BargainOffer.objects.filter(
            ride=ride,
            offered_by=offered_by,
            status=BargainOffer.OfferStatus.PENDING
        )
        
        if pending_offers.exists():
            return False, "You already have a pending offer for this ride", None
        
        # Create the offer
        with transaction.atomic():
            offer = BargainOffer.objects.create(
                ride=ride,
                offered_by=offered_by,
                amount=amount,
                offer_type=offer_type,
                notes=notes,
                expiry_time=timezone.now() + timedelta(minutes=cls.OFFER_EXPIRY_MINUTES)
            )
            
            # Create history entry
            from apps.rides.models import RideHistory
            RideHistory.objects.create(
                ride=ride,
                event_type=RideHistory.EventType.BARGAIN,
                description=f"{offer_type.title()} made offer of ₦{amount}",
                metadata={
                    'offer_id': str(offer.id),
                    'amount': str(amount),
                    'offer_type': offer_type
                }
            )
            
            # Send notification to the other party
            cls._send_offer_notification(offer)
        
        return True, "Offer made successfully", offer
    
    @classmethod
    def accept_offer(cls, offer: BargainOffer, accepted_by) -> Tuple[bool, str]:
        """
        Accept a bargain offer.
        """
        # Validate acceptance
        is_valid, error_message = cls._validate_acceptance(offer, accepted_by)
        if not is_valid:
            return False, error_message
        
        with transaction.atomic():
            # Update offer status
            offer.status = BargainOffer.OfferStatus.ACCEPTED
            offer.accepted_at = timezone.now()
            offer.save()
            
            # Update ride with agreed fare
            ride = offer.ride
            ride.final_fare = offer.amount
            ride.status = Ride.RideStatus.ACCEPTED
            
            # Assign driver if offer was made by driver
            if offer.offer_type == BargainOffer.OfferType.DRIVER:
                ride.driver = offer.offered_by
                ride.status = Ride.RideStatus.DRIVER_ASSIGNED
            
            ride.save()
            
            # Reject all other pending offers for this ride
            BargainOffer.objects.filter(
                ride=ride,
                status=BargainOffer.OfferStatus.PENDING
            ).exclude(id=offer.id).update(
                status=BargainOffer.OfferStatus.REJECTED,
                rejected_at=timezone.now()
            )
            
            # Create history entry
            from apps.rides.models import RideHistory
            RideHistory.objects.create(
                ride=ride,
                event_type=RideHistory.EventType.BARGAIN,
                description=f"Offer of ₦{offer.amount} accepted",
                metadata={
                    'offer_id': str(offer.id),
                    'accepted_amount': str(offer.amount)
                }
            )
            
            # Send notifications
            cls._send_acceptance_notification(offer)
        
        return True, "Offer accepted successfully"
    
    @classmethod
    def reject_offer(cls, offer: BargainOffer, rejected_by, reason: str = "") -> Tuple[bool, str]:
        """
        Reject a bargain offer.
        """
        # Validate rejection
        is_valid, error_message = cls._validate_rejection(offer, rejected_by)
        if not is_valid:
            return False, error_message
        
        with transaction.atomic():
            # Update offer status
            offer.status = BargainOffer.OfferStatus.REJECTED
            offer.rejected_at = timezone.now()
            offer.rejection_reason = reason
            offer.save()
            
            # Create history entry
            from apps.rides.models import RideHistory
            RideHistory.objects.create(
                ride=offer.ride,
                event_type=RideHistory.EventType.BARGAIN,
                description=f"Offer of ₦{offer.amount} rejected",
                metadata={
                    'offer_id': str(offer.id),
                    'rejection_reason': reason
                }
            )
            
            # Send notification
            cls._send_rejection_notification(offer, reason)
        
        return True, "Offer rejected successfully"
    
    @classmethod
    def make_counter_offer(cls, original_offer: BargainOffer, counter_by,
                          counter_amount: Decimal, notes: str = "") -> Tuple[bool, str, Optional[BargainOffer]]:
        """
        Make a counter offer to an existing offer.
        """
        # Validate counter offer
        is_valid, error_message = cls._validate_counter_offer(
            original_offer, counter_by, counter_amount
        )
        if not is_valid:
            return False, error_message, None
        
        with transaction.atomic():
            # Reject the original offer
            original_offer.status = BargainOffer.OfferStatus.REJECTED
            original_offer.rejected_at = timezone.now()
            original_offer.rejection_reason = "Counter offer made"
            original_offer.save()
            
            # Determine counter offer type
            counter_type = (BargainOffer.OfferType.RIDER 
                          if original_offer.offer_type == BargainOffer.OfferType.DRIVER 
                          else BargainOffer.OfferType.DRIVER)
            
            # Create counter offer
            counter_offer = BargainOffer.objects.create(
                ride=original_offer.ride,
                offered_by=counter_by,
                amount=counter_amount,
                offer_type=counter_type,
                notes=notes,
                counter_offer=original_offer,
                expiry_time=timezone.now() + timedelta(minutes=cls.OFFER_EXPIRY_MINUTES)
            )
            
            # Create history entry
            from apps.rides.models import RideHistory
            RideHistory.objects.create(
                ride=original_offer.ride,
                event_type=RideHistory.EventType.BARGAIN,
                description=f"Counter offer of ₦{counter_amount} made",
                metadata={
                    'original_offer_id': str(original_offer.id),
                    'counter_offer_id': str(counter_offer.id),
                    'counter_amount': str(counter_amount)
                }
            )
            
            # Send notification
            cls._send_counter_offer_notification(counter_offer)
        
        return True, "Counter offer made successfully", counter_offer
    
    @classmethod
    def expire_offers(cls) -> int:
        """
        Expire all offers that have passed their expiry time.
        """
        now = timezone.now()
        
        expired_offers = BargainOffer.objects.filter(
            status=BargainOffer.OfferStatus.PENDING,
            expiry_time__lt=now
        )
        
        count = expired_offers.count()
        
        expired_offers.update(
            status=BargainOffer.OfferStatus.EXPIRED,
            rejected_at=now
        )
        
        return count
    
    @classmethod
    def get_bargain_summary(cls, ride: Ride) -> dict:
        """
        Get summary of bargaining activity for a ride.
        """
        offers = BargainOffer.objects.filter(ride=ride).order_by('created_at')
        
        summary = {
            'total_offers': offers.count(),
            'pending_offers': offers.filter(status=BargainOffer.OfferStatus.PENDING).count(),
            'accepted_offers': offers.filter(status=BargainOffer.OfferStatus.ACCEPTED).count(),
            'rejected_offers': offers.filter(status=BargainOffer.OfferStatus.REJECTED).count(),
            'expired_offers': offers.filter(status=BargainOffer.OfferStatus.EXPIRED).count(),
            'rider_offers': offers.filter(offer_type=BargainOffer.OfferType.RIDER).count(),
            'driver_offers': offers.filter(offer_type=BargainOffer.OfferType.DRIVER).count(),
            'bargain_rounds': cls._count_bargain_rounds(offers),
            'final_agreed_amount': ride.final_fare,
            'original_estimate': ride.estimated_fare
        }
        
        return summary
    
    @classmethod
    def _validate_offer(cls, ride: Ride, offered_by, amount: Decimal, offer_type: str) -> Tuple[bool, str]:
        """
        Validate a bargain offer.
        """
        # Check ride status
        if ride.status != Ride.RideStatus.BARGAINING:
            return False, "Ride is not in bargaining status"
        
        # Check user involvement
        if offer_type == BargainOffer.OfferType.RIDER and offered_by != ride.rider:
            return False, "Only the rider can make rider offers"
        
        if offer_type == BargainOffer.OfferType.DRIVER and not offered_by.is_driver:
            return False, "Only drivers can make driver offers"
        
        # Check amount limits
        min_amount = ride.estimated_fare * Decimal(str(cls.MIN_OFFER_PERCENTAGE))
        max_amount = ride.estimated_fare * Decimal(str(cls.MAX_OFFER_PERCENTAGE))
        
        if amount < min_amount:
            return False, f"Offer amount too low (minimum: ₦{min_amount})"
        
        if amount > max_amount:
            return False, f"Offer amount too high (maximum: ₦{max_amount})"
        
        # Check bargain rounds limit
        offer_count = BargainOffer.objects.filter(ride=ride).count()
        if offer_count >= cls.MAX_BARGAIN_ROUNDS:
            return False, "Maximum bargain rounds exceeded"
        
        return True, "Valid offer"
    
    @classmethod
    def _validate_acceptance(cls, offer: BargainOffer, accepted_by) -> Tuple[bool, str]:
        """
        Validate offer acceptance.
        """
        # Check offer status
        if offer.status != BargainOffer.OfferStatus.PENDING:
            return False, "Offer is not pending"
        
        # Check expiry
        if timezone.now() > offer.expiry_time:
            return False, "Offer has expired"
        
        # Check user authorization
        if offer.offer_type == BargainOffer.OfferType.RIDER:
            # Driver accepting rider's offer
            if not accepted_by.is_driver:
                return False, "Only drivers can accept rider offers"
        else:
            # Rider accepting driver's offer
            if accepted_by != offer.ride.rider:
                return False, "Only the rider can accept driver offers"
        
        return True, "Valid acceptance"
    
    @classmethod
    def _validate_rejection(cls, offer: BargainOffer, rejected_by) -> Tuple[bool, str]:
        """
        Validate offer rejection.
        """
        # Check offer status
        if offer.status != BargainOffer.OfferStatus.PENDING:
            return False, "Offer is not pending"
        
        # Check user authorization (same as acceptance)
        if offer.offer_type == BargainOffer.OfferType.RIDER:
            if not rejected_by.is_driver:
                return False, "Only drivers can reject rider offers"
        else:
            if rejected_by != offer.ride.rider:
                return False, "Only the rider can reject driver offers"
        
        return True, "Valid rejection"
    
    @classmethod
    def _validate_counter_offer(cls, original_offer: BargainOffer, counter_by,
                              counter_amount: Decimal) -> Tuple[bool, str]:
        """
        Validate counter offer.
        """
        # Check original offer status
        if original_offer.status != BargainOffer.OfferStatus.PENDING:
            return False, "Original offer is not pending"
        
        # Check expiry
        if timezone.now() > original_offer.expiry_time:
            return False, "Original offer has expired"
        
        # Check user authorization
        if original_offer.offer_type == BargainOffer.OfferType.RIDER:
            if not counter_by.is_driver:
                return False, "Only drivers can counter rider offers"
        else:
            if counter_by != original_offer.ride.rider:
                return False, "Only the rider can counter driver offers"
        
        # Check amount limits
        ride = original_offer.ride
        min_amount = ride.estimated_fare * Decimal(str(cls.MIN_OFFER_PERCENTAGE))
        max_amount = ride.estimated_fare * Decimal(str(cls.MAX_OFFER_PERCENTAGE))
        
        if counter_amount < min_amount or counter_amount > max_amount:
            return False, f"Counter offer amount must be between ₦{min_amount} and ₦{max_amount}"
        
        return True, "Valid counter offer"
    
    @classmethod
    def _count_bargain_rounds(cls, offers) -> int:
        """
        Count the number of bargain rounds.
        """
        # A round consists of offers from both parties
        rider_offers = offers.filter(offer_type=BargainOffer.OfferType.RIDER).count()
        driver_offers = offers.filter(offer_type=BargainOffer.OfferType.DRIVER).count()
        
        return max(rider_offers, driver_offers)
    
    @classmethod
    def _send_offer_notification(cls, offer: BargainOffer):
        """
        Send notification about new offer.
        """
        if offer.offer_type == BargainOffer.OfferType.RIDER:
            # Notify available drivers
            NotificationService.send_bargain_offer_notification(
                offer, notification_type='new_rider_offer'
            )
        else:
            # Notify the rider
            NotificationService.send_bargain_offer_notification(
                offer, notification_type='new_driver_offer'
            )
    
    @classmethod
    def _send_acceptance_notification(cls, offer: BargainOffer):
        """
        Send notification about offer acceptance.
        """
        NotificationService.send_bargain_offer_notification(
            offer, notification_type='offer_accepted'
        )
    
    @classmethod
    def _send_rejection_notification(cls, offer: BargainOffer, reason: str):
        """
        Send notification about offer rejection.
        """
        NotificationService.send_bargain_offer_notification(
            offer, notification_type='offer_rejected', extra_data={'reason': reason}
        )
    
    @classmethod
    def _send_counter_offer_notification(cls, counter_offer: BargainOffer):
        """
        Send notification about counter offer.
        """
        NotificationService.send_bargain_offer_notification(
            counter_offer, notification_type='counter_offer'
        )
