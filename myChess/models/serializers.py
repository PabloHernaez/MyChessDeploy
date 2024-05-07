from rest_framework import serializers
from .models import ChessGame, ChessMove


class ChessGameSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChessGame
        fields = ['id', 'status', 'whitePlayer', 'blackPlayer']


class ChessMoveSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChessMove
        fields = ['id', 'game', 'player', 'move_from', 'move_to', 'promotion']
