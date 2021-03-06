import string

def run(payload):
    genome = payload['genome']
    target_string = payload['target_string']

    correct_characters = sum(a == b for a, b in zip(genome, target_string))
    length_difference = len(genome) - len(target_string)

    return {
        'correct_characters': correct_characters,
        'length_difference': length_difference,
    }
