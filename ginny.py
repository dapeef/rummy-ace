import rummy
import neat
import gzip
import pickle
import random
import itertools
import time
import numpy as np
from dataclasses import dataclass


GENOME_FILE_NAME = "ginny_genome.gn"
CONFIG_FILE_NAME = "ginny_config.txt"
NODE_NAMES = {
    -1: "Num turns",
    -2: "Min opps' cards",
    -3: "Deck size",
    -4: "Card score",
    -5: "Num melds",
    -6: "Num cards to meld",
    -7: "Num meldable now",
    -8: "Prox to hand",
     0: "Card\nvalue"
}


@dataclass
class CardKnowledge:
    # Number of possible melds which this card facilitates
    num_melds : int = 0
    # Number of available different possible cards which could complete a meld with this card
    num_friend_cards : int = 0
    # Number of cards this allows the player to meld immediately
    num_immediate_meld_cards : int = 0
    # Proximity to an existing card in the hand (eg 9♣ would have a proximity score of 2 from 9♦. A♣ would be 1 to 3♣)
    proximity : int = 0


class Ginny:
    def __init__(self, game:rummy.Game, player:int, genome:neat.DefaultGenome, config:neat.Config, human_delay:float=1) -> None:
        self.game = game
        self.player = player

        self.human_delay = human_delay

        self.genome = genome
        self.config = config

        # Spin up "brain"
        self.nn = neat.nn.FeedForwardNetwork.create(genome, config)

        # Initialise card value caching
        self.card_values : dict[str, CardKnowledge] = {card: CardKnowledge() for card in rummy.DECK}
    

    @staticmethod
    def get_genome(file_name:str=GENOME_FILE_NAME) -> neat.DefaultGenome:
        with gzip.open(file_name, "r") as f:
            return pickle.load(f)
    
    @staticmethod
    def get_config(file_name:str=CONFIG_FILE_NAME) -> neat.Config:
        return neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                           neat.DefaultSpeciesSet, neat.DefaultStagnation,
                           file_name)
    
    def save_genome_to_file(self, file_name:str=GENOME_FILE_NAME) -> None:
        with gzip.open(file_name, "w") as f:
            pickle.dump(self.genome, f)


    def update_card_scores(self, include_discard=False) -> None:
        # Reset values
        for card in rummy.DECK:
            self.card_values[card] = CardKnowledge()

        # Check whether this card can be added directly to a meld
        for meld, meld_type in zip(self.game.melds, self.game.meld_types):
            if meld_type == "set" and len(meld) == 3:
                remaining_suit = (set(rummy.SUITS) - set([card[1] for card in meld])).pop()
                self.card_values[meld[0][0] + remaining_suit].num_immediate_meld_cards = 1
            if meld_type == "run":
                left_number = rummy.NUMBERS[(rummy.NUMBERS.index(meld[0][0]) - 1) % len(rummy.NUMBERS)]
                right_number = rummy.NUMBERS[(rummy.NUMBERS.index(meld[-1][0]) + 1) % len(rummy.NUMBERS)]
                for number in [left_number, right_number]:
                    self.card_values[number + meld[0][1]].num_immediate_meld_cards = 1
               
        # Get list of cards which are impossible to be drawn (ie NOT in deck, or in other people's hands. Equiv to in melds, discard, or own hand)
        impossible_friends = [card for meld in self.game.melds for card in meld] + self.game.get_hand(self.player).copy()
        if not include_discard:
            impossible_friends += self.game.discard_pile.copy()

        # Compute values
        for partial_meld in self.game.get_knowledge(self.player).partial_melds:
            possible_meld_cards = len(partial_meld[1])

            for card in partial_meld[1]:
                if card in impossible_friends:
                    possible_meld_cards -= 1

            if possible_meld_cards > 0:
                for card in partial_meld[0]:
                    self.card_values[card].num_melds += 1
                    self.card_values[card].num_friend_cards += possible_meld_cards
                    
                for card in partial_meld[1]:
                    self.card_values[card].num_immediate_meld_cards = 3

        # Update proximity score for cards in current hand
        for card in self.game.get_hand(self.player):
            # Runs
            number_index : int = rummy.NUMBERS.index(card[0])
            len_nums : int = len(rummy.NUMBERS)
            def get_number_diff_card(difference : int):
                return rummy.NUMBERS[(number_index + difference) % len_nums] + card[1]
            self.card_values[get_number_diff_card(-2)].proximity += 1
            self.card_values[get_number_diff_card(-1)].proximity += 2
            self.card_values[get_number_diff_card(1)].proximity += 2
            self.card_values[get_number_diff_card(2)].proximity += 1
            # Sets
            for suit in rummy.SUITS:
                if suit != card[1]:
                    self.card_values[card[0] + suit].proximity += 2
        
        # TODO take into account currently melded cards

    def get_card_value(self, card:str) -> float:
        """
        Values to be fed into the network:
        - Number of turns into the game
        - Min number of opponents' cards
        - Size of deck
        - Score of card
        - Number of possible melds which this card facilitates
        - Number of available different possible cards which could complete a meld with this card
        - Number of cards this allows Ginny to meld immediately
        - Proximity from one of the cards in the hand already
        """

        # Number of turns into the game
        num_turns_taken = self.game.num_turns_taken

        # Min number of opponents' cards
        min_opponent_cards = min([len(hand) for player, hand in enumerate(self.game.hands) if player != self.player])

        # Size of deck
        deck_size = len(self.game.deck)

        # Score of card
        card_score = self.game.get_score([card])

        # Number of possible melds which this card facilitates
        num_melds = self.card_values[card].num_melds

        # Number of available different possible cards which could complete a meld with this card
        num_friend_cards = self.card_values[card].num_friend_cards

        # Number of cards this allows Ginny to meld immediately
        num_immediate_meld_cards = self.card_values[card].num_immediate_meld_cards

        # Proximity to existing cards in the hand
        proximity = self.card_values[card].proximity

        # Evaluate network
        inputs = (
            num_turns_taken,
            min_opponent_cards,
            deck_size,
            card_score,
            num_melds,
            num_friend_cards,
            num_immediate_meld_cards,
            proximity
        )
        card_value = self.nn.activate(inputs)

        return card_value[0]


    def take_turn(self):
        time.sleep(self.human_delay)

        self.update_card_scores(include_discard=True)
        
        # Pick up a card
        if self.card_values[self.game.discard_pile[-1]].num_immediate_meld_cards > 0:
            from_deck = False
        
        else:
            min_hand_value = min([self.get_card_value(card) for card in self.game.get_hand(self.player)])
            discard_value = self.get_card_value(self.game.discard_pile[-1])

            if min_hand_value < discard_value:
                # Get expectation of deck value
                expected_deck_value = np.mean([self.get_card_value(card) for card in self.game.get_knowledge(self.player).deck])

                from_deck = expected_deck_value > discard_value
            
            else:
                from_deck = True

        # Draw from whichever has the higher expected value
        self.game.draw(self.player, from_deck=from_deck)

        time.sleep(self.human_delay)

        self.update_card_scores()

        # Meld if possible
        # TODO make this smarter
        search_complete = False
        while not search_complete:
            meld_success = False

            # Brute force try every combo
            combos : list[list[int]] = []
            for i in range(1, min(len(self.game.get_hand()), 4)):
                combos += list(itertools.combinations(range(len(self.game.get_hand())), i))

            while len(combos) > 0:
                success = True

                try:
                    self.game.lay_meld(self.player, combos.pop())
                except rummy.BadMeldError as e:
                    success = False
                
                if success:
                    meld_success = True
                    time.sleep(self.human_delay)
                    break

            if not meld_success:
                search_complete = True

        self.update_card_scores()
        
        # Discard lowest value card
        hand_values = [self.get_card_value(card) for card in self.game.get_hand()]
        min_hand_value = np.min(hand_values)
        min_indices = np.where(hand_values == min_hand_value)[0]
        
        # If there's a draw in value, discard the card which has the highest score
        if len(min_indices) == 0:
            index = min_indices[0]
        else:
            max_card_score = 0
            for i in min_indices:
                current_card_score = rummy.Game.get_score([self.game.get_hand()[i]])
                if current_card_score > max_card_score:
                    max_card_score = current_card_score
                    index = i
            
        self.game.discard(self.player, index)
