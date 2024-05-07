from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import ChessGame
from .serializers import ChessGameSerializer, serializers 
# Create your views here.

@api_view(['GET'])
def getData(request):
    games = ChessGame.objects.all()
    serializer = ChessGameSerializer(games, many=True)
    return Response(serializer.data)
