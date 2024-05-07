from django.contrib import admin
from .models import Player, ChessGame, ChessMove

# Register your models here.
admin.site.register(Player)
admin.site.register(ChessGame)
admin.site.register(ChessMove)
