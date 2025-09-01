# trading_backend/core/views.py

import json
import os
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

@api_view(['GET'])
def trading_status_view(request):
    """
    API view to return the live status of the trading bot from a JSON file.
    """
    status_file_path = os.path.join(settings.BASE_DIR, 'trading_status.json')
    
    if not os.path.exists(status_file_path):
        return Response(
            {'error': 'Trading bot status file not found. The bot may not be running.'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        with open(status_file_path, 'r') as f:
            status_data = json.load(f)
        return Response(status_data)
    
    except json.JSONDecodeError:
        return Response(
            {'error': 'Error decoding status file. The file may be empty or corrupted.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        return Response(
            {'error': f'An unexpected error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )