import rummy
import neat
import gzip
import pickle
import random
import itertools
import time
import numpy as np


GENOME_FILE_NAME = "ginny_genome.gn"
CONFIG_FILE_NAME = "ginny_config.txt"
NODE_NAMES = {
    -1: "Num turns",
    -2: "Min opps' cards",
    -3: "Deck size",
    -4: "Card score",
    -5: "Num cards to meld",
     0: "Paddle\naccel"
}

class Ginny:
    def __init__(self, game:rummy.Game, player:int, genome:neat.DefaultGenome, config:neat.Config, human_delay:float=1) -> None:
        self.game = game
        self.player = player

        self.human_delay = human_delay

        self.genome = genome
        self.config = config

        # Spin up "brain"
        self.nn = neat.nn.FeedForwardNetwork.create(genome, config)
    

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


    def check_melds(self, card:str):
        pass


    def get_card_value(self, card:str) -> float:
        """
        Values to be fed into the network:
        - Number of turns into the game
        - Min number of opponents' cards
        - Size of deck
        - Score of card
        # - Number of possible melds which this card facilitates
        - Number of available different possible cards which could complete a meld with this card
        - Number of cards this allows Ginny to meld immediately
        """

        # Number of turns into the game
        num_turns_taken = self.game.num_turns_taken

        # Min number of opponents' cards
        min_opponent_cards = min([len(hand) for hand in self.game.hands])

        # Size of deck
        deck_size = len(self.game.deck)

        # Score of card
        card_score = self.game.get_score([card])

        # # Number of possible melds which this card facilitates
        # num_melds = 

        # Number of available different possible cards which could complete a meld with this card
        num_friend_cards = 0

        # Evaluate network
        inputs = (
            num_turns_taken,
            min_opponent_cards,
            deck_size,
            card_score,
            num_friend_cards
        )
        card_value = self.nn.activate(inputs)

        return card_value

    def take_turn(self):
        time.sleep(self.human_delay)
        
        # Pick up a card
        # Get expectation of deck value
        expected_deck_value = np.mean([self.get_card_value(card) for card in self.game.get_knowledge_deck(self.player)])
        discard_value = self.get_card_value(self.game.discard_pile[-1])

        # Draw from whichever has the higher expected value
        self.game.draw(self.player, from_deck=expected_deck_value > discard_value)

        time.sleep(self.human_delay)

        # Meld if possible
        # TODO make this smarter
        search_complete = False
        while not search_complete:
            meld_success = False

            # Brute force try every combo
            positions = [i for i in range(len(self.game.get_hand()))]

            combos : list[list[int]]= []
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
        
        # Discard lowest value card
        index = np.argmin([self.get_card_value(card) for card in self.game.get_hand()])
        self.game.discard(self.player, index)
