import aiohttp.web
import asyncio
import copy
import datetime
import json
from pathlib import Path
import random
import string
import textwrap
import typing
import uuid

import ditef_producer_shared.event
import ditef_producer_shared.json
from ditef_producer_shared.individual import AbstractIndividual
import ditef_router.api_client


class Individual(AbstractIndividual):

    def individual_type(self) -> str:
        return('string')

    @staticmethod
    def configuration_values() -> dict:
        return {
            'target_string': {
                'help': 'string to strive for',
                'default': "This is an example string.",
            },
            'character_pool': {
                'help': 'Pool for random string operations to choose characters from',
                'default': string.ascii_letters + " .",
            },
            'maximum_amount_of_mutations': {
                'help': 'Maximum amount of mutations',
                'default': 10,
            },
        }

    @staticmethod
    def load_individual_to_static_dict(individual_file: Path, task_api_client: ditef_router.api_client.ApiClient, configuration):
        with open(individual_file, 'r') as f:
            individual_data = json.loads(f.read())

        Individual.individuals[individual_file.stem] = Individual(task_api_client,
            configuration,
            individual_file.stem,
            individual_data['genome'],
            individual_data['creation_type'],
        )

        Individual.individuals[individual_file.stem].genealogy_parents = individual_data['genealogy_parents']
        Individual.individuals[individual_file.stem].genealogy_children = individual_data['genealogy_children']

        if 'evaluation_result' in individual_data:
            AbstractIndividual.individuals[individual_file.stem].evaluation_result = individual_data['evaluation_result']

    @staticmethod
    def random(task_api_client: ditef_router.api_client.ApiClient, configuration: dict) -> 'Individual':
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
        )

        return Individual.individuals[individual_id]

    @staticmethod
    def clone(parent: 'Individual', task_api_client: ditef_router.api_client.ApiClient, configuration: dict, creation_type: str) -> 'Individual':
        '''Creates a copy of a parent individual'''

        individual_id = str(uuid.uuid4())
        Individual.individuals[individual_id] = Individual(
            task_api_client,
            configuration,
            individual_id,
            copy.deepcopy(parent.genome),
            creation_type,
        )
        Individual.individuals[individual_id].genealogy_parents = [parent.id]
        parent.genealogy_children.append(individual_id)
        parent.update_event.notify()

        return Individual.individuals[individual_id]

    @staticmethod
    def cross_over_one(parent_a: 'Individual', parent_b: 'Individual', task_api_client: ditef_router.api_client.ApiClient, configuration: dict) -> 'Individual':
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
        )
        Individual.individuals[individual_id].genealogy_parents = [
            parent_a.id,
            parent_b.id,
        ]
        parent_a.genealogy_children.append(individual_id)
        parent_a.update_event.notify()
        parent_b.genealogy_children.append(individual_id)
        parent_b.update_event.notify()

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
        self.update_event.notify()

    async def evaluate(self):
        self.evaluation_result = await self.task_api_client.run(
            'ditef_worker_genetic_individual_string',
            payload={
                'genome': self.genome,
                'target_string': self.configuration['target_string'],
            },
        )
        self.update_event.notify()

    def fitness(self) -> typing.Optional[float]:
        try:
            return self.evaluation_result['correct_characters'] - abs(self.evaluation_result['length_difference']) * 2
        except TypeError:
            return None
