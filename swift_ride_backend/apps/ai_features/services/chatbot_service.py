from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import get_user_model
from typing import Dict, List, Any, Optional
import logging
import json
import uuid
import re
from datetime import timedelta

from ..models import ChatbotConversation, ChatbotMessage, AIModel
from apps.rides.models import Ride
from apps.payments.models import Payment
from apps.users.models import UserProfile

User = get_user_model()
logger = logging.getLogger(__name__)


class ChatbotService:
    """Service for AI-powered chatbot interactions"""
    
    @staticmethod
    def start_conversation(user_id: str, initial_message: str = None) -> Dict[str, Any]:
        """Start a new chatbot conversation"""
        try:
            user = User.objects.get(id=user_id)
            
            # Get the latest AI model for chatbot
            ai_model = AIModel.objects.filter(
                model_type=AIModel.AIModelType.NLP,
                status=AIModel.AIModelStatus.DEPLOYED,
                is_active=True
            ).first()
            
            if not ai_model:
                return {'success': False, 'error': 'No active chatbot model found'}
            
            # Create conversation
            conversation = ChatbotConversation.objects.create(
                user=user,
                ai_model=ai_model,
                conversation_id=f"chat_{uuid.uuid4().hex[:10]}",
                language=user.preferred_language if hasattr(user, 'preferred_language') else 'en',
                context_data={
                    'user_name': user.get_full_name(),
                    'user_type': 'driver' if hasattr(user, 'driver_profile') else 'rider',
                    'account_age_days': (timezone.now() - user.date_joined).days
                }
            )
            
            # Add system message
            system_message = ChatbotMessage.objects.create(
                conversation=conversation,
                message_type=ChatbotMessage.MessageType.SYSTEM,
                content=ChatbotService._generate_system_prompt(user)
            )
            
            # Process initial message if provided
            response = None
            if initial_message:
                response = ChatbotService.process_message(
                    conversation.id, initial_message
                )
            
            return {
                'success': True,
                'conversation_id': str(conversation.id),
                'conversation_code': conversation.conversation_id,
                'initial_response': response['response'] if response else None
            }
            
        except Exception as e:
            logger.error(f"Error starting conversation: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def process_message(conversation_id: str, message_content: str) -> Dict[str, Any]:
        """Process a user message and generate a response"""
        try:
            conversation = ChatbotConversation.objects.get(id=conversation_id)
            
            # Check if conversation is active
            if conversation.status != ChatbotConversation.ConversationStatus.ACTIVE:
                return {
                    'success': False,
                    'error': f"Conversation is {conversation.status}, not active"
                }
            
            start_time = timezone.now()
            
            # Create user message
            user_message = ChatbotMessage.objects.create(
                conversation=conversation,
                message_type=ChatbotMessage.MessageType.USER,
                content=message_content
            )
            
            # Analyze intent
            intent, confidence, entities = ChatbotService._analyze_intent(message_content)
            
            # Update user message with intent data
            user_message.intent_detected = intent
            user_message.confidence_score = confidence
            user_message.entities_extracted = entities
            user_message.save()
            
            # Generate response based on intent
            response_content = ChatbotService._generate_response(
                conversation, intent, entities, message_content
            )
            
            # Create bot response
            bot_message = ChatbotMessage.objects.create(
                conversation=conversation,
                message_type=ChatbotMessage.MessageType.BOT,
                content=response_content,
                intent_detected=intent,
                confidence_score=confidence,
                entities_extracted=entities,
                response_time=timezone.now() - start_time,
                model_used=conversation.ai_model.name
            )
            
            # Update conversation metrics
            conversation.message_count += 2  # User message + bot response
            
            # Check if escalation is needed
            if ChatbotService._should_escalate(conversation, intent, confidence, message_content):
                conversation.status = ChatbotConversation.ConversationStatus.ESCALATED
                conversation.escalated_to_human = True
                conversation.escalation_reason = "Complex issue requiring human assistance"
            
            conversation.save()
            
            return {
                'success': True,
                'conversation_id': str(conversation.id),
                'response': response_content,
                'intent': intent,
                'confidence': float(confidence) if confidence else None,
                'entities': entities,
                'escalated': conversation.escalated_to_human
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def end_conversation(conversation_id: str, satisfaction_score: int = None) -> Dict[str, Any]:
        """End a chatbot conversation"""
        try:
            conversation = ChatbotConversation.objects.get(id=conversation_id)
            
            # Update conversation status
            conversation.status = ChatbotConversation.ConversationStatus.RESOLVED
            
            # Record satisfaction score if provided
            if satisfaction_score is not None:
                conversation.satisfaction_score = satisfaction_score
            
            # Calculate resolution time
            conversation.resolution_time = timezone.now() - conversation.created_at
            
            conversation.save()
            
            # Add closing system message
            ChatbotMessage.objects.create(
                conversation=conversation,
                message_type=ChatbotMessage.MessageType.SYSTEM,
                content="Conversation ended. Thank you for using our support!"
            )
            
            return {
                'success': True,
                'conversation_id': str(conversation.id),
                'status': conversation.status,
                'satisfaction_score': satisfaction_score,
                'resolution_time_minutes': conversation.resolution_time.total_seconds() / 60
            }
            
        except Exception as e:
            logger.error(f"Error ending conversation: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def escalate_to_human(conversation_id: str, reason: str = None) -> Dict[str, Any]:
        """Escalate conversation to human agent"""
        try:
            conversation = ChatbotConversation.objects.get(id=conversation_id)
            
            # Update conversation status
            conversation.status = ChatbotConversation.ConversationStatus.ESCALATED
            conversation.escalated_to_human = True
            conversation.escalation_reason = reason or "User requested human assistance"
            conversation.save()
            
            # Add escalation message
            ChatbotMessage.objects.create(
                conversation=conversation,
                message_type=ChatbotMessage.MessageType.SYSTEM,
                content="Your conversation has been escalated to a human agent. Please wait for assistance."
            )
            
            # In a real implementation, this would notify human agents
            # For now, we'll just log it
            logger.info(f"Conversation {conversation.conversation_id} escalated to human")
            
            return {
                'success': True,
                'conversation_id': str(conversation.id),
                'status': conversation.status,
                'escalation_reason': conversation.escalation_reason
            }
            
        except Exception as e:
            logger.error(f"Error escalating conversation: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _generate_system_prompt(user: User) -> str:
        """Generate system prompt for the chatbot"""
        user_type = 'driver' if hasattr(user, 'driver_profile') else 'rider'
        
        return f"""
        You are Swift Ride's AI assistant. You're helping {user.get_full_name()}, a {user_type}.
        
        You can help with:
        - Ride booking and management
        - Payment and billing questions
        - Account settings and profile
        - General support and troubleshooting
        - Platform features and how-to guides
        
        Be friendly, helpful, and concise. If you can't help with something, offer to escalate to a human agent.
        """
    
    @staticmethod
    def _analyze_intent(message: str) -> tuple:
        """Analyze user message intent"""
        # Simple rule-based intent detection
        # In a real implementation, this would use NLP models
        
        message_lower = message.lower()
        
        # Define intent patterns
        intent_patterns = {
            'book_ride': [
                'book', 'ride', 'trip', 'need a ride', 'want to go',
                'take me to', 'pickup', 'destination'
            ],
            'cancel_ride': [
                'cancel', 'cancel ride', 'cancel trip', 'cancel booking'
            ],
            'payment_issue': [
                'payment', 'charge', 'billing', 'refund', 'money',
                'card', 'credit card', 'debit', 'wallet'
            ],
            'account_help': [
                'account', 'profile', 'settings', 'password', 'login',
                'sign in', 'register', 'verification'
            ],
            'driver_issue': [
                'driver', 'late', 'no show', 'rude', 'complaint',
                'report driver', 'driver problem'
            ],
            'app_issue': [
                'app', 'bug', 'error', 'crash', 'not working',
                'technical', 'problem', 'issue'
            ],
            'pricing': [
                'price', 'cost', 'fare', 'expensive', 'cheap',
                'surge', 'pricing', 'estimate'
            ],
            'greeting': [
                'hello', 'hi', 'hey', 'good morning', 'good afternoon',
                'good evening', 'help', 'support'
            ],
            'goodbye': [
                'bye', 'goodbye', 'thanks', 'thank you', 'done',
                'that\'s all', 'no more questions'
            ]
        }
        
        # Extract entities (simple keyword extraction)
        entities = {}
        
        # Look for locations
        location_keywords = ['to', 'from', 'at', 'near']
        for keyword in location_keywords:
            if keyword in message_lower:
                # Simple entity extraction - in reality, would use NER
                words = message.split()
                if keyword in [w.lower() for w in words]:
                    idx = [w.lower() for w in words].index(keyword)
                    if idx + 1 < len(words):
                        entities['location'] = words[idx + 1]
        
        # Look for amounts
        amount_match = re.search(r'\$?(\d+(?:\.\d{2})?)', message)
        if amount_match:
            entities['amount'] = amount_match.group(1)
        
        # Look for ride IDs
        ride_id_match = re.search(r'ride\s*#?(\w+)', message_lower)
        if ride_id_match:
            entities['ride_id'] = ride_id_match.group(1)
        
        # Determine intent
        best_intent = 'general_inquiry'
        best_score = 0.0
        
        for intent, keywords in intent_patterns.items():
            score = sum(1 for keyword in keywords if keyword in message_lower)
            if score > best_score:
                best_score = score
                best_intent = intent
        
        # Calculate confidence
        confidence = min(0.95, best_score / 3.0) if best_score > 0 else 0.3
        
        return best_intent, confidence, entities
    
    @staticmethod
    def _generate_response(
        conversation: ChatbotConversation,
        intent: str,
        entities: Dict[str, Any],
        user_message: str
    ) -> str:
        """Generate response based on intent and context"""
        user = conversation.user
        
        # Response templates based on intent
        if intent == 'greeting':
            return f"Hello {user.first_name}! I'm here to help you with Swift Ride. What can I assist you with today?"
        
        elif intent == 'book_ride':
            if 'location' in entities:
                return f"I'd be happy to help you book a ride to {entities['location']}! Please use the main app to book your ride, as I can help with questions but can't complete bookings directly. Is there anything specific about booking you'd like to know?"
            else:
                return "I'd be happy to help you with booking a ride! Please use the main app to book your ride. I can answer questions about the booking process, pricing, or help you troubleshoot any issues. What would you like to know?"
        
        elif intent == 'cancel_ride':
            if 'ride_id' in entities:
                return f"I can help you with canceling ride {entities['ride_id']}. You can cancel your ride in the app by going to 'My Rides' and selecting the cancel option. Keep in mind that cancellation fees may apply depending on timing. Would you like me to explain the cancellation policy?"
            else:
                return "To cancel a ride, go to 'My Rides' in the app and select the ride you want to cancel. You can cancel up to a few minutes before pickup, though fees may apply. Do you need help finding a specific ride to cancel?"
        
        elif intent == 'payment_issue':
            if 'amount' in entities:
                return f"I see you're asking about a ${entities['amount']} charge. I can help explain charges and billing. For specific payment disputes or refunds, I may need to connect you with our billing team. Can you tell me more about the issue?"
            else:
                return "I can help with payment and billing questions! Common issues include understanding charges, updating payment methods, or requesting refunds. What specific payment issue are you experiencing?"
        
        elif intent == 'account_help':
            return "I can help with account-related questions! This includes updating your profile, changing settings, password issues, or verification problems. What specifically do you need help with regarding your account?"
        
        elif intent == 'driver_issue':
            return "I'm sorry to hear you had an issue with a driver. Your safety and satisfaction are important to us. You can report driver issues through the app after your ride, or I can help escalate this to our support team for immediate attention. Would you like me to connect you with a human agent?"
        
        elif intent == 'app_issue':
            return "I can help troubleshoot app issues! Common solutions include restarting the app, checking your internet connection, or updating to the latest version. What specific problem are you experiencing with the app?"
        
        elif intent == 'pricing':
            return "I can explain our pricing structure! Ride costs depend on distance, time, vehicle type, and demand. During busy times, surge pricing may apply. Would you like me to explain how pricing works or help you get a fare estimate?"
        
        elif intent == 'goodbye':
            return "You're welcome! Thanks for using Swift Ride. If you need any more help, just start a new chat. Have a great day!"
        
        else:  # general_inquiry
            return "I'm here to help! I can assist with ride booking questions, account issues, payments, app problems, and general support. What would you like help with today? If you need something I can't handle, I can connect you with a human agent."
    
    @staticmethod
    def _should_escalate(
        conversation: ChatbotConversation,
        intent: str,
        confidence: float,
        message: str
    ) -> bool:
        """Determine if conversation should be escalated to human"""
        # Escalate if confidence is very low
        if confidence and confidence < 0.3:
            return True
        
        # Escalate for certain intents that require human intervention
        escalation_intents = ['driver_issue', 'payment_issue']
        if intent in escalation_intents:
            return True
        
        # Escalate if user explicitly asks for human
        human_keywords = ['human', 'agent', 'person', 'representative', 'speak to someone']
        if any(keyword in message.lower() for keyword in human_keywords):
            return True
        
        # Escalate if conversation is getting long without resolution
        if conversation.message_count > 10:
            return True
        
        # Escalate if user seems frustrated
        frustration_keywords = ['frustrated', 'angry', 'terrible', 'awful', 'useless', 'stupid']
        if any(keyword in message.lower() for keyword in frustration_keywords):
            return True
        
        return False
