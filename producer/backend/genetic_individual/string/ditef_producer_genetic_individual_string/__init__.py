import copy
import pathlib
import random
import string
import typing
import uuid

import ditef_producer_shared.genetic_individual
import ditef_router.api_client


class Individual(ditef_producer_shared.genetic_individual.AbstractIndividual):

    def individual_type(self) -> str:
        return 'string'

    @staticmethod
    def configuration_values() -> dict:
        return {
            'type': 'default',
            # string to strive for
            'target_string': "This is an example string.",
            # Pool for random string operations to choose characters from
            'character_pool': string.ascii_letters + " .",
            # Maximum amount of mutations
            'maximum_amount_of_mutations': 10,
        }

    @staticmethod
    def random(task_api_client: ditef_router.api_client.ApiClient, configuration: dict, state_path: pathlib.Path) -> 'Individual':
        '''Generates a new random individual'''

        target_length = len(configuration['target_string'])
        individual_id = str(uuid.uuid4())

        Individual.individuals[individual_id] = Individual(
            task_api_client,
            configuration,
            individual_id,
            [
                random.choice(configuration['character_pool'])
                for _ in range(random.randrange(target_length // 2, target_length * 2))
            ],
            'random',
            state_path/'individuals'/f'{individual_id}.json',
        )
        Individual.individuals[individual_id].write_to_file()

        return Individual.individuals[individual_id]

    @staticmethod
    def clone(parent: 'Individual', task_api_client: ditef_router.api_client.ApiClient, configuration: dict, creation_type: str, state_path: pathlib.Path) -> 'Individual':
        '''Creates a copy of a parent individual'''

        individual_id = str(uuid.uuid4())
        Individual.individuals[individual_id] = Individual(
            task_api_client,
            configuration,
            individual_id,
            copy.deepcopy(parent.genome),
            creation_type,
            state_path/'individuals'/f'{individual_id}.json',
        )
        Individual.individuals[individual_id].genealogy_parents = [parent.id]
        Individual.individuals[individual_id].write_to_file()
        parent.add_child(individual_id)

        return Individual.individuals[individual_id]

    @staticmethod
    def cross_over_one(parent_a: 'Individual', parent_b: 'Individual', task_api_client: ditef_router.api_client.ApiClient, configuration: dict, state_path: pathlib.Path) -> 'Individual':
        '''Creates one cross-overed individual from two parent individuals'''

        individual_id = str(uuid.uuid4())
        Individual.individuals[individual_id] = Individual(
            task_api_client,
            configuration,
            individual_id,
            [
                random.choice([gene_a, gene_b])
                for gene_a, gene_b in zip(parent_a.genome, parent_b.genome)
            ],
            'cross_over_one',
            state_path/'individuals'/f'{individual_id}.json',
        )
        Individual.individuals[individual_id].genealogy_parents = [
            parent_a.id,
            parent_b.id,
        ]
        Individual.individuals[individual_id].write_to_file()
        parent_a.add_child(individual_id)
        parent_b.add_child(individual_id)

        return Individual.individuals[individual_id]

    def mutate(self):
        for _ in range(random.randrange(self.configuration['maximum_amount_of_mutations'])):
            if random.choice([True] * 9 + [False]):
                # change character
                i = random.randrange(len(self.genome))
                self.genome[i] = random.choice(
                    self.configuration['character_pool'])
            else:
                if random.choice([True, False]) and len(self.genome) > 0:
                    # remove one character
                    i = random.randrange(len(self.genome))
                    del self.genome[i]
                else:
                    # insert new character
                    i = random.randrange(len(self.genome))
                    self.genome.insert(i, random.choice(
                        self.configuration['character_pool']))
        self.write_to_file()
        self.update_event.notify()

    async def evaluate(self):
        self.evaluation_result = await self.task_api_client.run(
            'ditef_worker_genetic_individual_string',
            payload={
                'genome': self.genome,
                'target_string': self.configuration['target_string'],
            },
        )
        self.write_to_file()
        self.update_event.notify()

    def fitness(self) -> typing.Optional[float]:
        try:
            return self.evaluation_result['correct_characters'] - abs(self.evaluation_result['length_difference']) * 2
        except TypeError:
            return None
