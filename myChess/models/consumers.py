
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

        print("Este es el gameID que me llega -> " + str(self.gameID) + " Con el token " + str(self.token))

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
            }))
            await self.close()
        else:
            await self.accept()
            await self.channel_layer.group_add(str(self.gameID), self.channel_name)

            dict = {
                "type" : "game_cb",
                'message': message,
                'status': self.game.status.upper(),
                'playerID': self.user.id,
            }
            
            await self.channel_layer.group_send(str(self.gameID), dict)


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
                dict = {
                    "type" : "move_cb",
                    'from': _from,
                    'to': to,
                    'playerID': playerID,
                    "promotion" : promotion
                }
                await self.channel_layer.group_send(str(self.gameID), dict)
            except ValidationError:
                message = f"Error: invalid move (game is not active)"
                await self.send(text_data=json.dumps({"type":'error', "message" : message}))
            except ValueError:
                message = f'Error: invalid move {_from}{to}'
                await self.send(text_data=json.dumps({"type":'error', "message" : message}))
            except Exception as ex:
                 message = f'Error: an exception has been produced ' + str(ex)
                await self.send(text_data=json.dumps({"type":'error', "message" : message}))
        else:
            await self.send(text_data=json.dumps({"type":'error', "message" : "Se ha recibido un mensaje no entendido"}))
            return

    async def game_cb(self, arg):
        await self.send(text_data=json.dumps({
                'type': 'game',  
                'message': arg["message"],
                'status': arg["status"],
                'playerID': arg["playerID"],
                'board_status' : arg["status"],
            })
        )

    async def move_cb(self, arg):
        await self.send(text_data=json.dumps({
                'type': 'move',  
                'from': arg["from"],
                'to': arg["to"],
                'playerID': arg["playerID"],
                'promotion': arg["promotion"],
            })
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
    
