import aiohttp.web
import copy
import json
import random
import string
import task_router.api_client
import textwrap
import typing
import uuid


class Individual:

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

    individuals = {}

    def __init__(self, task_api_client: task_router.api_client.ApiClient, configuration: dict, id: str, genome: typing.List[bool], creation_type: str):
        self.task_api_client = task_api_client
        self.configuration = configuration
        self.id = id
        self.genome = genome
        self.creation_type = creation_type
        self.genealogy_parents = []
        self.genealogy_children = []
        self.correct_characters: typing.Optional[int] = None
        self.length_difference: typing.Optional[int] = None

    @staticmethod
    def random(task_api_client: task_router.api_client.ApiClient, configuration: dict) -> 'Individual':
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
    def clone(parent: 'Individual',task_api_client: task_router.api_client.ApiClient,  configuration: dict, creation_type: str) -> 'Individual':
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

        return Individual.individuals[individual_id]

    @staticmethod
    def cross_over_one(parent_a: 'Individual', parent_b: 'Individual', task_api_client: task_router.api_client.ApiClient, configuration: dict) -> 'Individual':
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
        parent_b.genealogy_children.append(individual_id)

        return Individual.individuals[individual_id]

    def mutate(self):
        for _ in range(random.randrange(self.configuration['maximum_amount_of_mutations'])):
            if random.choice([True] * 9 + [False]):
                # change character
                i = random.randrange(len(self.genome))
                self.genome[i] = random.choice(self.configuration['character_pool'])
            else:
                if random.choice([True, False]) and len(self.genome) > 0:
                    # remove one character
                    i = random.randrange(len(self.genome))
                    del self.genome[i]
                else:
                    # insert new character
                    i = random.randrange(len(self.genome))
                    self.genome.insert(i, random.choice(self.configuration['character_pool']))

    async def evaluate(self):
        result = await self.task_api_client.run(
            'ditef_worker_genetic_individual_string',
            payload={
                'genome': self.genome,
                'target_string': self.configuration['target_string'],
            },
        )
        self.correct_characters = result['correct_characters']
        self.length_difference = result['length_difference']

    def fitness(self) -> float:
        try:
            return self.correct_characters - abs(self.length_difference) * 2
        except TypeError:
            return None

    def ui_url(self) -> str:
        return f'/genetic_individual_string/ui?id={self.id}'

    @staticmethod
    def ui_add_routes(app: aiohttp.web.Application):
        app.add_routes([
            aiohttp.web.get(
                '/genetic_individual_string/ui',
                Individual.ui_handle_index,
            ),
        ])

    @staticmethod
    async def ui_handle_index(request: aiohttp.web.Request):
        individual_id = request.query['id']
        individual = Individual.individuals[individual_id]
        parents_list = ''
        for parent_id in individual.genealogy_parents:
            parent = Individual.individuals[parent_id]
            parents_list += f'<p><a href="{parent.ui_url()}">{parent.fitness()}</a></p>'
        children_list = ''
        for child_id in individual.genealogy_children:
            child = Individual.individuals[child_id]
            children_list += f'<p><a href="{child.ui_url()}">{child.fitness()}</a></p>'
        raise aiohttp.web.HTTPOk(
            text=textwrap.dedent(f'''
                <!DOCTYPE html>
                <html>
                    <head>
                        <title>genetic_individual_string</title>
                    </head>
                    <body>
                        <h1>Genetic Individual (String)</h1>
                        <h2>ID</h2>
                        <p>{individual_id}</p>
                        <h2>Genome</h2>
                        <p>{json.dumps("".join(individual.genome))} (Length: {len(individual.genome)})</p>
                        <h2>Fitness</h2>
                        <p>{json.dumps(individual.fitness())}</p>
                        <h2>Creation Type</h2>
                        {individual.creation_type}
                        <h2>Parents</h2>
                        {parents_list}
                        <h2>Children</h2>
                        {children_list}
                    </body>
                </html>
            '''),
            content_type='text/html',
        )
