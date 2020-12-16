import asyncio
import datetime
import json
import importlib
import pandas
from pathlib import Path
import random

import ditef_producer_shared.event
import ditef_router.api_client
import weakref


class Population:

    @staticmethod
    def configuration_values(individual_type: str) -> dict:
        if Population.loaded_default_configuration is not None:
            return Population.loaded_default_configuration
        else:
            return {
                'minimum_amount_of_members': {
                    'help': 'Minimum amount of members in the population',
                    'default': 15,
                },
                'maximum_amount_of_members': {
                    'help': 'Maximum amount of members in the population',
                    'default': 25,
                },
                'migration_weight': {
                    'help': 'Weight for choosing migration as a random operation',
                    'default': 0.005,
                },
                'clone_weight': {
                    'help': 'Weight for choosing cloning with mutations as a random operation',
                    'default': 0.25,
                },
                'random_individual_weight': {
                    'help': 'Weight for choosing the creation of a random individual as a random operation',
                    'default': 0.25,
                },
                'cross_over_individual_weight': {
                    'help': 'Weight for choosing cross over to create a child from two parents as a random operation',
                    'default': 0.5,
                },
                **importlib.import_module(
                    individual_type,
                ).Individual.configuration_values(),
            }

    @staticmethod
    def purge_dead_populations():
        Population.populations = [
            population_reference
            for population_reference in Population.populations
            if population_reference() is not None
        ]

    populations = []
    loaded_default_configuration = None

    def __init__(self, individual_type: str, task_api_client: ditef_router.api_client.ApiClient, algorithm_event: ditef_producer_shared.event.BroadcastEvent, configuration: dict, state_path: Path, id: str):
        self.individual_type = individual_type
        self.task_api_client = task_api_client
        self.algorithm_metric_event = algorithm_event
        self.configuration = configuration
        self.configuration_event = ditef_producer_shared.event.BroadcastEvent()
        self.metric_event = ditef_producer_shared.event.BroadcastEvent()
        self.members_event = ditef_producer_shared.event.BroadcastEvent()
        self.members = []
        self.loading_queue = []
        self.state_path = state_path
        self.id = id
        self.history = pandas.DataFrame(
            data={
                'amount_of_members': pandas.Series([], dtype='int64'),
                'amount_of_evaluated_members': pandas.Series([], dtype='int64'),
                'amount_of_unevaluated_members': pandas.Series([], dtype='int64'),
                'fitness_minimum': pandas.Series([], dtype='float64'),
                'fitness_maximum': pandas.Series([], dtype='float64'),
                'fitness_median': pandas.Series([], dtype='float64'),
                'fitness_mean': pandas.Series([], dtype='float64'),
                'fitness_standard_deviation': pandas.Series([], dtype='float64'),
            },
            index=pandas.DatetimeIndex([]),
        )
        Population.populations.append(weakref.ref(self))

    async def ensure_minimum_amount_of_members(self):
        while len(self.members) < self.configuration['minimum_amount_of_members']:
            # too few members, add one random
            random_individual = importlib.import_module(
                self.individual_type,
            ).Individual.random(
                self.task_api_client,
                self.configuration,
                self.state_path/'individuals',
            )
            await self.finalize_new_member_operation(random_individual)
            self.append_to_history()
            self.algorithm_metric_event.notify()
            self.metric_event.notify()

    async def finalize_new_member_operation(self, individual):
        self.members.append(individual)
        self.write_to_file()
        self.members_event.notify()
        await individual.evaluate()
        individual.write_to_file(self.state_path/'individuals')
        self.members_event.notify()

    def write_to_file(self):
        data = {
            'members': [member.id for member in self.members],
            'configuration': self.configuration,
        }
        with open(self.state_path/'populations'/(self.id + '.json'), 'w') as f:
            json.dump(data, f, indent=4)

    async def random_operation(self):
        Population.purge_dead_populations()
        operation_weights = {
            self.migration_operation: self.configuration['migration_weight'] if len(Population.populations) > 1 else 0,
            self.clone_operation: self.configuration['clone_weight'],
            self.random_individual_operation: self.configuration['random_individual_weight'],
            self.cross_over_individual_operation: self.configuration['cross_over_individual_weight'],
        }
        operations = list(operation_weights.keys())
        await random.choices(operations, [operation_weights[t] for t in operations])[0]()
        self.append_to_history()
        self.algorithm_metric_event.notify()
        self.metric_event.notify()

    async def migration_operation(self):
        migration_origin = random.choice([
            population_reference
            for population_reference in Population.populations
            if population_reference() != self
        ])
        migrated_individual = importlib.import_module(
            self.individual_type,
        ).Individual.clone(
            random.choice(migration_origin().members),
            self.task_api_client,
            self.configuration,
            'migrant',
            self.state_path/'individuals',
        )
        await self.finalize_new_member_operation(migrated_individual)

    async def clone_operation(self):
        cloned_individual = importlib.import_module(
            self.individual_type,
        ).Individual.clone(
            random.choice(self.members),
            self.task_api_client,
            self.configuration,
            'clone',
            self.state_path/'individuals',
        )
        cloned_individual.mutate()
        await self.finalize_new_member_operation(cloned_individual)

    async def random_individual_operation(self):
        random_individual = importlib.import_module(
            self.individual_type,
        ).Individual.random(
            self.task_api_client,
            self.configuration,
            self.state_path/'individuals',
        )
        await self.finalize_new_member_operation(random_individual)

    async def cross_over_individual_operation(self):
        parent_a, parent_b = random.sample(self.members, k=2)
        crossed_over_individual = importlib.import_module(
            self.individual_type,
        ).Individual.cross_over_one(
            parent_a,
            parent_b,
            self.task_api_client,
            self.configuration,
            self.state_path/'individuals',
        )
        crossed_over_individual.mutate()
        await self.finalize_new_member_operation(crossed_over_individual)

    def load_member_from_static_dict(self, individual_id):
        if individual_id not in importlib.import_module(self.individual_type).Individual.individuals:
            print('could not find individual', individual_id, 'in dict')
            return
        individual = importlib.import_module(
            self.individual_type,
        ).Individual.individuals[individual_id]
        self.members.append(individual)
        self.members_event.notify()
        if individual.evaluation_result is None:
            self.loading_queue.append(individual)

    def ensure_maximum_amount_of_members(self):
        if len(self.members) > self.configuration['maximum_amount_of_members']:
            # too many members, remove some
            while len(self.members) > self.configuration['maximum_amount_of_members']:
                member_id_with_minimal_fitness = min(
                    [member_id for member_id in range(
                        len(self.members)) if self.members[member_id].fitness() is not None],
                    key=lambda member_id: self.members[member_id].fitness(),
                )
                del self.members[member_id_with_minimal_fitness]
            while len(self.members) > self.configuration['minimum_amount_of_members'] and random.choice([True, False]):
                member_id_with_minimal_fitness = min(
                    [member_id for member_id in range(
                        len(self.members)) if self.members[member_id].fitness() is not None],
                    key=lambda member_id: self.members[member_id].fitness(),
                )
                del self.members[member_id_with_minimal_fitness]
            self.append_to_history()
            self.algorithm_metric_event.notify()
            self.metric_event.notify()
            self.members_event.notify()

    def append_to_history(self):
        self.history = self.history.append(
            pandas.DataFrame(
                data=self.current_metrics(),
                index=pandas.DatetimeIndex([datetime.datetime.now()]),
            ),
        )

    def current_metrics(self):
        fitnesses = [member.fitness() for member in self.members]
        evaluated_fitnesses = pandas.Series([
            fitness
            for fitness in fitnesses
            if fitness is not None
        ])
        return {
            'amount_of_members': len(fitnesses),
            'amount_of_evaluated_members': len(evaluated_fitnesses),
            'amount_of_unevaluated_members': len(fitnesses) - len(evaluated_fitnesses),
            'fitness_minimum': evaluated_fitnesses.min(),
            'fitness_maximum': evaluated_fitnesses.max(),
            'fitness_median': evaluated_fitnesses.median(),
            'fitness_mean': evaluated_fitnesses.mean(),
            'fitness_standard_deviation': evaluated_fitnesses.std(),
        }

    def detailed_metrics(self, offset: datetime.datetime, duration: datetime.timedelta, interval: datetime.timedelta, aggregation_method: str):
        sliced_history = self.history.loc[offset:offset+duration]
        resampled_history = getattr(
            sliced_history.resample(interval),
            aggregation_method,
        )().interpolate(method='pad')
        return {
            'current': self.current_metrics(),
            'history': {
                'columns': ['timestamp'] + resampled_history.columns.to_list(),
                'data': [
                    list(metric_row)
                    for metric_row in resampled_history.itertuples()
                ],
            },
        }

    async def run(self):
        try:
            while self.loading_queue:
                individual, *self.loading_queue = self.loading_queue
                await individual.evaluate()
                individual.write_to_file(self.state_path/'individuals')
                self.members_event.notify()
            while True:
                await self.ensure_minimum_amount_of_members()
                await self.random_operation()
                self.ensure_maximum_amount_of_members()
        except asyncio.CancelledError:
            pass
        except:
            import traceback
            traceback.print_exc()
            raise
