import neat
import neat_utils
import gzip
import pickle
import ginny
import rummy
import os
from multiprocessing import Pool
from itertools import combinations
import time


MAX_TURNS_PER_GAME = 300
NUM_GAMES = 3
MAX_TURN_PENALTY = 20 * NUM_GAMES
PENALTY_PER_TURN = MAX_TURN_PENALTY / MAX_TURNS_PER_GAME / NUM_GAMES

NUM_WORKERS = 16
CHECKPOINT_FOLDER = "./checkpoints/"


def play_match(genomes:tuple[int, list[neat.DefaultGenome]], config:neat.Config, num_games:int) -> dict[str, int]:
    # Create game instantiation
    game = rummy.Game(len(genomes), human_readable=False)

    # Spin up Ginnys
    ginnys = [ginny.Ginny(game, i, genome[1], config, human_delay=0) for i, genome in enumerate(genomes)]

    # Total num turns
    num_turns = 0

    # Play games
    for _ in range(num_games):
        game.shuffle()
        game.deal()

        while not game.game_ended:
            if game.num_turns_taken >= MAX_TURNS_PER_GAME:
                game.end_game()
                break

            ginnys[game.whose_go].take_turn()

        # print(f"Game completed in {game.num_turns_taken} turns")

        num_turns += game.num_turns_taken

    # print(f"fitnesses: score: {-game.scores[0]}, {-game.scores[1]} length: {-PENALTY_PER_TURN * num_turns:.2f}")

    fitnesses : dict[str, int] = {
        genome[0]: -game.scores[i] - PENALTY_PER_TURN * num_turns
        for i, genome in enumerate(genomes)
    }
    # print(f"Num turns: {num_turns}, scores: {game.scores}, length penalty: {PENALTY_PER_TURN * num_turns :.2f}")
    
    return fitnesses, num_turns


def eval_genomes(genomes:list[tuple[int,neat.DefaultGenome]], config:neat.Config):
    # Get game pairings
    genome_groups = list(combinations(genomes, 2))

    # Evaluate pairs using multiprocessing pool
    start_time = time.time()
    with Pool(NUM_WORKERS) as pool:
        results = pool.starmap(play_match, [(genome_group, config, NUM_GAMES) for genome_group in genome_groups])
    time_diff = time.time() - start_time

    # Reset fitness scores -- TODO is this necessary?
    for id, genome in genomes:
        genome.fitness = 0

    # Tell genomes their fitness
    for result in results:
        for id, fitness in result[0].items():
            for genome_id, genome in genomes:
                if genome_id == id:
                    genome.fitness += fitness
        
    # Print diagnostics
    print(f"\nNum matches: {len(genome_groups)}",
          f"Time: {time_diff:.2f} s",
          f"Av game length: {sum([result[1] for result in results]) / len(genome_groups) / NUM_GAMES :.1f} turns",
          f"Time per turn: {time_diff / sum([result[1] for result in results]) * 1e6 :.1f} µs",
          sep=" --- ",
          end="\n\n")
    
    pass


    # for i in range(len(genomes)):
    #     for j in range(i + 1, len(genomes)):
    #         print(f"\nPlaying games between genomes {i} and {j}")
    #         fitness = play_match([genomes[i], genomes[j]], config, NUM_GAMES)

    #         genomes[i][1].fitness -= game.scores[0] + PENALTY_PER_TURN * num_turns
    #         genomes[j][1].fitness -= game.scores[1] + PENALTY_PER_TURN * num_turns

    #         print(f"{i} vs {j} fitnesses: score: {-game.scores[0]}, {-game.scores[1]} length: {-PENALTY_PER_TURN * num_turns:.2f}")

                  
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
    winner = p.run(eval_genomes, 1000)
    
    # Save best genome
    with gzip.open(winner_file, "w") as f:
        pickle.dump(winner, f)

    # Display the winning genome.
    print('\n--- Best genome: ---\n{!s}'.format(winner))


if __name__ == "__main__":
    run(resume_training=False)