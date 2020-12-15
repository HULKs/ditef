import aiohttp.web
import asyncio
import copy
import datetime
import json
from pathlib import Path
import random
import textwrap
import typing
import uuid

import ditef_producer_shared.event
import ditef_producer_shared.json
from ditef_producer_shared.individual import AbstractIndividual
import ditef_router.api_client


class Individual(AbstractIndividual):

    def individual_type(self) -> str:
        return('bitvector')

    @staticmethod
    def configuration_values() -> dict:
        return {
            'genome_size': {
                'help': 'Amount of bits in bitvector genome',
                'default': 100,
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

        individual_id = str(uuid.uuid4())
        Individual.individuals[individual_id] = Individual(
            task_api_client,
            configuration,
            individual_id,
            [
                random.choice([True, False])
                for _ in range(configuration['genome_size'])
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
        for _ in range(random.randrange(self.configuration['maximum_amount_of_mutations'] + 1)):
            i = random.randrange(len(self.genome))
            self.genome[i] = not self.genome[i]
        self.update_event.notify()

    async def evaluate(self):
        sum = await self.task_api_client.run(
            'ditef_worker_genetic_individual_bitvector',
            self.genome,
        )
        self.evaluation_result = {'sum': sum}
        self.update_event.notify()

    def fitness(self) -> typing.Optional[float]:
        if self.evaluation_result is not None:
            return float(self.evaluation_result['sum'])
