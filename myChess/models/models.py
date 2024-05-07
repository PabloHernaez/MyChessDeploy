from django.db import models
from django.contrib.auth.models import AbstractUser
import chess
from django.core.exceptions import ValidationError

# Create your models here.


class Player(AbstractUser):

    rating = models.IntegerField(
        help_text="The rate of the player",
        default=-1
    )

    username = models.CharField(
        unique=True,
        help_text="The name of the Player",
        max_length=100,
        default=""
    )

    class Meta:
        ordering = ["rating"]

    def __str__(self):

        return self.username+" ("+str(self.rating)+")"


class ChessGame(models.Model):
    PENDING = 'PENDING'
    ACTIVE = 'ACTIVE'
    FINISHED = 'FINISHED'
    DEFAULT_BOARD_STATE = chess.STARTING_FEN
    STATUS_CHOICES = [
            ('PENDING', 'pending'),
            ('ACTIVE', 'active'),
            ('FINISHED', 'finished'),
    ]
    status = models.CharField(
        max_length=64,
        choices=STATUS_CHOICES,
        default='pending'
    )

    board_state = models.TextField(
        default=DEFAULT_BOARD_STATE,
        help_text="Almacena la posición de las piezas en formato FEN"
    )

    start_time = models.DateTimeField(
        'Start',
        auto_now=True,
        null=True,
        blank=True,
        help_text="Game starting time"
    )

    end_time = models.DateTimeField(
        'Ending',
        null=True,
        blank=True,
        help_text="Game ending time"
    )

    timeControl = models.CharField(
        'Time Control',
        max_length=50,
        help_text="Control de tiempo para cada jugador"
    )

    whitePlayer = models.ForeignKey(
        'Player',
        related_name='whitePlayer',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    blackPlayer = models.ForeignKey(
        'Player',
        related_name='blackPlayer',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    winner = models.ForeignKey(
        'Player',
        related_name='games_won',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="El ganador de la partida." +
        "Puede ser nulo si el juego está " +
        "pendiente o ha terminado en empate.")

    def __str__(self):
        white_data = str(self.whitePlayer) if self.whitePlayer else "unknown"
        black_data = str(self.blackPlayer) if self.blackPlayer else "unknown"

        return f"GameID=({self.id}) {white_data} vs {black_data}"


class ChessMove(models.Model):

    PROMOTIONS = (
        ('q', 'queen'),
        ('r', 'rook'),
        ('n', 'knight'),
        ('b', 'bishop'),
    )

    game = models.ForeignKey(
        'ChessGame',
        on_delete=models.RESTRICT
    )

    player = models.ForeignKey(
        'Player',
        on_delete=models.RESTRICT
    )

    move_from = models.CharField(
        max_length=2,
        help_text="The coords from where the figure is moved from"
    )

    move_to = models.CharField(
        max_length=2,
        help_text="The coordenates where the figure is moved to"
    )

    promotion = models.CharField(
        max_length=8,
        help_text="The figure that is promoted to",
        choices=PROMOTIONS, null=True
    )

    def __str__(self):
        return self.player.username+" ("+str(self.player.rating)+"): "+self.move_from+" -> " + self.move_to

    def save(self, *args, **kwargs):
        self.game.refresh_from_db()
        if self.game.status == 'active':
            fen_board = chess.Board(self.game.board_state)
            coords = str(self.move_from)+str(self.move_to)
            if self.promotion:
                coords = coords + str(self.promotion)
            move = chess.Move.from_uci(coords)
            if move not in fen_board.legal_moves:
                raise ValueError("Error, accion ilegal")
            else:
                fen_board.push(move)
                if fen_board.is_checkmate():
                    self.game.status = 'FINISHED'
                    self.game.winner = self.player
                
                elif fen_board.is_stalemate() or fen_board.is_insufficient_material() or fen_board.is_seventyfive_moves() or fen_board.is_fivefold_repetition():
                    self.game.status = 'FINISHED'
                
                self.game.board_state = fen_board.fen()
                self.game.save()
                super().save(*args, **kwargs)
        else:
            raise ValidationError("Game is not active")
