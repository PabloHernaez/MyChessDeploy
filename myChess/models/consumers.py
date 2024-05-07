
import json
from django.core.mail import message
from django.test.testcases import ValidationError
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import ChessMove, ChessGame, Player
from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework.authtoken.models import Token
from asgiref.sync import sync_to_async
from django.db.models import Q
import chess


#from django.contrib.auth.models import AnonymousUser


class ChessConsumer(AsyncWebsocketConsumer):

    async def game_message(self, event):
        await self.send(text_data=json.dumps(event['message']))

    async def connect(self):
        # Obtiene el id de la partida y el usuario a partir de la URL
        self.gameID = self.scope['url_route']['kwargs']['gameID']
        # Obtiene el token del usuario
        self.token = self.scope['query_string'].decode('utf-8')

        print("Este es el gameID que me llega -> " + self.gameID + " Con el token " + str(self.token))

        # Para que sea compatible con los test
        if not self.token:
            self.token = self.scope['query_string'].decode()

        # Obtiene la partida a traves del ID
        self.game = await self.from_id(self.gameID)
        # Comprueba que la partida exista
        if self.game is None:
            await self.accept()
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Invalid game with id {self.gameID}',
                'status': None,
                'playerID': None,
            }))
            await self.close()
            return

        # Obtiene el usuario a partir del token
        self.user = await self.get_user_by_token(self.token)
        # Comprueba que el usuario esté en la partida
        if self.user is None or not await self.is_valid_user_game_pair(self.user, self.game):
            if self.user is None:
                message = 'Invalid token. Connection not authorized.'
            else:
                message = f'Invalid game with id {self.gameID}'
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': message,
                'status': self.game.status.upper(),
                'playerID': None,
            }))
            await self.close()
        else:
            await self.accept()
            await self.channel_layer.group_add(str(self.gameID), self.channel_name)
            await self.game_cb('game', 'OK', self.game.status.upper(), self.user.id, self.game.board_state)


    async def receive(self, text_data):
        data = json.loads(text_data)
        print("Este es el mensaje que nos ha llegado por webSocket" + str(data))
        _from = ''
        to = ''
        playerID = ''
        promotion = ''
        # Comprueba el tipo de mensaje
        if data['type'] == 'move':
            try:
                _from = data['from']
                to = data['to']
                playerID = data['playerID']
                promotion = data['promotion']
        # Crea un nuevo movimiento, se llama a save con la creación y en ese método se comprueba la validez del movimiento.
                await sync_to_async(ChessMove.objects.create)(
                    game=self.game,
                    player=self.user,
                    move_from=_from,
                    move_to=to,
                    promotion=promotion
                )
                
                await self.move_cb('move', _from, to, playerID, promotion, None)
            except ValidationError:
                message = f"Error: invalid move (game is not active)"
                await self.move_cb('error', _from, to, playerID, promotion, message)
            except ValueError:
                message = f'Error: invalid move {_from}{to}'
                await self.move_cb('error', _from, to, playerID, promotion, message)
            except Exception:
                await self.move_cb('error', _from, to, playerID, promotion, None)
        else:
            return

    async def game_cb(self, _type, message, status, player_id, board_status):
        await self.channel_layer.group_send(
            str(self.gameID),
            {
                'type': 'game.message',  
                'message': {
                    'type': _type,
                    'message': message,
                    'status': status,
                    'playerID': player_id,
                    'board_status' : board_status,
                }
            }
        )

    async def move_cb(self, _type, m_from, m_to, player_id, promotion, _message):
        await self.channel_layer.group_send(str(self.gameID),{
                'type': 'move.message',  
                'message': {
                    'type': _type,
                    'from': m_from,
                    'to': m_to,
                    'playerID': player_id,
                    'promotion': promotion,
                    'message': _message, 
                }
            }
        )

    async def move_message(self, event):
        await self.send(text_data=json.dumps(event['message']))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(str(self.gameID), self.channel_name)

    @database_sync_to_async
    def get_user_by_token(self, token_key):
        try:
            token = Token.objects.get(key=token_key)
            return token.user
        except Token.DoesNotExist:
            return None

    @database_sync_to_async
    def from_id(self, gameID): #GET GAME FROM ID
        try:
            game = ChessGame.objects.get(id=gameID)
            return game
        except ChessGame.DoesNotExist:
            return None

    @database_sync_to_async
    def is_valid_user_game_pair(self, user, game):
        return ChessGame.objects.filter(Q(id=self.gameID, whitePlayer_id=self.user.id) | Q(id=self.gameID, blackPlayer_id=self.user.id)).exists()
    