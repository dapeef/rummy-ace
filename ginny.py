import rummy
import neat
import gzip
import pickle

class Ginny:
    def __init__(self, game:rummy.Game, player:int, genome:neat.DefaultGenome, config:neat.Config, human_readable:bool=True) -> None:
        self.game = game
        self.player = player

        self.human_readable = human_readable

        self.genome = genome
        self.config = config

        # Spin up "brain"
        self.nn = neat.nn.FeedForwardNetwork.create(genome, config)
    
    @staticmethod
    def get_genome_from_file(file_name:str) -> neat.DefaultGenome:
        with gzip.open(file_name, "r") as f:
            return pickle.load(f)
    
    @staticmethod
    def get_config_from_file(file_name:str) -> neat.Config:
        return neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                           neat.DefaultSpeciesSet, neat.DefaultStagnation,
                           file_name)
    
    def save_genome_to_file(self, file_name:str):
        with gzip.open(file_name, "w") as f:
            pickle.dump(self.genome, f)
