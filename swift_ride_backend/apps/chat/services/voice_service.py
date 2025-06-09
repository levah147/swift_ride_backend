"""
Service for voice message processing.
"""

import os
import subprocess
from django.conf import settings


class VoiceService:
    """
    Service for processing voice messages.
    """
    
    @staticmethod
    def get_audio_duration(audio_file):
        """
        Get duration of audio file in seconds.
        """
        try:
            # Use ffprobe to get duration
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                audio_file.path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                return int(duration)
            else:
                print(f"Error getting audio duration: {result.stderr}")
                return 0
        
        except Exception as e:
            print(f"Error processing audio file: {e}")
            return 0
    
    @staticmethod
    def convert_audio_format(input_file, output_format='mp3'):
        """
        Convert audio file to specified format.
        """
        try:
            # Generate output filename
            base_name = os.path.splitext(input_file.name)[0]
            output_filename = f"{base_name}.{output_format}"
            output_path = os.path.join(settings.MEDIA_ROOT, 'converted_audio', output_filename)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Use ffmpeg to convert
            cmd = [
                'ffmpeg',
                '-i', input_file.path,
                '-acodec', 'libmp3lame' if output_format == 'mp3' else 'copy',
                '-y',  # Overwrite output file
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return output_path
            else:
                print(f"Error converting audio: {result.stderr}")
                return None
        
        except Exception as e:
            print(f"Error converting audio file: {e}")
            return None
    
    @staticmethod
    def transcribe_audio(audio_file):
        """
        Transcribe audio to text using speech recognition.
        """
        try:
            # This is a placeholder implementation
            # In production, you would use services like:
            # - Google Speech-to-Text
            # - AWS Transcribe
            # - Azure Speech Services
            # - OpenAI Whisper
            
            # For now, return a placeholder
            return "Audio transcription not implemented yet"
        
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None
    
    @staticmethod
    def generate_audio_waveform(audio_file):
        """
        Generate waveform data for audio visualization.
        """
        try:
            # This would generate waveform data for UI visualization
            # Implementation would depend on the frontend requirements
            
            # Placeholder implementation
            return {
                'peaks': [0.1, 0.3, 0.5, 0.7, 0.4, 0.2, 0.6, 0.8, 0.3, 0.1],
                'duration': VoiceService.get_audio_duration(audio_file)
            }
        
        except Exception as e:
            print(f"Error generating waveform: {e}")
            return None
