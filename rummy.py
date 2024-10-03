import random
import copy
from dataclasses import dataclass, field


NUMBERS : str = "A234567890JQK"
DOUBLED_NUMBERS : str = NUMBERS + NUMBERS
CARD_SCORES : list[int] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10]
SUITS : str = "♣♦♥♠"
DECK : list[str] = [f"{i}{j}" for j in SUITS for i in NUMBERS]
NUM_CARDS : dict[int, int] = {
    2 : 10,
    3 : 7,
    4 : 7,
    5 : 6,
    6 : 6
}


@dataclass
class CardKnowledge:
    # Number of possible melds which this card facilitates
    num_melds : int = 0
    # Number of available different possible cards which could complete a meld with this card
    num_friend_cards : int = 0
    # Number of cards this allows the player to meld immediately
    num_immediate_meld_cards : int = 0

@dataclass
class Knowledge:
    deck : list[str]
    hands : list[list[str]]
    partial_melds : list[tuple[list[str]]] = field(default_factory=list) # [(partial meld, cards which can complete meld)]


class BadMeldError(Exception):
    def __init__(self, message):
        # Call the base class constructor with the parameters it needs
        super().__init__(message)


class Game():
    def __init__(self, num_players:int=2, human_readable:bool=True, allow_rearranging:bool=True) -> None:
        # Assert that the number of players is valid
        assert num_players in NUM_CARDS.keys(), f"Invalid number of players, must be one of {list(NUM_CARDS.keys())}"

        # Assign self values
        self.num_players : int = num_players
        self.num_cards : int = NUM_CARDS[num_players]
        self.human_readable : bool = human_readable
        self.allow_rearranging : bool = allow_rearranging

        # Initialise scores
        self.scores : list[int] = [0 for i in range(self.num_players)]

        # Shuffle the cards in the deck
        self.has_shuffled = False

        # self.game_ended = True
        # self.shuffle()
        # Deal cards
        # self.deal()

        self.game_ended = True


    def shuffle(self):
        # Make sure game has ended before restarting
        assert self.game_ended, "Can't restart game now; old game hasn't ended yet"

        # Create shuffled deck
        self.deck : list[str] = DECK.copy()
        random.shuffle(self.deck)

        self.discard_pile : list[str] = []
        self.hands : list[list[str]] = [[] for _ in range(self.num_players)]
        self.melds : list[list[str]] = []
        self.meld_types : list[str] = []

        # Randomise which player starts
        self.whose_go : int = random.randint(0, self.num_players - 1)

        self.has_shuffled = True
        self.has_drawn = False

    def deal(self):
        # Assert that the deck has been shuffled before dealing
        assert self.has_shuffled, "Can't deal until you've shuffled"

        # Deal the cards
        self.hands = [self.deck[i*self.num_cards : (i+1)*self.num_cards] for i in range(0, self.num_players)]
        self.discard_pile = [self.deck[self.num_players * self.num_cards]]
        self.deck = self.deck[self.num_players * self.num_cards + 1:]
        
        # Sort the hands for easier legibility
        if self.human_readable:
            self.hands = [self.sort_cards(hand) for hand in self.hands]

        # Initialise players' knowledge of where cards are
        self.player_knowledges : list[Knowledge] = [Knowledge(
            DECK.copy(),
            [[] for _ in range(self.num_players)]
        ) for _ in range(self.num_players)]

        for player in range(self.num_players):
            # Remove discard card and player's hand from knowledge of the deck
            self.player_knowledges[player].deck.remove(self.discard_pile[0])
            for card in self.get_hand(player):
                self.player_knowledges[player].deck.remove(card)
            
            # Copy own cards to own knowledge
            self.player_knowledges[player].hands[player] = self.get_hand(player).copy()

            # Initialise knowledge of own hand
            # Find partial melds
            for ind, i in enumerate(self.get_hand(player)):
                potential_friends = self.get_possible_meld_friends(i)

                for jnd, j in enumerate(self.get_hand(player)[ind+1:], start=ind+1):
                    if j in potential_friends.keys():
                        self.player_knowledges[player].partial_melds.append(([i, j], potential_friends[j]))
            # # Based on partial melds, update card scores
            # self.update_card_scores(player)

        # Play has just started
        self.has_shuffled = False
        self.game_ended = False
        self.num_turns_taken = 0


    def draw(self, player:int, from_deck:bool=True) -> None:
        # Assert that the game hasn't ended
        assert not self.game_ended, "The game has ended; player cannot draw another card"
        # Assert that the correct player is playing
        assert player == self.whose_go, f"Player {player} can't draw a card because it's currently player {self.whose_go}'s turn"
        # Assert that the player hasn't drawn a card yet
        assert not self.has_drawn, "Player has already drawn a card this turn"

        # Draw card
        if from_deck:
            drawn_card = self.deck.pop(0)
            self.get_hand().append(drawn_card)

            self.player_knowledges[player].deck.remove(drawn_card)

            # If the deck has run out of cards, shuffle the discard pile (excluding the top-most card)
            if len(self.deck) == 0:
                self.deck = self.discard_pile.copy()
                random.shuffle(self.deck)

                self.discard_pile = []
                
                # Update card counting knowledge
                for card in range(self.num_players):
                    self.player_knowledges[card].deck = self.deck.copy()

        else:
            drawn_card = self.discard_pile.pop()
            self.get_hand().append(drawn_card)

            # Update card counting
            for i in range(self.num_players):
                self.player_knowledges[i].hands[player].append(drawn_card)

        # Update knowledge
        # Add any new partial melds
        potential_friends = self.get_possible_meld_friends(self.get_hand(player)[-1])
        for card in self.get_hand(player)[:-1]:
            if card in potential_friends.keys():
                self.player_knowledges[player].partial_melds.append(([self.get_hand(player)[-1], card], potential_friends[card]))
        # # Based on partial melds, update card scores
        # self.update_card_scores(player)

        # Sort the hands for easier legibility
        if self.human_readable:
            self.sort_cards(self.get_hand(), in_place=True)

        self.has_drawn = True

    def discard(self, player:int, card_index:int) -> None:
        # Assert that the game hasn't ended
        assert not self.game_ended, "The game has ended; player cannot draw another card"
        # Assert that the correct player is playing
        assert player == self.whose_go, f"Player {player} can't draw a card because it's currently player {self.whose_go}'s turn"
        # Check that player has drawn a card before discarding
        assert self.has_drawn, "Player hasn't drawn a card yet"
        # Check that the card index is within the number of cards in the hand
        assert 0 <= card_index < len(self.get_hand()), f"Not able to discard card at index {card_index}; only {len(self.get_hand())} cards in the hand"

        # Discard card
        discard_card = self.get_hand().pop(card_index)
        self.discard_pile.append(discard_card)

        # Update card counting
        for i in range(self.num_players):
            try:
                self.player_knowledges[i].hands[player].remove(discard_card)
            except ValueError:
                pass
            try:
                self.player_knowledges[i].deck.remove(discard_card)
            except ValueError:
                pass

        # Update knowledge
        # Remove any partial melds which had the melded cards in
        for ind, meld in reversed(list(enumerate(self.player_knowledges[player].partial_melds))):
            if discard_card in meld[0]:
                self.player_knowledges[player].partial_melds.pop(ind)
        # # Based on partial melds, update card scores
        # self.update_card_scores(player)

        self.has_drawn = False

        # End turn
        self._end_turn()

    def lay_meld(self, player:int, card_indices:list[int]) -> None:
        # Assert that the game hasn't ended
        assert not self.game_ended, "The game has ended; player cannot draw another card"
        # Assert that the correct player is playing
        assert player == self.whose_go, f"Player {player} can't draw a card because it's currently player {self.whose_go}'s turn"
        # Assert that player has drawn a card before laying down a meld
        assert self.has_drawn, "Player hasn't drawn a card yet"
        # Assert that there'll be at least one card left in the player's hand after the meld is laid
        assert len(self.get_hand()) > len(card_indices), "Can't play this meld; player must have a card to discard at the end of the turn"
        # Assert that all values of list are in range
        for index in card_indices:
            assert 0 <= index < len(self.get_hand()), f"Not able to meld card at index {index}; only {len(self.get_hand())} cards in the hand"
        # Assert that there are no duplicates in the list
        assert len(card_indices) == len(set(card_indices)), "There are duplicates in the list"

        # Get card values from indices
        cards = [self.get_hand()[index] for index in card_indices]

        valid_meld = False

        # If it's a valid meld on its own, then lay it down
        valid, meld_type = self.is_valid_meld(cards)
        if valid:
            if self.human_readable:
                self.sort_cards(cards, in_place=True, is_meld=True)
            self.melds.append(cards)
            self.meld_types.append(meld_type)
            valid_meld = True
        
        else:
            # Otherwise check if it fits with any melds which have already been laid down
            for existing_meld in self.melds:
                valid, meld_type = self.is_valid_meld(cards + existing_meld)
                if valid:
                    existing_meld += cards
                    if self.human_readable:
                        self.sort_cards(existing_meld, in_place=True, is_meld=True)
                    valid_meld = True
                    break
            
            # Check if melds can be rearranged to fit
            if not valid_meld and self.allow_rearranging and len(cards) < 3:
                excess_cards = [len(meld)-3 for meld in self.melds]

                # Check there are even enough cards to allow rearrangement
                if sum(excess_cards) + len(cards) >= 3:
                    meld, meld_locations, meld_type = self.try_rearrange_meld(cards, self.melds, self.meld_types)

                    if not meld is None:
                        meld_locations.sort(key=lambda x: x[0], reverse=True)

                        for location in meld_locations:
                            self.melds[location[0]].pop(location[1])

                            # If stealing the middle card of a meld, then split into two new melds
                            if not location[1] == 0 and not location[1] == len(self.melds[location[0]]) and self.meld_types[location[0]] == "run":
                                left = self.melds[location[0]][:location[1]]
                                right = self.melds[location[0]][location[1]:]

                                self.melds[location[0]] = left
                                self.melds.insert(location[0] + 1, right)
                                self.meld_types.insert(location[0] + 1, "run")
                        
                        if self.human_readable:
                            self.sort_cards(meld, in_place=True, is_meld=True)

                        self.melds.append(meld)
                        self.meld_types.append(meld_type)

                        valid_meld = True

        if not valid_meld:
            raise BadMeldError(f"Bad meld; {cards} is not itself a meld, nor does it fit with any of the other melds")
        

        # --- Meld has been verified as good ---
               
        # Remove from hand
        sorted_indices = sorted(card_indices, reverse=True)
        for index in sorted_indices:
            self.get_hand().pop(index)

        # Update card counting
        for i in range(self.num_players):
            for card in cards:
                try:
                    self.player_knowledges[i].hands[player].remove(card)
                except ValueError:
                    pass

                try:
                    self.player_knowledges[i].deck.remove(card)
                except ValueError:
                    pass

        # Update knowledge
        # Remove any partial melds which had the melded cards in
        for ind, meld in reversed(list(enumerate(self.player_knowledges[player].partial_melds))):
            if any(item in meld[0] for item in cards):
                self.player_knowledges[player].partial_melds.pop(ind)
        # # Based on partial melds, update card scores
        # self.update_card_scores(player)


    @staticmethod
    def sort_cards(cards:list[str], in_place:bool=False, is_meld=False) -> list[str] | None:
        number_order = NUMBERS

        # Handle KA2 melds
        if is_meld:
            numbers_only = [card[0] for card in cards]
            numbers_present = [num in numbers_only for num in NUMBERS]
            numbers_present_doubled = numbers_present * 2

            for i in range(len(numbers_present_doubled) - 1):
                if numbers_present_doubled[i] == False and numbers_present_doubled[i+1] == True:
                    # The start of the run is at i+1
                    number_order = DOUBLED_NUMBERS[i+1 : i+1+len(NUMBERS)]
                    break
            

        if in_place:
            # Sort by suit
            cards.sort(key=lambda x: SUITS.index(x[1]))
            # Sort by number
            cards.sort(key=lambda x: number_order.index(x[0]))

        else:
            # Sort by suit
            cards = sorted(cards, key=lambda x: SUITS.index(x[1]))
            # Sort by number
            cards = sorted(cards, key=lambda x: number_order.index(x[0]))

            return cards

    @staticmethod
    def is_valid_meld(cards:list[str]) -> bool:
        # Check that there are no duplicates in the list
        assert len(cards) == len(set(cards)), "There are duplicates in the list"
        
        # Check if the meld is a set
        def is_set():
            # Check number is the same for all cards
            return all([cards[0][0] == cards[i][0] for i in range(1, len(cards))])

        # Check if the meld is a run
        def is_run():
            # Check suit is the same for all cards
            if all([cards[0][1] == cards[i][1] for i in range(1, len(cards))]):
                card_numbers = set([i[0] for i in cards])
                
                for i in range(len(NUMBERS)):
                    if card_numbers == set(DOUBLED_NUMBERS[i : i+len(cards)]):
                        return True
                
                return False
            
            else:
                return False

        # Check meld is long enough
        if len(cards) < 3:
            return False, None

        # return any([is_set(), is_run()])
    
        if is_set():
            return True, "set"
        if is_run():
            return True, "run"
        else:
            return False, None
    
    @staticmethod
    def get_possible_meld_friends(card:str) -> dict[str, list[str]]:

        number_index : int = NUMBERS.index(card[0])
        len_nums : int = len(NUMBERS)
        
        possible_friends : dict[str, list[str]] = {}
        
        def get_number_diff_card(difference : int):
            return NUMBERS[(number_index + difference) % len_nums] + card[1]
        possible_friends[get_number_diff_card(-2)] = [get_number_diff_card(-1)]
        possible_friends[get_number_diff_card(-1)] = [get_number_diff_card(-2), get_number_diff_card(1)]
        possible_friends[get_number_diff_card(1)] = [get_number_diff_card(-1), get_number_diff_card(2)]
        possible_friends[get_number_diff_card(2)] = [get_number_diff_card(1)]
        

        for suit in SUITS:
            if suit != card[1]:
                possible_friends[card[0] + suit] = []

                for suit_2 in SUITS:
                    if suit_2 != card[1] and suit_2 != suit:
                        possible_friends[card[0] + suit].append(card[0] + suit_2)
            
        return possible_friends


    def _end_turn(self) -> None:
        # Check if the player has cards left. If not, the game has ended
        if len(self.get_hand()) == 0:
            self.end_game()

        if not self.game_ended:
            # Change to next player's turn
            self.whose_go = (self.whose_go + 1) % self.num_players

            self.num_turns_taken += 1

    def end_game(self) -> None:
        self.game_ended = True

        for player in range(self.num_players):
            self.scores[player] += self.get_score(self.get_hand(player))

        # print(f"Game has ended. Player {self.whose_go} has won. Scores on the doors: {self.scores}")


    def get_hand(self, player=None) -> list[str]:
        if player is None:
            player = self.whose_go

        return self.hands[player]

    @staticmethod
    def get_score(cards:list[str]) -> int:
        score = 0

        for card in cards:
            score += CARD_SCORES[NUMBERS.index(card[0])]

        return score
    
    def get_knowledge(self, player:int) -> Knowledge:
        # Assert that the correct player is playing
        assert player == self.whose_go, f"Player {player} can't access knowledge; it's not their go"
        
        self.player_knowledges[player].hands[player] = self.get_hand(player).copy()

        return self.player_knowledges[player]


    def select_loose_meld_card(self, melds:list[list[str]], meld_types:list[str], index:int) -> str | None:
        current_index = 0

        for i, meld in enumerate(melds):
            if len(meld) > 3:
                old_current_index = current_index
                if meld_types[i] == "run":
                    current_index += 2
                if meld_types[i] == "set":
                    current_index += len(meld)
                
                if current_index > index:
                    local_index = index - old_current_index
                    if meld_types[i] == "run":
                        self.sort_cards(meld, in_place=True, is_meld=True)
                        return meld.pop(local_index - 1) # pops end, then beginning; local_index will only take values of 0 or 1
                    if meld_types[i] == "set":
                        return meld.pop(local_index)
        
        return None # If hasn't returned by this point, then there are no more cards available

    def select_loose_meld_cards(self, melds:list[list[str]], meld_types:list[str]) -> str | None:
        loose_cards : list[str] = []
        loose_card_locations : list[tuple[int]] = []

        for i, meld in enumerate(melds):
            if len(meld) > 3:
                if meld_types[i] == "run":
                    self.sort_cards(meld, in_place=True, is_meld=True)

                    loose_cards.append(meld[0])
                    loose_cards.append(meld[-1])

                    loose_card_locations.append((i, 0))
                    loose_card_locations.append((i, -1))

                    if len(meld) > 6:
                        for j in range(3, len(meld) - 3):
                            loose_cards.append(meld[j])
                            loose_card_locations.append((i, j))
                if meld_types[i] == "set":
                    for k, card in enumerate(meld):
                        loose_cards.append(card)
                        loose_card_locations.append((i, k))
        
        return loose_cards, loose_card_locations

    def try_rearrange_meld(self, proposed_meld:list[str], melds:list[list[str]], meld_types:list[str]):
        assert len(proposed_meld) in [1, 2], f"Bad proposed meld length of {len(proposed_meld)}. Must be either 1 or 2"

        # TODO possibly make this a recursive function? Or use a function to prevent repeating code

        if len(proposed_meld) == 1:
            loose_cards_1, loose_card_locations_1 = self.select_loose_meld_cards(melds, meld_types)

            for card_1, location_1 in zip(loose_cards_1, loose_card_locations_1):
                temp_melds = copy.deepcopy(melds)
                temp_melds[location_1[0]].pop(location_1[1])

                loose_cards_2, loose_card_locations_2 = self.select_loose_meld_cards(temp_melds, meld_types)

                # TODO perhaps don't need to search with 2 cards from the same meld; this would just add the card to that meld

                for card_2, location_2 in zip(loose_cards_2, loose_card_locations_2):
                    meld_attempt = proposed_meld + [card_1, card_2]

                    meld_validity, meld_type = self.is_valid_meld(meld_attempt)

                    if meld_validity:
                        meld_location = [location_1, location_2]

                        return meld_attempt, meld_location, meld_type
            
        elif len(proposed_meld) == 2:
            if proposed_meld[0][0] == proposed_meld[1][0] or \
               proposed_meld[0][1] == proposed_meld[1][1]:
                loose_cards_1, loose_card_locations_1 = self.select_loose_meld_cards(melds, meld_types)

                for card_1, location_1 in zip(loose_cards_1, loose_card_locations_1):
                    meld_attempt = proposed_meld + [card_1]

                    meld_validity, meld_type = self.is_valid_meld(meld_attempt)

                    if meld_validity:
                        meld_location = [location_1]

                        return meld_attempt, meld_location, meld_type

        return None, [], ""


if __name__ == "__main__":
    game = Game(human_readable=True)

    game.get_possible_meld_friends("A♥")

    game.shuffle()
    game.deal()

    game.melds = [["Q♣", "K♣", "2♣", "5♣", "3♣", "4♣", "A♣"], ["A♥", "A♣", "A♦", "A♠"]]#, ["2♥", "2♣", "2♦", "2♠"]]
    game.meld_types = ["run", "set"]#, "set"]
    # print(game.select_loose_meld_cards(game.melds, game.meld_types))
    game.draw(game.whose_go)
    game.hands[game.whose_go][0] = "K♠"
    game.hands[game.whose_go][1] = "2♠"
    game.lay_meld(game.whose_go, [0, 1])
    game.discard(game.whose_go, 0)

    # game.draw(0)
    # game.lay_meld(0, [6, 7, 8])
    # game.discard(0, 7)

    # game.draw(1)
    # game.lay_meld(1, [0, 1, 2])
    # game.discard(1, 0)

    # game.draw(0)
    # game.lay_meld(0, [6])
    # game.discard(0, 6)

    # game.draw(1)
    # game.lay_meld(1, [2])
    # game.discard(1, 3)

    # game.draw(0)
    # game.lay_meld(0, [0, 1, 2, 3, 4, 5])
    # game.discard(0, 0)

    pass
