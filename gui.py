import pygame
import sys
import rummy
import enum
import time
import math
import copy
import random


# Initialize Pygame
pygame.init()


# Variables
NUM_PLAYERS = 4
NUM_CARDS_PER_PLAYER = rummy.NUM_CARDS[NUM_PLAYERS]

# Constants
CARD_WIDTH, CARD_HEIGHT = 50, 75
CARD_CORNER_RADIUS = 5
CARD_BORDER_THICKNESS = 2
CARD_ANIMATION_TIME = 1 # secs

BUTTON_CORNER_RADIUS = 5
BUTTON_BORDER_THICKNESS = 2
BUTTON_ANIMATION_TIME = .5 # secs

INFO_FONT_SIZE = 25
MARGIN = 10
PLAYER_CARDS_X = MARGIN
PLAYER_CARDS_Y = CARD_HEIGHT * (NUM_PLAYERS+1) + (NUM_PLAYERS+5)*MARGIN
SCORE_WIDTH = 50
WIN_WIDTH = CARD_WIDTH * (NUM_CARDS_PER_PLAYER+1) + MARGIN * (NUM_CARDS_PER_PLAYER+5) + SCORE_WIDTH
WIN_HEIGHT = CARD_HEIGHT * (2*NUM_PLAYERS+1) + MARGIN * (3*NUM_PLAYERS+7) + INFO_FONT_SIZE
MELD_BUTTON_X, MELD_BUTTON_Y = 2*MARGIN, 2*MARGIN
MELD_X, MELD_Y = 2*MARGIN, 4*MARGIN + CARD_HEIGHT
DECK_X, DECK_Y = max(MELD_BUTTON_X + 110 + 120 + 2*MARGIN, WIN_WIDTH//2 - CARD_WIDTH - MARGIN//2), 2*MARGIN
DISCARD_X, DISCARD_Y = DECK_X + MARGIN + CARD_WIDTH, 2*MARGIN

WHITE = (255, 255, 255)
GREEN = (0, 100, 0)
LIGHT_GREEN = (152, 251, 152)
RED = (255, 0, 0)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
TABLE_COLOUR = (161, 102, 47) # Brown

# Setup display
screen = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT))
pygame.display.set_caption('Rummy GUI')

# Fonts
CARD_FONT = pygame.font.Font("arial.ttf", size=30)
BUTTON_FONT = pygame.font.Font("arial.ttf", size=30)
INFO_FONT = pygame.font.Font(None, size=INFO_FONT_SIZE)
SCORE_FONT = pygame.font.Font(None, size=30)

# Info variables
INFO_ON_TIME = 1 # secs
INFO_FADE_TIME = 1 # secs
info_text : str = ""
info_time : float = 0.0


class GUIState:
    def __init__(self, game:rummy.Game, num_human_players:int|None=None) -> None:
        if num_human_players is None:
            num_human_players = game.num_players
        # Assert that 0 <= num_human_players <= num_players
        assert 0 <= num_human_players <= game.num_players, f"Bad num_human_players: {num_human_players}; must be >= 0 and <= game.num_players"
        self.num_human_players = num_human_players

        # Create buttons
        self.buttons : dict[str, Button] = {
            "create_cancel_meld": Button("create_meld",
                    MELD_BUTTON_X, MELD_BUTTON_Y,
                    width=90,
                    text="Meld"),
            "confirm_meld": Button("confirm_meld",
                    MELD_BUTTON_X + 90 + MARGIN, DISCARD_Y,
                    width=120,
                    text="Confirm",
                    enabled=False)
        }
        self.is_selecting_meld : bool = True
        self.change_meld_mode(False)
        self.meld_selected : list[int] = []

        # Create cards
        self.cards : Cards = Cards(game, self)

        # Assign which players are human
        self.players_at_table = [] # Players who can see their cards
        self.human_players = [True] * num_human_players + [False] * (game.num_players-num_human_players)
        random.shuffle(self.human_players)

        # Create animator for whose_go bar
        self.player_go_animator = CompoundAnimator({
            "position": FloatAnimator(game.whose_go, 0.5),
            "color": ColorAnimator(GREEN if self.human_players[game.whose_go] else GRAY, 0.5)})

        # Create animators for scores
        self.scores_animators = [FloatAnimator(0, CARD_ANIMATION_TIME, animation_type="linear") for _ in range(game.num_players)]

        # Initialise tracker for whose_go in order to detect player change
        if self.human_players[game.whose_go]:
            self.waiting_for_show_confirmation = True
            show_info("Click to turn your cards over")
        else:
            self.waiting_for_show_confirmation = False

        # Force initial update
        self.update(game)
    
    def change_meld_mode(self, enabled:bool) -> None:
        if self.is_selecting_meld != enabled:
            self.is_selecting_meld = enabled

            if enabled:
                self.buttons["create_cancel_meld"].update(
                    width=110,
                    id="cancel_meld",
                    text="Cancel")
                self.buttons["confirm_meld"].update(
                    enabled=True,
                    x=MELD_BUTTON_X + 110 + MARGIN)
            
            else:
                self.buttons["create_cancel_meld"].update(
                    width=90,
                    id="create_meld",
                    text="Meld")
                self.buttons["confirm_meld"].update(enabled=False, x=MELD_BUTTON_X + 90 + MARGIN)

                self.meld_selected = []

    def check_for_wait(self, game):
        if self.human_players[game.whose_go] and self.num_human_players > 1 and not game.game_ended:
            self.waiting_for_show_confirmation = True
            show_info("Click to turn your cards over")

    def update(self, game:rummy.Game) -> None:
        # Update card states
        self.cards.update(game, self)
        
        # Move green player bar
        if self.player_go_animator.get_target_value("position") != game.whose_go:
            self.player_go_animator.start_animation({
                "position": game.whose_go,
                "color": GREEN if self.human_players[game.whose_go] else GRAY
            })
            
            self.check_for_wait(game)

        # Show/hide cards
        if game.game_ended:
            self.players_at_table = [i for i in range(game.num_players)]
        elif self.waiting_for_show_confirmation:
            self.players_at_table = []
        else:
            self.players_at_table = [game.whose_go] if self.human_players[game.whose_go] else []
        
        # Check whether score has changed
        for i in range(game.num_players):
            if self.scores_animators[i].get_target_value() != game.scores[i]:
                self.scores_animators[i].start_animation(game.scores[i])


class Animator:
    def __init__(self) -> None:
        pass
    
    def start_animation(self, target_value) -> None:
        pass

    def get_current_value(self) -> float | bool | str:
        pass
        
    def get_target_value(self) -> float | bool | str:
        pass

    def set_value(self, value) -> None:
        pass

    def is_animating(self) -> bool:
        pass

class FloatAnimator(Animator):
    def __init__(self, initial_value:float, animation_time:float, animation_type:str="parametric", parametric_alpha:float=3) -> None:
        self.start_time : float = 0

        self.start_value = initial_value
        self.target_value = initial_value

        self.animating = False

        assert animation_time >= 0, "Animation time cannot be negative"
        self.animation_time = animation_time
        assert animation_type in ["linear", "bezier", "parametric", "half_step", "step", "parametric_bounce"], f"Bad animation type: {animation_type}"
        self.animation_type = animation_type
        self.alpha = parametric_alpha
    
    def start_animation(self, target_value) -> None:
        self.start_value = self.get_current_value()
        self.target_value = target_value
        self.start_time = time.time()
        self.animating = True
    
    def get_current_value(self) -> float:
        proportion = pygame.math.clamp((time.time() - self.start_time) / self.animation_time, 0, 1)

        if proportion == 1:
            self.animating = False


        if self.animation_type == "linear":
            # Linear
            return self.start_value + (self.target_value - self.start_value) * proportion
        
        if self.animation_type == "bezier":
            # Cubic bezier function
            distance = proportion * proportion * (3 - 2 * proportion)
            return self.start_value + (self.target_value - self.start_value) * distance
        
        if self.animation_type == "parametric":
            # Uses the following equation: x^a / (x^a + (1-x)^a)
            # a -> alpha. With a=1, linear; as a -> inf, the line becomes steeper in the middle
            distance = proportion**self.alpha / (proportion**self.alpha + (1 - proportion)**self.alpha)
            return self.start_value + (self.target_value - self.start_value) * distance
        
        if self.animation_type == "half_step":
            # Step function at t=0.5
            if proportion < 0.5:
                return self.start_value
            else:
                return self.target_value
            
        if self.animation_type == "step":
            # Step function at t=0.5
            if proportion == 0:
                return self.start_value
            else:
                return self.target_value

        if self.animation_type == "parametric_bounce":
            # Parametric equation, but returning to original value
            self.alpha = 3

            distance = 1 - 2 * abs(0.5 - (proportion**self.alpha / (proportion**self.alpha + (1 - proportion)**self.alpha)))
            return self.start_value + (self.target_value - self.start_value) * distance


    def get_target_value(self) -> float:
        return self.target_value

    def set_value(self, value:float) -> None:
        self.start_time : float = 0

        self.start_value = value
        self.target_value = value

        self.animating = False

    def is_animating(self) -> bool:
        return self.animating
    
class CompoundAnimator(Animator):
    def __init__(self, animators:dict[str,Animator]) -> None:
        self.animators = animators
    
    def start_animation(self, target_values:dict[str,float|bool|str]) -> None:
        for key, value in target_values.items():
            self.animators[key].start_animation(value)
    
    def get_current_value(self, key:str) -> float|bool|str:
        return self.animators[key].get_current_value()
        
    def get_target_value(self, key:str) -> float|bool|str:
        return self.animators[key].get_target_value()

    def set_value(self, values:dict[str,float|bool|str]) -> None:
        for key, value in values.items():
            self.animators[key].set_value(value)

    def is_animating(self) -> bool:
        return any([animator.is_animating() for animator in self.animators.values()])
    
class ColorAnimator(Animator):
    def __init__(self, initial_color:tuple[int], animation_time:float, animation_type:str="parametric", parametric_alpha:float=1.7) -> None:
        self.animators = tuple([FloatAnimator(val, animation_time, animation_type, parametric_alpha=parametric_alpha) for val in initial_color])
    
    def start_animation(self, target_value:tuple[int]) -> None:
        for i in range(len(self.animators)):
            self.animators[i].start_animation(target_value[i])
    
    def get_current_value(self) -> tuple[int]:
        return tuple(animator.get_current_value() for animator in self.animators)
        
    def get_target_value(self) -> tuple[int]:
        return tuple(animator.get_target_value() for animator in self.animators)

    def set_value(self, value:tuple[int]) -> None:
        for i in range(len(self.animators)):
            self.animators[i].set_value(value[i])

    def is_animating(self) -> bool:
        return self.animators[0].is_animating()
    
class BooleanAnimator(Animator):
    def __init__(self, initial_value:bool, animation_time:float, animation_type:str="step") -> None:
        assert animation_type in ["half_step", "step"], f"Bad animation type: {animation_type}"
        
        self.float_animator = FloatAnimator(int(initial_value), animation_time, animation_type)
    
    def start_animation(self, target_value:bool) -> None:
        if target_value != self.float_animator.get_target_value():
            self.float_animator.start_animation(int(target_value))
    
    def get_current_value(self) -> bool:
        return bool(self.float_animator.get_current_value())
        
    def get_target_value(self) -> bool:
        return bool(self.float_animator.get_target_value())

    def set_value(self, value:bool) -> None:
        self.float_animator.set_value(int(value))

    def is_animating(self) -> bool:
        return self.float_animator.is_animating()
  
class TextAnimator(Animator):
    def __init__(self, initial_text:str, animation_time:float, animation_type:str="step") -> None:
        assert animation_type in ["half_step", "step"], f"Bad animation type: {animation_type}"

        self.start_text = initial_text
        self.target_text = initial_text
        
        self.bool_animator = BooleanAnimator(0, animation_time, animation_type)
    
    def start_animation(self, target_text:str) -> None:
        if target_text != self.target_text:
            self.start_text = self.target_text
            self.target_text = target_text

            self.bool_animator.float_animator.set_value(0)
            self.bool_animator.start_animation(1)
    
    def get_current_value(self) -> str:
        return self.target_text if self.bool_animator.get_current_value() else self.start_text
        
    def get_target_value(self) -> str:
        return self.target_text

    def set_value(self, value:str) -> None:
        self.start_text = value
        self.target_text = value

        self.bool_animator.set_value(0)

    def is_animating(self) -> bool:
        return self.bool_animator.is_animating()


class Cards:
    def __init__(self, game:rummy.Game, state:GUIState) -> None:
        self.game : rummy.Game = game
        self.old_game : rummy.Game = game
        self.cards : dict[str, Card] = {card_name: Card("deck",
                                              DECK_X, DECK_Y,
                                              face_up=False,
                                              text=card_name) for card_name in game.deck} # Spawn all cards in the deck face down
        self.priority_draw_cards : list[Card] = []
        self.update(game, state)
    
    def update(self, game:rummy.Game, state:GUIState):
        # Cards in the deck
        for card_name in game.deck:
            self.cards[card_name].update(DECK_X, DECK_Y, id="deck", face_up=False)

        # Cards in the discard pile
        for card_name in game.discard_pile:
            self.cards[card_name].update(DISCARD_X, DISCARD_Y, id="discard")
        
        # Cards in melds
        temp_x = MELD_X
        temp_y = MELD_Y

        for meld in game.melds:
            if temp_x + len(meld)*CARD_WIDTH > WIN_WIDTH - 2*MARGIN:
                # Carriage return
                temp_y += CARD_HEIGHT + MARGIN
                temp_x = MELD_X

            for card_name in meld:
                self.cards[card_name].update(temp_x, temp_y, id="meld")
                temp_x += CARD_WIDTH
            
            temp_x += MARGIN

        # Cards in hands
        for i, cards in enumerate(game.hands):
            for j, card_name in enumerate(cards):
                selected = i == game.whose_go and j in state.meld_selected

                self.cards[card_name].update(
                    PLAYER_CARDS_X + MARGIN + j * (CARD_WIDTH + MARGIN),
                    PLAYER_CARDS_Y + MARGIN + i * (CARD_HEIGHT + MARGIN*2),
                    id=f"card-{i}-{j}",
                    selected=selected,
                    face_up = i in state.players_at_table
                )


        # Handle priority cards - cards which need to be drawn last so they appear on top
        self.priority_draw_cards : list[Card] = []

        # Add discard pile to priority drawing; to be drawn at the end
        self.priority_draw_cards += [self.cards[card] for card in game.discard_pile]

        for card in self.cards.values():
            if any([card.x.is_animating(), card.y.is_animating()]):
                self.priority_draw_cards.append(card)

    def draw(self, surface:pygame.surface.Surface):
        for card in self.cards.values():
            if not card in self.priority_draw_cards:
                card.draw(surface)
        
        for card in self.priority_draw_cards:
            card.draw(surface)

class Card:
    def __init__(self, id:str, x:int, y:int, text:str="", width:int=CARD_WIDTH, height:int=CARD_HEIGHT, face_up:bool=True, selected:bool=False) -> None:
        self.id = id

        self.x = FloatAnimator(x, CARD_ANIMATION_TIME)
        self.y = FloatAnimator(y, CARD_ANIMATION_TIME)
        
        self.width = width
        self.height = height

        self.rect = pygame.Rect(self.x.get_current_value(), self.y.get_current_value(), self.width, self.height)

        self.text = text

        self.face_up = CompoundAnimator({
            "boolean": BooleanAnimator(face_up, CARD_ANIMATION_TIME, animation_type="half_step"),
            "color": ColorAnimator(WHITE if face_up else RED, CARD_ANIMATION_TIME, animation_type="half_step"),
            "abs_width": FloatAnimator(self.width if face_up else -self.width, CARD_ANIMATION_TIME),
            "text_width": FloatAnimator(1 if face_up else -1, CARD_ANIMATION_TIME)
        })
        self.selected = CompoundAnimator({
            "boolean": BooleanAnimator(selected, CARD_ANIMATION_TIME),
            "color": ColorAnimator(LIGHT_GREEN if selected else WHITE, 0.5, animation_type="linear")
        })
    
    def update(self, x:int|None=None, y:int|None=None, id:str|None=None, face_up:bool=True, selected:bool|None=False):
        # Position
        if x is None:
            x = self.x.get_target_value()
        if y is None:
            y = self.y.get_target_value()

        if x != self.x.get_target_value() or y != self.y.get_target_value():
            self.x.start_animation(x)
            self.y.start_animation(y)

        if not id is None:
            self.id = id
    
        if bool(self.face_up.animators["boolean"].get_target_value()) != face_up:
            self.face_up.start_animation({
                "boolean": face_up,
                "color": WHITE if face_up else RED,
                "abs_width": self.width if face_up else -self.width,
                "text_width": 1 if face_up else -1
            })

        if not selected is None and bool(self.selected.animators["boolean"].get_target_value()) != selected:
            self.selected.start_animation({
                "boolean": selected,
                "color": LIGHT_GREEN if selected else WHITE
            })

    def draw(self, surface:pygame.surface.Surface) -> pygame.Rect:
        """Draw a card with rounded corners and text."""
        self.rect = pygame.Rect(
            self.x.get_current_value() + (self.width//2 - abs(self.face_up.get_current_value("abs_width")//2)),
            self.y.get_current_value(),
            max(2*CARD_BORDER_THICKNESS, abs(self.face_up.get_current_value("abs_width"))),
            self.height)
        
        # Colour
        if self.face_up.get_current_value("boolean") == False or self.face_up.is_animating():
            # Flipping or is flipped
            card_color = self.face_up.get_current_value("color")
        elif self.selected.get_current_value("boolean") == True or self.selected.is_animating():
            card_color = self.selected.get_current_value("color")
        else:
            card_color = WHITE

        border_color = BLACK
        
        # Draw the card
        pygame.draw.rect(surface, card_color, self.rect, border_radius=CARD_CORNER_RADIUS)
        pygame.draw.rect(surface, border_color, self.rect, CARD_BORDER_THICKNESS, border_radius=CARD_CORNER_RADIUS)
        
        # Draw the text
        text_surface = CARD_FONT.render(self.text if self.face_up.get_current_value("abs_width") > 0 else "", True, BLACK if self.text[1] in "♣♠" else RED)
        text_surface = pygame.transform.scale(text_surface, (text_surface.get_width() * max(0, self.face_up.get_current_value("text_width")), text_surface.get_height()))
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)


class Button:
    def __init__(self, id:str, x:int, y:int, text, width:int, height:int=CARD_WIDTH, enabled:bool=True) -> None:
        self.id = id

        self.x = FloatAnimator(x, BUTTON_ANIMATION_TIME)
        self.y = FloatAnimator(y, BUTTON_ANIMATION_TIME)
        
        self.width = FloatAnimator(width, BUTTON_ANIMATION_TIME)
        self.height = FloatAnimator(height, BUTTON_ANIMATION_TIME)

        self.rect = pygame.Rect(self.x.get_current_value(), self.y.get_current_value(), self.width.get_current_value(), self.height.get_current_value())

        self.text = CompoundAnimator({
            "text": TextAnimator(text, BUTTON_ANIMATION_TIME, animation_type="half_step"),
            "color": ColorAnimator(BLACK if enabled else TABLE_COLOUR, BUTTON_ANIMATION_TIME, animation_type="parametric_bounce", parametric_alpha=1.5)
        })

        self.enabled = CompoundAnimator({
            "boolean": BooleanAnimator(enabled, BUTTON_ANIMATION_TIME, animation_type="step"),
            "background_color": ColorAnimator(WHITE if enabled else TABLE_COLOUR, BUTTON_ANIMATION_TIME),
            "border_color": ColorAnimator(BLACK if enabled else TABLE_COLOUR, BUTTON_ANIMATION_TIME),
            "text_color": ColorAnimator(BLACK if enabled else TABLE_COLOUR, BUTTON_ANIMATION_TIME)
        })
    
    def update(self, x:int|None=None, y:int|None=None, width:int|None=None, height:int|None=None, id:str|None=None, text:str|None=None, enabled:bool|None=None):
        # Position
        if x is None:
            x = self.x.get_target_value()
        if y is None:
            y = self.y.get_target_value()

        if x != self.x.get_target_value() or y != self.y.get_target_value():
            self.x.start_animation(x)
            self.y.start_animation(y)

        # Size
        if not width is None and width != self.width.get_target_value():
            self.width.start_animation(width)
        if not height is None and height != self.height.get_target_value():
            self.height.start_animation(height)

        # ID
        if not id is None:
            self.id = id

        # Text
        if not text is None and text != self.text.get_target_value("text"):
            self.text.start_animation({
                "text": text,
                "color": WHITE
            })

        # Enabled
        if not enabled is None and self.enabled.get_current_value("boolean") != enabled:
            self.enabled.start_animation({
                "boolean": enabled,
                "background_color": WHITE if enabled else TABLE_COLOUR,
                "border_color": BLACK if enabled else TABLE_COLOUR,
                "text_color": BLACK if enabled else TABLE_COLOUR
            })

    def draw(self, surface:pygame.surface.Surface) -> pygame.Rect:
        """Draw a card with rounded corners and text."""
        self.rect = pygame.Rect(
            self.x.get_current_value(),
            self.y.get_current_value(),
            self.width.get_current_value(),
            self.height.get_current_value())
        
        # Colour
        if self.enabled.is_animating() or not self.enabled.get_current_value("boolean"):
            text_color = self.enabled.get_current_value("text_color")
        else:
            text_color = self.text.get_current_value("color")
        border_color = self.enabled.get_current_value("border_color")
        
        # Draw the background
        pygame.draw.rect(surface, self.enabled.get_current_value("background_color"), self.rect, border_radius=CARD_CORNER_RADIUS)
        
        # Draw the text
        text_surface = BUTTON_FONT.render(self.text.get_current_value("text"), True, text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

        # Draw the border
        pygame.draw.rect(surface, border_color, self.rect, BUTTON_BORDER_THICKNESS, border_radius=BUTTON_CORNER_RADIUS)


def draw_buttons(surface:pygame.surface.Surface, state:GUIState):
    for button in state.buttons.values():
        button.draw(surface)

def draw_scores(surface:pygame.surface.Surface, game:rummy.Game, state:GUIState) -> None:
    for i, score in enumerate(game.scores):
        text_surface = SCORE_FONT.render(str(int(state.scores_animators[i].get_current_value())), True, BLACK)
        text_rect = text_surface.get_rect(center=(WIN_WIDTH - MARGIN - SCORE_WIDTH//2, PLAYER_CARDS_Y + MARGIN + i * (CARD_HEIGHT + MARGIN*2) + CARD_HEIGHT//2))
        surface.blit(text_surface, text_rect)

def draw_info(surface:pygame.surface.Surface) -> None:
    if "click" in info_text.lower():
        colour_multiplier = math.sin((time.time() - info_time) * (2*math.pi) / INFO_FADE_TIME / 2) / 2 + .5
    else:
        colour_multiplier = pygame.math.clamp((time.time() - info_time - INFO_ON_TIME)/INFO_FADE_TIME, 0, 1)

    text_surface = INFO_FONT.render(info_text, True, [255 * colour_multiplier]*3)
    text_rect = text_surface.get_rect(center=(WIN_WIDTH//2, WIN_HEIGHT - MARGIN - INFO_FONT_SIZE//2))
    surface.blit(text_surface, text_rect)


def show_info(text:str) -> None:
    global info_text
    global info_time

    info_text = str(text)
    info_time = time.time()


def on_mouse_click(position:tuple, game:rummy.Game, state:GUIState) -> None:
    """Check if a card is clicked and call a function."""
    if game.game_ended and not game.has_shuffled:
        # Shuffle
        game.shuffle()
        show_info("Click again to deal")

        return # Disallow any button being clicked at the same time
    
    if game.game_ended and game.has_shuffled:
        # Start a new game
        game.deal()
        show_info("")

        state.check_for_wait(game)


        return # Disallow any button being clicked at the same time
    
    if not state.human_players[game.whose_go]:
        # Computer is playing; block all clicks
        show_info("Computer is now playing; you can't do anything")

        return # Disallow any button being clicked at the same time

    if state.waiting_for_show_confirmation:
        # Flip current players cards
        state.waiting_for_show_confirmation = False
        show_info("")

        return # Disallow any button being clicked at the same time
    
    for button in state.buttons.values():
        if button.rect.collidepoint(position) and button.enabled.get_current_value("boolean"):
            # Check for meld button clicks
            if button.id == "create_meld":
                state.change_meld_mode(True)
            elif button.id == "cancel_meld":
                state.change_meld_mode(False)
            elif button.id == "confirm_meld":
                try:
                    game.lay_meld(game.whose_go, state.meld_selected)
                except AssertionError as e:
                    show_info(e)
                
                state.change_meld_mode(False)

            return # Disallow multiple buttons being clicked at the same time
                
    for card in state.cards.cards.values():
        if card.rect.collidepoint(position):
            if not state.is_selecting_meld:
                # Normal mode
                if card.id == "deck":
                    try:
                        game.draw(player=game.whose_go, from_deck=True)
                    except AssertionError as e:
                        show_info(e)
                elif card.id == "discard":
                    try:
                        game.draw(player=game.whose_go, from_deck=False)
                    except AssertionError as e:
                        show_info(e)
                elif card.id[:4] == "card":
                    # Parse player and card index
                    _, player, card_index = [i for i in card.id.split("-")]
                    player = int(player)
                    card_index = int(card_index)

                    try:
                        game.discard(player=player, card_index=card_index)
                        
                        if game.game_ended:
                            show_info("Game has ended; click anywhere to shuffle")
                    except AssertionError as e:
                        show_info(e)
            
            else:
                # Meld selection mode
                if card.id[:4] == "card":
                    # Parse player and card index
                    _, player, card_index = [i for i in card.id.split("-")]
                    player = int(player)
                    card_index = int(card_index)

                    if player == game.whose_go:
                        if not card_index in state.meld_selected:
                            # Card hasn't been clicked yet
                            state.meld_selected.append(card_index)
                        else:
                            state.meld_selected.pop(state.meld_selected.index(card_index))
                    else:
                        show_info(f"Can't touch that card, it's player {game.whose_go}'s turn, not player {player}")

            return # Disallow multiple buttons being clicked at the same time


def main() -> None:
    # Initialise game
    game = rummy.Game(NUM_PLAYERS)

    # Initialise GUI state
    state = GUIState(game, num_human_players=None)

    # Deal cards
    game.deal()
    
    # Initialise pygame clock
    clock = pygame.time.Clock()

    # Main loop
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    on_mouse_click(event.pos, game, state)
        
        state.update(game)

        screen.fill(WHITE)

        # Draw "table" rectangle
        pygame.draw.rect(
            screen,
            TABLE_COLOUR,
            pygame.Rect(MARGIN, MARGIN, WIN_WIDTH - 2*MARGIN, CARD_HEIGHT * (NUM_PLAYERS+1) + (NUM_PLAYERS+3)*MARGIN),
            border_radius=CARD_CORNER_RADIUS + MARGIN
        )

        # Draw banner to display current player
        pygame.draw.rect(
            screen,
            state.player_go_animator.get_current_value("color"),
            pygame.Rect(
                PLAYER_CARDS_X,
                PLAYER_CARDS_Y + (CARD_HEIGHT + MARGIN*2)*state.player_go_animator.get_current_value("position"),
                (CARD_WIDTH+MARGIN) * (NUM_CARDS_PER_PLAYER+1) + MARGIN,
                CARD_HEIGHT + 2*MARGIN),
            border_radius=CARD_CORNER_RADIUS + MARGIN
        )

        # Draw buttons
        draw_buttons(screen, state)

        # Draw cards
        state.cards.draw(screen)

        # Draw scores
        draw_scores(screen, game, state)

        # Draw info
        draw_info(screen)
        
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()
