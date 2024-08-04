import rummy
import neat
import gzip
import pickle
import random
import itertools
import time


GENOME_FILE_NAME = "ginny_genome.gn"
CONFIG_FILE_NAME = "ginny_config.txt"

class Ginny:
    def __init__(self, game:rummy.Game, player:int, genome:neat.DefaultGenome, config:neat.Config, human_delay:float=1) -> None:
        self.game = game
        self.player = player

        self.human_delay = human_delay

        self.genome = genome
        self.config = config

        # Spin up "brain"
        # self.nn = neat.nn.FeedForwardNetwork.create(genome, config)
    

    @staticmethod
    def get_genome(file_name:str=GENOME_FILE_NAME) -> neat.DefaultGenome:
        with gzip.open(file_name, "r") as f:
            # return pickle.load(f)
            pass
    
    @staticmethod
    def get_config(file_name:str=CONFIG_FILE_NAME) -> neat.Config:
        return neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                           neat.DefaultSpeciesSet, neat.DefaultStagnation,
                           file_name)
    
    def save_genome_to_file(self, file_name:str=GENOME_FILE_NAME):
        with gzip.open(file_name, "w") as f:
            pickle.dump(self.genome, f)

    def take_turn(self):
        time.sleep(self.human_delay)
        
        # Pick up a card
        self.game.draw(self.player, from_deck=False)

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
        
        # Discard a card
        self.game.discard(self.player, random.randint(0, len(self.game.get_hand())-1))
