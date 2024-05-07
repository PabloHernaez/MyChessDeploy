from djoser.views import TokenCreateView
from djoser.conf import settings
from .models import ChessGame
from .serializers import ChessGameSerializer
from django.db.models import Q
from rest_framework import mixins, viewsets, status
from rest_framework.response import Response
import random


class MyTokenCreateView(TokenCreateView):

    def _action(self, serializer):
        response = super()._action(serializer)
        tokenString = response.data['auth_token']
        tokenObject = settings.TOKEN_MODEL.objects.get(key=tokenString)
        response.data['user_id'] = tokenObject.user.id
        response.data['rating'] = tokenObject.user.rating
        return response


class ChessGameViewSet(mixins.CreateModelMixin,
                       mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset = ChessGame.objects.all()
    serializer_class = ChessGameSerializer

    def create(self, request, *args, **kwargs):
        game = ChessGame.objects.exclude(
             Q(whitePlayer=self.request.user) | 
             Q(blackPlayer=self.request.user)).filter(
                 Q(whitePlayer=None) | Q(blackPlayer=None)
            ).first()
               
        if game:
            return self.update(request, game, *args, **kwargs)

        data = {'status': 'PENDING'}
        if random.choice([True, False]):
            data['whitePlayer'] = self.request.user.id
        else:             
            data['blackPlayer'] = self.request.user.id

        request._full_data = data
        return super().create(request, *args, **kwargs)

    def update(self, request, game, *args, **kwargs):
        if game.status.lower() == 'pending':

            response = {'status': 'ACTIVE'}
            
            if game.whitePlayer is None:
                response['whitePlayer'] = self.request.user.id
            else:
                response['blackPlayer'] = self.request.user.id
        
            request._full_data = response
            self.kwargs['pk'] = str(game.id)
            return super().update(request, *args, **kwargs)
        else:
            return Response(
                {'detail': 'Game is not pending'},
                status=status.HTTP_400_BAD_REQUEST
            )
