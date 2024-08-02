import random
import copy


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


class Game():
    def __init__(self, num_players:int=2, human_readable:bool=True, allow_rearranging:bool=True) -> None:
        # Assert that the number of players is valid
        assert num_players in NUM_CARDS.keys(), f"Invalid number of players, must be one of {list(NUM_CARDS.keys())}"

        # Assign self values
        self.num_players : int = num_players
        self.num_cards : int = NUM_CARDS[num_players]
        self.human_readable : bool = human_readable
        self.allow_rearranging : bool= allow_rearranging

        # Initialise scores
        self.scores = [0 for i in range(self.num_players)]

        # Shuffle the cards in the deck
        self.has_shuffled = False
        self.shuffle()
        # Deal cards
        # self.deal()

        self.game_ended = False


    def shuffle(self):
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
        assert self.has_shuffled, "Can't deal until you've shuffled"

        # Deal the cards
        self.hands = [self.deck[i*self.num_cards : (i+1)*self.num_cards] for i in range(0, self.num_players)]
        self.discard_pile = [self.deck[self.num_players * self.num_cards]]
        self.deck = self.deck[self.num_players * self.num_cards + 1:]

        # Sort the hands for easier legibility
        if self.human_readable:
            self.hands = [self.sort_cards(hand) for hand in self.hands]

        # Play has just started
        self.has_shuffled = False
        self.game_ended = False


    def draw(self, player:int, from_deck:bool=True) -> None:
        # Assert that the game hasn't ended
        assert not self.game_ended, "The game has ended; player cannot draw another card"
        # Assert that the correct player is playing
        assert player == self.whose_go, f"Player {player} can't draw a card because it's currently player {self.whose_go}'s turn"
        # Assert that the player hasn't drawn a card yet
        assert not self.has_drawn, "Player has already drawn a card this turn"

        # Draw card
        if from_deck:
            self.get_hand().append(self.deck.pop(0))

            # If the deck has run out of cards, shuffle the discard pile (excluding the top-most card)
            if len(self.deck) == 0:
                self.deck = self.discard_pile.copy()
                random.shuffle(self.deck)

                self.discard_pile = []
        else:
            self.get_hand().append(self.discard_pile.pop())

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
        self.discard_pile.append(self.get_hand().pop(card_index))
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
            assert 0 <= index < len(self.get_hand()), f"Not able to discard card at index {index}; only {len(self.get_hand())} cards in the hand"
        # Assert that there are no duplicates in the list
        assert len(card_indices) == len(set(card_indices)), "There are duplicates in the list"

        # Get card values from indices
        cards = [self.get_hand()[index] for index in card_indices]

        valid_meld = False

        # If it's a valid meld on its own, then lay it down
        valid, type = self.is_valid_meld(cards)
        if valid:
            if self.human_readable:
                self.sort_cards(cards, in_place=True, is_meld=True)
            self.melds.append(cards)
            self.meld_types.append(type)
            valid_meld = True
        
        else:
            # Otherwise check if it fits with any melds which have already been laid down
            for existing_meld in self.melds:
                valid, type = self.is_valid_meld(cards + existing_meld)
                if valid:
                    existing_meld += cards
                    if self.human_readable:
                        self.sort_cards(existing_meld, in_place=True, is_meld=True)
                    valid_meld = True
                    break
            
            # Check if melds can be rearranged to fit
            if not valid_meld and self.allow_rearranging:
                excess_cards = [len(meld)-3 for meld in self.melds]

                # Check there are even enough cards to allow rearrangement
                if sum(excess_cards) + len(cards) >= 3:
                    def select_card(melds:list[list[str]], index:int) -> str | None:
                        current_index = 0

                        for i, meld in enumerate(melds):
                            if len(meld) > 3:
                                old_current_index = current_index
                                if self.meld_types[i] == "run":
                                    current_index += 2
                                if self.meld_types[i] == "set":
                                    current_index += len(meld)
                                
                                if current_index > index:
                                    local_index = index - old_current_index
                                    if self.meld_types[i] == "run":
                                        self.sort_cards(meld, in_place=True, is_meld=True)
                                        return meld.pop(local_index - 1) # pops end, then beginning; local_index will only take values of 0 or 1
                                    if self.meld_types[i] == "set":
                                        return meld.pop(local_index)
                        
                        return None # If hasn't returned by this point, then there are no more cards available

                    indeces = [0, 0]
                    
                    check_finished = False
                    while not check_finished:
                        melds_temp = copy.deepcopy(self.melds)
                        proposed_meld = copy.deepcopy(cards)

                        run_out_of_cards = [False, False]

                        while len(proposed_meld) < 3 and not any(run_out_of_cards):
                            current_index = indeces[len(proposed_meld) - 1]

                            next_card = select_card(melds_temp, current_index)
                            if not next_card is None:
                                proposed_meld.append(next_card)
                            else:
                                run_out_of_cards[len(proposed_meld) - 1] = True
                        
                        if run_out_of_cards[0] and len(cards) == 1 or \
                           run_out_of_cards[1] and len(cards) == 2:
                            # Completely finished
                            check_finished = True
                        elif run_out_of_cards[1] and len(cards) == 1:
                            # Move carry - 2nd card has been exhaused, try a new first card
                            indeces[0] += 1
                            indeces[1] = 0
                        else:
                            # Successfully selected a potential meld
                            if self.is_valid_meld(proposed_meld)[0]:
                                # The meld actually works!
                                if self.human_readable:
                                    self.sort_cards(proposed_meld, in_place=True, is_meld=True)
                                melds_temp.append(proposed_meld)
                                self.melds = melds_temp

                                valid_meld = True

                                check_finished = True

                            indeces[1] += 1


        assert valid_meld, (f"Bad meld; {cards} is not itself a meld, nor does it fit with any of the other melds")

        # Remove from hand
        sorted_indices = sorted(card_indices, reverse=True)
        for index in sorted_indices:
            self.get_hand().pop(index)


    def sort_cards(self, cards:list[str], in_place:bool=False, is_meld=False) -> list[str] | None:
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
        
        else:
            number_order = NUMBERS


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

    def is_valid_meld(self, cards:list[str]) -> bool:
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
    
    def _end_turn(self) -> None:
        # Check if the player has cards left. If not, the game has ended
        if len(self.get_hand()) == 0:
            self._end_game()

        if not self.game_ended:
            # Change to next player's turn
            self.whose_go = (self.whose_go + 1) % self.num_players

    def _end_game(self) -> None:
        self.game_ended = True

        for player in range(self.num_players):
            self.scores[player] += self.get_score(self.get_hand(player))

        # print(f"Game has ended. Player {self.whose_go} has won. Scores on the doors: {self.scores}")

    def get_hand(self, player=None) -> list[str]:
        if player is None:
            player = self.whose_go

        return self.hands[player]

    def get_score(self, cards:list[str]) -> int:
        score = 0

        for card in cards:
            score += CARD_SCORES[NUMBERS.index(card[0])]

        return score


if __name__ == "__main__":
    game = Game(human_readable=True)

    # game.melds = [["Q♣", "K♣", "2♣", "5♣", "3♣", "4♣", "A♣"], ["A♥", "A♣", "A♦", "A♠"], ["2♥", "2♣", "2♦", "2♠"]]
    # game.meld_types = ["run", "set", "set"]
    # game.draw(game.whose_go)
    # game.hands[game.whose_go][0] = "K♠"
    # # game.hands[game.whose_go][1] = "2♠"
    # game.lay_meld(game.whose_go, [0])

    # print(game.sort_cards(["K♣", "2♣", "5♣", "3♣", "4♣", "Q♣", "A♣"], is_meld=True))

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
