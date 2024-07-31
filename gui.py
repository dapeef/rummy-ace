import pygame
import sys
from game import Game
import enum
import time
import math


# Initialize Pygame
pygame.init()

# Variables
NUM_CARDS_PER_PLAYER = 10
NUM_PLAYERS = 2

# Constants
CARD_WIDTH, CARD_HEIGHT = 50, 75
CARD_CORNER_RADIUS = 5
CARD_BORDER_THICKNESS = 2
INFO_FONT_SIZE = 25
MARGIN = 10
PLAYER_CARDS_X = MARGIN
PLAYER_CARDS_Y = CARD_HEIGHT * (NUM_PLAYERS+1) + (NUM_PLAYERS+5)*MARGIN
SCORE_WIDTH = 50
WIN_WIDTH = CARD_WIDTH * (NUM_CARDS_PER_PLAYER+1) + MARGIN * (NUM_CARDS_PER_PLAYER+5) + SCORE_WIDTH
WIN_HEIGHT = CARD_HEIGHT * (2*NUM_PLAYERS+1) + MARGIN * (2*NUM_PLAYERS+8) + INFO_FONT_SIZE
DECK_X, DECK_Y = WIN_WIDTH//2 - CARD_WIDTH - MARGIN//2, 2*MARGIN
DISCARD_X, DISCARD_Y = WIN_WIDTH//2 + MARGIN//2, 2*MARGIN
MELD_BUTTON_X, MELD_BUTTON_Y = 2*MARGIN, 2*MARGIN
MELD_X, MELD_Y = 2*MARGIN, 4*MARGIN + CARD_HEIGHT

WHITE = (255, 255, 255)
GREEN = (0, 100, 0)
LIGHT_GREEN = (0, 200, 0)
RED = (255, 0, 0)
BLACK = (0, 0, 0)
TABLE_COLOUR = (161, 102, 47) # Brown

# Setup display
screen = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT))
pygame.display.set_caption('Rummy GUI')

# Fonts
CARD_FONT = pygame.font.Font(None, size=36)
INFO_FONT = pygame.font.Font(None, size=INFO_FONT_SIZE)
SCORE_FONT = pygame.font.Font(None, size=30)

# Info variables
INFO_ON_TIME = 1 # secs
INFO_FADE_TIME = 1 # secs
info_text : str = ""
info_time : float = 0.0


# TODO turn this into an enum
class GUIState:
    def __init__(self) -> None:
        self.is_selecting_meld : bool = False
        self.meld_selected : list[int] = []


def draw_card(surface:pygame.surface.Surface, x:int, y:int, width:int=CARD_WIDTH, height:int=CARD_HEIGHT, face_up:bool=True, selected:bool=False, card_text:str="") -> pygame.Rect:
    """Draw a card with rounded corners and text."""
    card_rect = pygame.Rect(x, y, width, height)
    card_color = LIGHT_GREEN if selected else (WHITE if face_up else RED)
    border_color = BLACK
    
    # Draw the card
    pygame.draw.rect(surface, card_color, card_rect, border_radius=CARD_CORNER_RADIUS)
    pygame.draw.rect(surface, border_color, card_rect, CARD_BORDER_THICKNESS, border_radius=CARD_CORNER_RADIUS)
    
    # Draw the text
    text_surface = CARD_FONT.render(card_text if face_up else "", True, BLACK)
    text_rect = text_surface.get_rect(center=card_rect.center)
    surface.blit(text_surface, text_rect)

    return card_rect

def draw_cards_for_players(surface:pygame.surface.Surface, game:Game, state:GUIState) -> dict[str, pygame.Rect]:
    """Draw cards for each player."""
    card_rects: dict[str, pygame.Rect] = {}

    for i, cards in enumerate(game.hands):
        for j, card in enumerate(cards):
            selected = i == game.whose_go and j in state.meld_selected

            card_rects[f"card-{i}-{j}"] = draw_card(
                surface,
                PLAYER_CARDS_X + MARGIN + j * (CARD_WIDTH + MARGIN),
                PLAYER_CARDS_Y + MARGIN + i * (CARD_HEIGHT + MARGIN),
                selected=selected,
                card_text=card
            )
    
    return card_rects

def draw_all_clickable(surface:pygame.surface.Surface, game:Game, state:GUIState) -> dict[str, pygame.Rect]:
    hit_boxes : dict[str, pygame.Rect] = {}
    
    # Draw deck and discard pile
    hit_boxes["deck"] = draw_card(surface, DECK_X, DECK_Y, face_up=False)
    hit_boxes["discard"] = draw_card(surface, DISCARD_X, DISCARD_Y, card_text=game.discard_pile[-1] if len(game.discard_pile) > 0 else "")
    
    # Draw cards for players
    hit_boxes |= draw_cards_for_players(surface, game, state)

    if state.is_selecting_meld:
        # Draw button to cancel a meld
        hit_boxes["cancel_meld"] = draw_card(surface, MELD_BUTTON_X, DISCARD_Y, width=110, height=50, card_text="Cancel")
        # Draw button to confirm a meld
        hit_boxes["confirm_meld"] = draw_card(surface, MELD_BUTTON_X + 110 + MARGIN, DISCARD_Y, width=120, height=50, card_text="Confirm")
    else:
        # Draw button to lay a meld
        hit_boxes["create_meld"] = draw_card(surface, MELD_BUTTON_X, MELD_BUTTON_Y, width=90, height=50, card_text="Meld")

    return hit_boxes

def draw_melds(surface:pygame.surface.Surface, game:Game) -> None:
    x_pos = MELD_X
    y_pos = MELD_Y

    for meld in game.melds:
        if x_pos + len(meld)*CARD_WIDTH > WIN_WIDTH - 2*MARGIN:
            # Carriage return
            y_pos += CARD_HEIGHT + MARGIN
            x_pos = MELD_X

        for card in meld:
            draw_card(surface, x_pos, y_pos, card_text=card)
            x_pos += CARD_WIDTH
        
        x_pos += MARGIN

def draw_scores(surface:pygame.surface.Surface, game:Game) -> None:
    for i, score in enumerate(game.scores):
        text_surface = SCORE_FONT.render(str(score), True, BLACK)
        text_rect = text_surface.get_rect(center=(WIN_WIDTH - MARGIN - SCORE_WIDTH//2, PLAYER_CARDS_Y + MARGIN + i * (CARD_HEIGHT + MARGIN) + CARD_HEIGHT//2))
        surface.blit(text_surface, text_rect)

def draw_info(surface:pygame.surface.Surface) -> None:
    if info_text == "Game has ended; click anywhere to redeal":
        colour_multiplier = math.sin((time.time() - info_time) * (2*math.pi) / INFO_FADE_TIME / 2) / 2 + .5
    else:
        colour_multiplier = pygame.math.clamp((time.time() - info_time - INFO_ON_TIME)/INFO_FADE_TIME, 0, 1)

    text_surface = INFO_FONT.render(info_text, True, [255 * colour_multiplier]*3)
    text_rect = text_surface.get_rect(center=(WIN_WIDTH//2, WIN_HEIGHT - MARGIN - INFO_FONT_SIZE//2))
    surface.blit(text_surface, text_rect)


def show_info(text:str):
    global info_text
    global info_time

    info_text = str(text)
    info_time = time.time()


def check_button_click(position:tuple, card_rects:dict[str, pygame.Rect], game:Game, state:GUIState) -> None:
    """Check if a card is clicked and call a function."""
    if game.game_ended:
        # Start a new game
        game.deal()
    
    else:
        for id, rect in card_rects.items():
            if rect.collidepoint(position):
                # Handle the card click event here
                print(f"Card clicked at {position}. Button id: {id}")

                # Check for meld button clicks
                if id == "create_meld":
                    state.is_selecting_meld = True
                elif id == "cancel_meld":
                    state.is_selecting_meld = False
                elif id == "confirm_meld":
                    state.is_selecting_meld = False
                    print(state.meld_selected)
                    game.lay_meld(game.whose_go, state.meld_selected)

                    state.meld_selected = []

                if not state.is_selecting_meld:
                    # Normal mode
                    if id == "deck":
                        print("DECK")
                        try:
                            game.draw(player=game.whose_go, from_deck=True)
                        except AssertionError as e:
                            print(e)
                            show_info(e)
                    elif id == "discard":
                        print("DISCARD")
                        try:
                            game.draw(player=game.whose_go, from_deck=False)
                        except AssertionError as e:
                            print(e)
                            show_info(e)
                    elif id[:4] == "card":
                        # Parse player and card index
                        _, player, card_index = [i for i in id.split("-")]
                        player = int(player)
                        card_index = int(card_index)
                        print(f"{player = } and {card_index = }")

                        # assert player == game.whose_go, f"Can't touch that card, it's player {game.whose_go}'s turn, not player {player}"

                        try:
                            game.discard(player=player, card_index=card_index)
                            
                            if game.game_ended:
                                show_info("Game has ended; click anywhere to redeal")
                        except AssertionError as e:
                            print(e)
                            show_info(e)
                
                else:
                    # Meld selection mode
                    if id[:4] == "card":
                        # Parse player and card index
                        _, player, card_index = [i for i in id.split("-")]
                        player = int(player)
                        card_index = int(card_index)
                        print(f"{player = } and {card_index = } selected for meld")

                        if player == game.whose_go:
                            if not card_index in state.meld_selected:
                                # Card hasn't been clicked yet
                                state.meld_selected.append(card_index)
                            else:
                                state.meld_selected.pop(state.meld_selected.index(card_index))
                        else:
                            print(f"Can't touch that card, it's player {game.whose_go}'s turn, not player {player}")
                            show_info(f"Can't touch that card, it's player {game.whose_go}'s turn, not player {player}")

                break


def main() -> None:
    # Initialise game
    game = Game(NUM_PLAYERS)

    # game.melds = [["A", "B", "C"], ["A", "B", "C", "D"], ["A", "B", "C"], ["A", "B", "C"], ["A", "B", "C"], ["A", "B", "C"]]

    # Initialise GUI state
    state = GUIState()
    
    # Initialise pygame clock
    clock = pygame.time.Clock()
    
    # Initialise to empty
    hit_boxes : dict[str, pygame.Rect] = {}

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    check_button_click(event.pos, hit_boxes, game, state)
        
        screen.fill(WHITE)

        # Draw "table" rectangle
        pygame.draw.rect(
            screen,
            TABLE_COLOUR,
            pygame.Rect(MARGIN, MARGIN, WIN_WIDTH - 2*MARGIN, CARD_HEIGHT * (NUM_PLAYERS+1) + (NUM_PLAYERS+3)*MARGIN),
            border_radius=CARD_CORNER_RADIUS + MARGIN
        )

        # Draw melds
        draw_melds(screen, game)

        # Draw banner to display current player
        pygame.draw.rect(
            screen,
            GREEN,
            pygame.Rect(PLAYER_CARDS_X, PLAYER_CARDS_Y + (CARD_HEIGHT+MARGIN)*game.whose_go, (CARD_WIDTH+MARGIN) * (NUM_CARDS_PER_PLAYER+1) + MARGIN, CARD_HEIGHT + 2*MARGIN),
            border_radius=CARD_CORNER_RADIUS + MARGIN
        )

        # Draw clickable items and save hitboxes
        hit_boxes : dict[str, pygame.Rect] = draw_all_clickable(screen, game, state)

        # Draw scores
        draw_scores(screen, game)

        # Draw info
        draw_info(screen)
        
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()
