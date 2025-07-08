"""
Base payment provider class.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional
from decimal import Decimal

from apps.payments.models import Payment, PaymentMethod, Refund


class BasePaymentProvider(ABC):
    """
    Abstract base class for payment providers.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
    
    @abstractmethod
    def process_payment(self, payment: Payment) -> Tuple[bool, str]:
        """
        Process a payment.
        
        Args:
            payment: Payment instance to process
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        pass
    
    @abstractmethod
    def process_refund(self, refund: Refund) -> Tuple[bool, str]:
        """
        Process a refund.
        
        Args:
            refund: Refund instance to process
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        pass
    
    @abstractmethod
    def create_payment_method(self, user, method_data: Dict[str, Any]) -> Tuple[Optional[PaymentMethod], str]:
        """
        Create a payment method.
        
        Args:
            user: User instance
            method_data: Payment method data
            
        Returns:
            Tuple of (payment_method: PaymentMethod or None, message: str)
        """
        pass
    
    @abstractmethod
    def verify_payment(self, provider_transaction_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify a payment with the provider.
        
        Args:
            provider_transaction_id: Provider's transaction ID
            
        Returns:
            Tuple of (success: bool, payment_data: dict)
        """
        pass
    
    @abstractmethod
    def handle_webhook(self, payload: Dict[str, Any], signature: str = None) -> Tuple[bool, str]:
        """
        Handle webhook from payment provider.
        
        Args:
            payload: Webhook payload
            signature: Webhook signature for verification
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        pass
    
    def validate_config(self) -> bool:
        """
        Validate provider configuration.
        
        Returns:
            bool: True if configuration is valid
        """
        required_keys = self.get_required_config_keys()
        return all(key in self.config for key in required_keys)
    
    @abstractmethod
    def get_required_config_keys(self) -> list:
        """
        Get list of required configuration keys.
        
        Returns:
            list: Required configuration keys
        """
        pass
    
    def get_supported_currencies(self) -> list:
        """
        Get list of supported currencies.
        
        Returns:
            list: Supported currency codes
        """
        return ['USD']
    
    def get_supported_payment_methods(self) -> list:
        """
        Get list of supported payment method types.
        
        Returns:
            list: Supported payment method types
        """
        return []
    
    def calculate_fees(self, amount: Decimal, currency: str = 'USD') -> Dict[str, Decimal]:
        """
        Calculate provider fees for a payment.
        
        Args:
            amount: Payment amount
            currency: Currency code
            
        Returns:
            dict: Fee breakdown
        """
        return {
            'processing_fee': Decimal('0.00'),
            'fixed_fee': Decimal('0.00'),
            'total_fee': Decimal('0.00')
        }
    
    def format_amount(self, amount: Decimal, currency: str = 'USD') -> int:
        """
        Format amount for provider API (usually in cents).
        
        Args:
            amount: Decimal amount
            currency: Currency code
            
        Returns:
            int: Amount in smallest currency unit
        """
        # Most providers expect amounts in cents
        return int(amount * 100)
    
    def parse_amount(self, amount: int, currency: str = 'USD') -> Decimal:
        """
        Parse amount from provider API (usually from cents).
        
        Args:
            amount: Amount in smallest currency unit
            currency: Currency code
            
        Returns:
            Decimal: Amount in standard currency unit
        """
        return Decimal(str(amount)) / 100
    
    def is_available(self) -> bool:
        """
        Check if provider is available and properly configured.
        
        Returns:
            bool: True if provider is available
        """
        return self.validate_config()
    
    def get_provider_name(self) -> str:
        """
        Get provider name.
        
        Returns:
            str: Provider name
        """
        return self.__class__.__name__.replace('Provider', '').lower()
    
    def log_transaction(self, transaction_type: str, data: Dict[str, Any]) -> None:
        """
        Log transaction for debugging and audit purposes.
        
        Args:
            transaction_type: Type of transaction
            data: Transaction data
        """
        import logging
        logger = logging.getLogger(f'payments.{self.get_provider_name()}')
        logger.info(f"{transaction_type}: {data}")
    
    def handle_error(self, error: Exception, context: str = None) -> str:
        """
        Handle and format provider errors.
        
        Args:
            error: Exception that occurred
            context: Additional context
            
        Returns:
            str: Formatted error message
        """
        import logging
        logger = logging.getLogger(f'payments.{self.get_provider_name()}')
        
        error_message = str(error)
        if context:
            error_message = f"{context}: {error_message}"
        
        logger.error(error_message)
        return error_message
