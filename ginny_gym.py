import neat
import neat_utils
import gzip
import pickle
import ginny
import rummy
import os


PENALTY_PER_TURN = 0.04

CHECKPOINT_FOLDER = "./checkpoints/"


def play_games(genomes:list[neat.DefaultGenome], config:neat.Config, num_games:int):
    # Create game instantiation
    game = rummy.Game(len(genomes), human_readable=False)

    # Spin up Ginnys
    ginnys = [ginny.Ginny(game, i, genome, config, human_delay=0) for i, genome in enumerate(genomes)]

    # Total num turns
    num_turns = 0

    # Play games
    for _ in range(num_games):
        game.shuffle()
        game.deal()

        while not game.game_ended:
            if game.num_turns_taken >= 500:
                game.end_game()
                break

            ginnys[game.whose_go].take_turn()

        print(f"Game completed in {game.num_turns_taken} turns")

        num_turns += game.num_turns_taken
    
    return game, num_turns


def eval_genomes(genomes:list[tuple[int,neat.DefaultGenome]], config:neat.Config):
    num_games = 5

    for id, genome in genomes:
        genome.fitness = 0
        
    for i in range(len(genomes)):
        for j in range(i + 1, len(genomes)):
            print(f"Playing games between genomes {i} and {j}")
            game, num_turns = play_games([genomes[i][1], genomes[j][1]], config, num_games=num_games)

            genomes[i][1].fitness -= game.scores[0] + PENALTY_PER_TURN * num_turns
            genomes[j][1].fitness -= game.scores[1] + PENALTY_PER_TURN * num_turns

            print(f"fitnesses: score: {-game.scores[0]}, {-game.scores[1]} length: {-PENALTY_PER_TURN * num_turns:.2f}")

                  
def run(winner_file:str=ginny.GENOME_FILE_NAME, config_file:str=ginny.CONFIG_FILE_NAME, resume_training:bool=False):
    # Load configuration
    config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                         neat.DefaultSpeciesSet, neat.DefaultStagnation,
                         config_file)
    
    # Create the overarching population object
    if resume_training:
        p = neat.Checkpointer.restore_checkpoint(os.path.join(CHECKPOINT_FOLDER, os.listdir(CHECKPOINT_FOLDER)[-1]))
    else:
        p = neat.Population(config)

    # Add a stdout reporter to show progress in the terminal.
    p.add_reporter(neat.StdOutReporter(False))
    p.add_reporter(neat_utils.DrawNetReporter(ginny.NODE_NAMES))
    p.add_reporter(neat_utils.SaveBestGenomeReporter(ginny.GENOME_FILE_NAME))
    stats = neat.StatisticsReporter()
    p.add_reporter(stats)
    p.add_reporter(neat_utils.StatsGraphReporter(stats))
    p.add_reporter(neat.Checkpointer(1, filename_prefix=CHECKPOINT_FOLDER))

    # Train the network
    winner = p.run(eval_genomes, 100)
    
    # Save best genome
    with gzip.open(winner_file, "w") as f:
        pickle.dump(winner, f)

    # Display the winning genome.
    print('\n--- Best genome: ---\n{!s}'.format(winner))


if __name__ == "__main__":
    run(resume_training=True)