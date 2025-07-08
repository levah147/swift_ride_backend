"""
Verification service for user document verification.
"""

from typing import Dict, Any, Optional
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.storage import default_storage
import logging
import requests
import json

from ..models import DriverProfile

User = get_user_model()
logger = logging.getLogger(__name__)


class VerificationService:
    """
    Service class for user verification operations.
    """
    
    def verify_user_documents(self, user) -> Dict[str, Any]:
        """
        Verify user documents (NIN, BVN, Driver's License).
        """
        try:
            verification_results = {
                'user_id': user.id,
                'overall_status': 'pending',
                'verifications': {},
                'timestamp': timezone.now().isoformat()
            }
            
            # Verify NIN if provided
            if user.nin:
                nin_result = self._verify_nin(user.nin)
                verification_results['verifications']['nin'] = nin_result
            
            # Verify BVN if provided
            if user.bvn:
                bvn_result = self._verify_bvn(user.bvn)
                verification_results['verifications']['bvn'] = bvn_result
            
            # Verify driver's license if user is a driver
            if user.user_type == 'driver':
                try:
                    driver_profile = DriverProfile.objects.get(user=user)
                    if driver_profile.license_number:
                        license_result = self._verify_drivers_license(
                            driver_profile.license_number,
                            driver_profile.license_expiry
                        )
                        verification_results['verifications']['drivers_license'] = license_result
                except DriverProfile.DoesNotExist:
                    verification_results['verifications']['drivers_license'] = {
                        'status': 'failed',
                        'message': 'Driver profile not found'
                    }
            
            # Determine overall status
            all_verifications = list(verification_results['verifications'].values())
            if all_verifications:
                if all(v['status'] == 'verified' for v in all_verifications):
                    verification_results['overall_status'] = 'verified'
                    user.is_verified = True
                    user.verified_at = timezone.now()
                    user.save()
                elif any(v['status'] == 'failed' for v in all_verifications):
                    verification_results['overall_status'] = 'failed'
                else:
                    verification_results['overall_status'] = 'pending'
            
            return {
                'success': True,
                'data': verification_results
            }
            
        except Exception as e:
            logger.error(f"Error verifying documents for user {user.id}: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def _verify_nin(self, nin: str) -> Dict[str, Any]:
        """
        Verify National Identification Number (NIN).
        """
        try:
            # In a real implementation, this would call the NIMC API
            # For now, we'll simulate the verification
            
            if len(nin) != 11 or not nin.isdigit():
                return {
                    'status': 'failed',
                    'message': 'Invalid NIN format',
                    'verified_at': timezone.now().isoformat()
                }
            
            # Simulate API call delay and response
            # In production, replace with actual NIMC API call
            verification_result = self._simulate_nin_verification(nin)
            
            return {
                'status': verification_result['status'],
                'message': verification_result['message'],
                'data': verification_result.get('data', {}),
                'verified_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error verifying NIN {nin}: {str(e)}")
            return {
                'status': 'failed',
                'message': f'Verification error: {str(e)}',
                'verified_at': timezone.now().isoformat()
            }
    
    def _verify_bvn(self, bvn: str) -> Dict[str, Any]:
        """
        Verify Bank Verification Number (BVN).
        """
        try:
            if len(bvn) != 11 or not bvn.isdigit():
                return {
                    'status': 'failed',
                    'message': 'Invalid BVN format',
                    'verified_at': timezone.now().isoformat()
                }
            
            # Simulate BVN verification
            # In production, replace with actual bank API call
            verification_result = self._simulate_bvn_verification(bvn)
            
            return {
                'status': verification_result['status'],
                'message': verification_result['message'],
                'data': verification_result.get('data', {}),
                'verified_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error verifying BVN {bvn}: {str(e)}")
            return {
                'status': 'failed',
                'message': f'Verification error: {str(e)}',
                'verified_at': timezone.now().isoformat()
            }
    
    def _verify_drivers_license(self, license_number: str, license_expiry) -> Dict[str, Any]:
        """
        Verify driver's license.
        """
        try:
            # Check license format
            import re
            pattern = r'^[A-Z]{3}-\d{8}-[A-Z]{2}$'
            if not re.match(pattern, license_number.upper()):
                return {
                    'status': 'failed',
                    'message': 'Invalid license number format',
                    'verified_at': timezone.now().isoformat()
                }
            
            # Check if license is expired
            if license_expiry <= timezone.now().date():
                return {
                    'status': 'failed',
                    'message': 'Driver license has expired',
                    'verified_at': timezone.now().isoformat()
                }
            
            # Simulate license verification
            # In production, replace with actual FRSC API call
            verification_result = self._simulate_license_verification(license_number)
            
            return {
                'status': verification_result['status'],
                'message': verification_result['message'],
                'data': verification_result.get('data', {}),
                'verified_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error verifying license {license_number}: {str(e)}")
            return {
                'status': 'failed',
                'message': f'Verification error: {str(e)}',
                'verified_at': timezone.now().isoformat()
            }
    
    def _simulate_nin_verification(self, nin: str) -> Dict[str, Any]:
        """
        Simulate NIN verification (replace with actual API call).
        """
        # Simulate different scenarios based on NIN
        if nin.endswith('000'):
            return {
                'status': 'failed',
                'message': 'NIN not found in database'
            }
        elif nin.endswith('999'):
            return {
                'status': 'pending',
                'message': 'Verification in progress'
            }
        else:
            return {
                'status': 'verified',
                'message': 'NIN verified successfully',
                'data': {
                    'first_name': 'John',
                    'last_name': 'Doe',
                    'date_of_birth': '1990-01-01',
                    'gender': 'Male'
                }
            }
    
    def _simulate_bvn_verification(self, bvn: str) -> Dict[str, Any]:
        """
        Simulate BVN verification (replace with actual API call).
        """
        # Simulate different scenarios based on BVN
        if bvn.endswith('000'):
            return {
                'status': 'failed',
                'message': 'BVN not found'
            }
        elif bvn.endswith('999'):
            return {
                'status': 'pending',
                'message': 'BVN verification in progress'
            }
        else:
            return {
                'status': 'verified',
                'message': 'BVN verified successfully',
                'data': {
                    'first_name': 'John',
                    'last_name': 'Doe',
                    'phone_number': '+2348012345678'
                }
            }
    
    def _simulate_license_verification(self, license_number: str) -> Dict[str, Any]:
        """
        Simulate driver's license verification (replace with actual API call).
        """
        # Simulate different scenarios
        if 'TEST' in license_number:
            return {
                'status': 'failed',
                'message': 'Invalid license number'
            }
        else:
            return {
                'status': 'verified',
                'message': 'Driver license verified successfully',
                'data': {
                    'license_class': 'C',
                    'issue_date': '2020-01-01',
                    'issuing_authority': 'Lagos State'
                }
            }
    
    def verify_phone_number(self, user, otp_code: str) -> Dict[str, Any]:
        """
        Verify phone number using OTP.
        """
        try:
            from apps.authentication.services.otp_service import OTPService
            
            otp_service = OTPService()
            verification_result = otp_service.verify_otp(user.phone_number, otp_code)
            
            if verification_result['success']:
                user.phone_verified = True
                user.phone_verified_at = timezone.now()
                user.save()
                
                return {
                    'success': True,
                    'message': 'Phone number verified successfully'
                }
            else:
                return {
                    'success': False,
                    'message': verification_result['message']
                }
                
        except Exception as e:
            logger.error(f"Error verifying phone for user {user.id}: {str(e)}")
            return {
                'success': False,
                'message': 'Phone verification failed'
            }
    
    def verify_email(self, user, verification_token: str) -> Dict[str, Any]:
        """
        Verify email address using verification token.
        """
        try:
            # In a real implementation, you would validate the token
            # For now, we'll simulate the verification
            
            if verification_token and len(verification_token) >= 32:
                user.email_verified = True
                user.email_verified_at = timezone.now()
                user.save()
                
                return {
                    'success': True,
                    'message': 'Email verified successfully'
                }
            else:
                return {
                    'success': False,
                    'message': 'Invalid verification token'
                }
                
        except Exception as e:
            logger.error(f"Error verifying email for user {user.id}: {str(e)}")
            return {
                'success': False,
                'message': 'Email verification failed'
            }
