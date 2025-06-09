"""
Views for the rides app.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q

from apps.rides.models import Ride, BargainOffer, RideHistory
from apps.rides.serializers import (
    RideSerializer, RideCreateSerializer, BargainOfferSerializer,
    BargainOfferCreateSerializer, RideHistorySerializer
)
from apps.rides.services.ride_service import RideService
from apps.rides.services.bargain_service import BargainService
from apps.rides.services.ride_matching import RideMatchingService
from apps.users.models import CustomUser


class RideViewSet(viewsets.ModelViewSet):
    """
    ViewSet for rides.
    """
    serializer_class = RideSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Get queryset based on user type.
        """
        user = self.request.user
        
        # Filter rides based on user type
        if user.is_rider:
            return Ride.objects.filter(rider=user).order_by('-created_at')
        elif user.is_driver:
            return Ride.objects.filter(driver=user).order_by('-created_at')
        else:  # Admin or staff
            return Ride.objects.all().order_by('-created_at')
    
    def create(self, request):
        """
        Create a new ride request.
        """
        serializer = RideCreateSerializer(data=request.data)
        if serializer.is_valid():
            # Create ride
            data = serializer.validated_data
            
            # If preferred driver is specified, get the user
            preferred_driver = None
            if data.get('preferred_driver_id'):
                try:
                    preferred_driver = CustomUser.objects.get(
                        id=data['preferred_driver_id'],
                        user_type=CustomUser.UserType.DRIVER
                    )
                    # Remove from data to avoid duplicate key
                    del data['preferred_driver_id']
                except CustomUser.DoesNotExist:
                    return Response(
                        {'error': 'Preferred driver not found'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Add preferred driver to data if found
            if preferred_driver:
                data['preferred_driver'] = preferred_driver
                
            # Create ride
            ride, request = RideService.create_ride_request(request.user, data)
            
            return Response(
                RideSerializer(ride).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel a ride.
        """
        ride = self.get_object()
        reason = request.data.get('reason', '')
        
        success, message = RideService.cancel_ride(ride, request.user, reason)
        
        if success:
            return Response({'message': message})
        else:
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """
        Get ride history.
        """
        ride = self.get_object()
        history = RideHistory.objects.filter(ride=ride).order_by('-created_at')
        serializer = RideHistorySerializer(history, many=True)
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def bargain_offers(self, request, pk=None):
        """
        Get all bargain offers for a ride.
        """
        ride = self.get_object()
        
        # Check if user is involved in this ride
        if request.user != ride.rider and request.user != ride.driver and not request.user.is_staff:
            return Response(
                {'error': 'You do not have permission to view these offers'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Get offers
        offers = BargainOffer.objects.filter(ride=ride).order_by('-created_at')
        serializer = BargainOfferSerializer(offers, many=True)
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def make_offer(self, request, pk=None):
        """
        Make a bargain offer.
        """
        ride = self.get_object()
        
        # Check if user is involved in this ride
        if request.user != ride.rider and request.user != ride.driver:
            return Response(
                {'error': 'You do not have permission to make an offer for this ride'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Check if ride is in bargaining state
        if not ride.is_bargaining:
            return Response(
                {'error': 'Ride is not in bargaining state'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate offer data
        serializer = BargainOfferCreateSerializer(data=request.data)
        if serializer.is_valid():
            offer = BargainService.make_offer(
                ride,
                request.user,
                serializer.validated_data['amount'],
                serializer.validated_data.get('message', '')
            )
            
            return Response(
                BargainOfferSerializer(offer).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['get'])
    def nearby_drivers(self, request, pk=None):
        """
        Get nearby drivers for a ride.
        """
        ride = self.get_object()
        
        # Check if user is the rider or admin
        if request.user != ride.rider and not request.user.is_staff:
            return Response(
                {'error': 'You do not have permission to view nearby drivers'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Get distance parameter
        max_distance = float(request.query_params.get('max_distance', 5))
        
        # Find nearby drivers
        nearby_drivers = RideMatchingService.find_nearby_drivers(ride, max_distance)
        
        return Response({
            'count': len(nearby_drivers),
            'drivers': nearby_drivers
        })


class BargainOfferViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for bargain offers.
    """
    serializer_class = BargainOfferSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Get queryset based on user.
        """
        user = self.request.user
        
        # Filter offers based on user
        if user.is_staff:
            return BargainOffer.objects.all().order_by('-created_at')
        else:
            # Get offers where user is involved as rider or driver
            return BargainOffer.objects.filter(
                Q(ride__rider=user) | Q(ride__driver=user)
            ).order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """
        Accept a bargain offer.
        """
        offer = self.get_object()
        ride = offer.ride
        
        # Check if user can accept this offer
        if offer.offer_type == BargainOffer.OfferType.RIDER and request.user != ride.driver:
            return Response(
                {'error': 'Only the driver can accept a rider\'s offer'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        if offer.offer_type == BargainOffer.OfferType.DRIVER and request.user != ride.rider:
            return Response(
                {'error': 'Only the rider can accept a driver\'s offer'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Accept offer
        success, message = BargainService.accept_offer(offer)
        
        if success:
            return Response({'message': message})
        else:
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Reject a bargain offer.
        """
        offer = self.get_object()
        ride = offer.ride
        
        # Check if user can reject this offer
        if offer.offer_type == BargainOffer.OfferType.RIDER and request.user != ride.driver:
            return Response(
                {'error': 'Only the driver can reject a rider\'s offer'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        if offer.offer_type == BargainOffer.OfferType.DRIVER and request.user != ride.rider:
            return Response(
                {'error': 'Only the rider can reject a driver\'s offer'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Reject offer
        success, message = BargainService.reject_offer(offer)
        
        if success:
            return Response({'message': message})
        else:
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def counter(self, request, pk=None):
        """
        Make a counter offer.
        """
        original_offer = self.get_object()
        ride = original_offer.ride
        
        # Check if user can counter this offer
        if original_offer.offer_type == BargainOffer.OfferType.RIDER and request.user != ride.driver:
            return Response(
                {'error': 'Only the driver can counter a rider\'s offer'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        if original_offer.offer_type == BargainOffer.OfferType.DRIVER and request.user != ride.rider:
            return Response(
                {'error': 'Only the rider can counter a driver\'s offer'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate counter offer data
        serializer = BargainOfferCreateSerializer(data=request.data)
        if serializer.is_valid():
            counter, message = BargainService.counter_offer(
                original_offer,
                serializer.validated_data['amount'],
                serializer.validated_data.get('message', '')
            )
            
            if counter:
                return Response(
                    BargainOfferSerializer(counter).data,
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
