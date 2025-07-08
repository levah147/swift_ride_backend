"""
Service for processing voice messages and audio files.
"""

import os
import subprocess
import tempfile
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


class VoiceProcessor:
    """
    Service for processing voice messages.
    """
    
    @staticmethod
    def process_voice_message(audio_file, target_format='mp3', target_bitrate='128k'):
        """
        Process and optimize voice message.
        """
        try:
            # Create temporary files
            with tempfile.NamedTemporaryFile(suffix='.tmp') as temp_input:
                with tempfile.NamedTemporaryFile(suffix=f'.{target_format}') as temp_output:
                    # Write input file
                    for chunk in audio_file.chunks():
                        temp_input.write(chunk)
                    temp_input.flush()
                    
                    # Process with ffmpeg
                    cmd = [
                        'ffmpeg',
                        '-i', temp_input.name,
                        '-acodec', 'libmp3lame' if target_format == 'mp3' else 'copy',
                        '-ab', target_bitrate,
                        '-ar', '44100',  # Sample rate
                        '-ac', '1',      # Mono
                        '-y',            # Overwrite output
                        temp_output.name
                    ]
                    
                    result = subprocess.run(
                        cmd, 
                        capture_output=True, 
                        text=True,
                        timeout=60  # 1 minute timeout
                    )
                    
                    if result.returncode == 0:
                        # Read processed file
                        temp_output.seek(0)
                        processed_content = temp_output.read()
                        
                        # Create Django file object
                        processed_file = ContentFile(
                            processed_content,
                            name=f"processed_{audio_file.name}"
                        )
                        
                        return processed_file
                    else:
                        print(f"FFmpeg error: {result.stderr}")
                        return audio_file
        
        except Exception as e:
            print(f"Error processing voice message: {e}")
            return audio_file
    
    @staticmethod
    def extract_audio_metadata(audio_file):
        """
        Extract metadata from audio file.
        """
        try:
            with tempfile.NamedTemporaryFile() as temp_file:
                # Write audio file to temp
                for chunk in audio_file.chunks():
                    temp_file.write(chunk)
                temp_file.flush()
                
                # Use ffprobe to get metadata
                cmd = [
                    'ffprobe',
                    '-v', 'quiet',
                    '-print_format', 'json',
                    '-show_format',
                    '-show_streams',
                    temp_file.name
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    import json
                    metadata = json.loads(result.stdout)
                    
                    # Extract relevant information
                    format_info = metadata.get('format', {})
                    streams = metadata.get('streams', [])
                    
                    audio_stream = None
                    for stream in streams:
                        if stream.get('codec_type') == 'audio':
                            audio_stream = stream
                            break
                    
                    return {
                        'duration': float(format_info.get('duration', 0)),
                        'size': int(format_info.get('size', 0)),
                        'bitrate': int(format_info.get('bit_rate', 0)),
                        'format': format_info.get('format_name', ''),
                        'codec': audio_stream.get('codec_name', '') if audio_stream else '',
                        'sample_rate': int(audio_stream.get('sample_rate', 0)) if audio_stream else 0,
                        'channels': int(audio_stream.get('channels', 0)) if audio_stream else 0,
                    }
                else:
                    print(f"FFprobe error: {result.stderr}")
                    return {}
        
        except Exception as e:
            print(f"Error extracting audio metadata: {e}")
            return {}
    
    @staticmethod
    def generate_waveform_data(audio_file, width=200, height=50):
        """
        Generate waveform data for audio visualization.
        """
        try:
            with tempfile.NamedTemporaryFile() as temp_input:
                with tempfile.NamedTemporaryFile(suffix='.txt') as temp_output:
                    # Write input file
                    for chunk in audio_file.chunks():
                        temp_input.write(chunk)
                    temp_input.flush()
                    
                    # Generate waveform data using ffmpeg
                    cmd = [
                        'ffmpeg',
                        '-i', temp_input.name,
                        '-filter_complex', f'[0:a]aformat=channel_layouts=mono,compand,showwavespic=s={width}x{height}:colors=blue[fg];color=s={width}x{height}:color=white[bg];[bg][fg]overlay=format=auto',
                        '-frames:v', '1',
                        '-y',
                        temp_output.name.replace('.txt', '.png')
                    ]
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode == 0:
                        # Read the generated waveform image
                        waveform_path = temp_output.name.replace('.txt', '.png')
                        if os.path.exists(waveform_path):
                            with open(waveform_path, 'rb') as wf:
                                waveform_data = wf.read()
                            
                            # Clean up
                            os.remove(waveform_path)
                            
                            return waveform_data
                    
                    # Fallback: generate simple waveform data
                    return VoiceProcessor._generate_simple_waveform(width)
        
        except Exception as e:
            print(f"Error generating waveform: {e}")
            return VoiceProcessor._generate_simple_waveform(width)
    
    @staticmethod
    def _generate_simple_waveform(width=200):
        """
        Generate simple waveform data as fallback.
        """
        import random
        
        # Generate random waveform data
        waveform = []
        for i in range(width):
            # Create a wave-like pattern with some randomness
            base_wave = abs(50 * (1 + 0.5 * (i / width - 0.5)) * 
                           (0.5 + 0.5 * (i % 20 / 20)))
            noise = random.uniform(-10, 10)
            amplitude = max(0, min(100, base_wave + noise))
            waveform.append(amplitude)
        
        return waveform
    
    @staticmethod
    def transcribe_audio(audio_file, language='en'):
        """
        Transcribe audio to text using speech recognition.
        """
        try:
            # This is a placeholder for actual speech-to-text implementation
            # In production, you would integrate with services like:
            # - Google Speech-to-Text
            # - AWS Transcribe
            # - Azure Speech Services
            # - OpenAI Whisper
            
            # For now, return a placeholder
            return {
                'text': '[Audio transcription not implemented]',
                'confidence': 0.0,
                'language': language,
                'words': [],
                'duration': 0.0
            }
        
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None
    
    @staticmethod
    def detect_audio_language(audio_file):
        """
        Detect the language of spoken audio.
        """
        try:
            # Placeholder for language detection
            # Would integrate with language detection services
            return 'en'  # Default to English
        
        except Exception as e:
            print(f"Error detecting audio language: {e}")
            return 'en'
    
    @staticmethod
    def enhance_audio_quality(audio_file):
        """
        Enhance audio quality using noise reduction and normalization.
        """
        try:
            with tempfile.NamedTemporaryFile(suffix='.tmp') as temp_input:
                with tempfile.NamedTemporaryFile(suffix='.mp3') as temp_output:
                    # Write input file
                    for chunk in audio_file.chunks():
                        temp_input.write(chunk)
                    temp_input.flush()
                    
                    # Apply audio enhancements
                    cmd = [
                        'ffmpeg',
                        '-i', temp_input.name,
                        '-af', 'highpass=f=80,lowpass=f=8000,dynaudnorm=f=500:g=31',
                        '-acodec', 'libmp3lame',
                        '-ab', '128k',
                        '-ar', '44100',
                        '-y',
                        temp_output.name
                    ]
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    
                    if result.returncode == 0:
                        temp_output.seek(0)
                        enhanced_content = temp_output.read()
                        
                        enhanced_file = ContentFile(
                            enhanced_content,
                            name=f"enhanced_{audio_file.name}"
                        )
                        
                        return enhanced_file
                    else:
                        print(f"Audio enhancement error: {result.stderr}")
                        return audio_file
        
        except Exception as e:
            print(f"Error enhancing audio: {e}")
            return audio_file
    
    @staticmethod
    def convert_to_format(audio_file, target_format='mp3'):
        """
        Convert audio file to specified format.
        """
        try:
            with tempfile.NamedTemporaryFile(suffix='.tmp') as temp_input:
                with tempfile.NamedTemporaryFile(suffix=f'.{target_format}') as temp_output:
                    # Write input file
                    for chunk in audio_file.chunks():
                        temp_input.write(chunk)
                    temp_input.flush()
                    
                    # Convert format
                    codec_map = {
                        'mp3': 'libmp3lame',
                        'ogg': 'libvorbis',
                        'wav': 'pcm_s16le',
                        'm4a': 'aac'
                    }
                    
                    codec = codec_map.get(target_format, 'libmp3lame')
                    
                    cmd = [
                        'ffmpeg',
                        '-i', temp_input.name,
                        '-acodec', codec,
                        '-y',
                        temp_output.name
                    ]
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    
                    if result.returncode == 0:
                        temp_output.seek(0)
                        converted_content = temp_output.read()
                        
                        converted_file = ContentFile(
                            converted_content,
                            name=f"converted_{audio_file.name}"
                        )
                        
                        return converted_file
                    else:
                        print(f"Format conversion error: {result.stderr}")
                        return audio_file
        
        except Exception as e:
            print(f"Error converting audio format: {e}")
            return audio_file
