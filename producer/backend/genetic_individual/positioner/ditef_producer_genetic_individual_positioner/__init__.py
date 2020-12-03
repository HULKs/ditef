import aiohttp.web
import asyncio
import copy
import datetime
import random
import typing
import uuid

import ditef_producer_shared.event
import ditef_producer_shared.json
import ditef_router.api_client


class Individual:

    @staticmethod
    def configuration_values() -> dict:
        return {
            'max_mutations': {
                'help': 'Maximum amount of mutations (suitable for changing online)',
                'default': 10,
            },
            'type': {
                'help': 'NN type',
                'default': 'positioner',
            },
            'final_layer_neurons': {
                'help': 'Number of output neurons',
                'default': 3,
            },
            'loss': {
                'help': 'loss function',
                'default': 'mean_squared_error',
            },
            'input_size_x': {
                'help': 'Pixel columns in input images',
                'default': 32,
            },
            'input_size_y': {
                'help': 'Pixel rows in input images',
                'default': 32,
            },
            'input_channels': {
                'help': 'Values per pixel',
                'default': 1,
            },
            'metrics': {
                'help': 'Metrics used for evaluation',
                'default': ['accuracy'],
            },
            'conv_activation_functions': {
                'help': 'Available activation functions for convolutional layers',
                'default': ['elu',
                            'hard_sigmoid',
                            'linear',
                            'relu',
                            'selu',
                            'sigmoid',
                            #'softmax', not supported for conv layers by CompiledNN
                            #'softplus', not supported by CompiledNN
                            #'softsign', suspicious
                            'tanh'],
            },
            'dense_activation_functions': {
                'help': 'Available activation functions for dense layers',
                'default': ['elu',
                            'hard_sigmoid',
                            'linear',
                            'relu',
                            'selu',
                            'sigmoid',
                            #'softmax', not supported for conv layers by CompiledNN
                            #'softplus', not supported by CompiledNN
                            #'softsign', suspicious
                            'tanh'],
            },
            'final_activation_functions': {
                'help': 'Available activation functions for the final layer',
                'default': ['elu', # good
                            #'hard_sigmoid', not useful when working with confidence thesholds
                            'linear',
                            'relu',
                            'selu'],
            },
            'optimizers': {
                'help': 'Available optimizers',
                'default': ['Adadelta',
                            'Adam',
                            'Adamax',
                            'Nadam',
                            'RMSprop',
                            'SGD'],
            },
            'batch_size': {
                'help': 'Size of batches datasets are being split into',
                'default': 32,
            },
            'compiledNN_threshold': {
                'help': 'CompiledNN descrepency threshold',
                'default': 0.001,
            },
            'computational_cost_factor': {
                'help': 'Scalar for computational costs in fitness function (suitable for changing online)',
                'default': 0.000000005,
            },
            'train_dataset': {
                'help': 'Path to dataset used for fitting',
                'default': 'data/HULKs/datasets/ball_detection/positives-v1-train.tfrecord',
            },
            'test_dataset': {
                'help': 'Path to dataset used for evaluating',
                'default': 'data/HULKs/datasets/ball_detection/positives-v1-test.tfrecord',
            },
            'compiledNN_predicter': {
                'help': 'Path to compiledNN predicter',
                'default': 'predicter/build/predicter',
            },
            'augment_params': {
                'help': 'Parameters for online data augmentation',
                'default': {
                    'random_brightness_delta': {'help': 'Blabla', 'default': 0.25 * 255.0},
                    'random_brightness_seed': {'help': 'Blablabla', 'default': 42},
                },
            },
            'mutate_change_training_epochs_weight': {
                'help': 'Weight of changing training epochs when choosing a random mutation',
                'default': 1,
            },
            'mutate_add_convolution_layer_weight': {
                'help': 'Weight of adding convolution layer when choosing a random mutation',
                'default': 0.5,
            },
            'mutate_remove_convolution_layer_weight': {
                'help': 'Weight of removing convolution layer when choosing a random mutation',
                'default': 0.5,
            },
            'mutate_change_convolution_layer_type_weight': {
                'help': 'Weight of changing convolution layer type when choosing a random mutation',
                'default': 0.25,
            },
            'mutate_change_convolution_layer_kernels_weight': {
                'help': 'Weight of changing convolution layer kernels when choosing a random mutation',
                'default': 0.25,
            },
            'mutate_change_convolution_layer_kernel_size_weight': {
                'help': 'Weight of changing convolution layer kernel size when choosing a random mutation',
                'default': 0.25,
            },
            'mutate_change_convolution_layer_activation_function_weight': {
                'help': 'Weight of changing convolution layer activation function when choosing a random mutation',
                'default': 0.25,
            },
            'mutate_change_convolution_layer_pooling_weight': {
                'help': 'Weight of changing convolution layer pooling when choosing a random mutation',
                'default': 0.25,
            },
            'mutate_change_convolution_layer_batch_normalization_weight': {
                'help': 'Weight of changing convolution layer batch normalization when choosing a random mutation',
                'default': 0.25,
            },
            'mutate_change_convolution_layer_drop_out_weight': {
                'help': 'Weight of changing convolution layer drop out when choosing a random mutation',
                'default': 0.25,
            },
            'mutate_change_convolution_layer_stride_weight': {
                'help': 'Weight of changing convolution layer stride when choosing a random mutation',
                'default': 0.25,
            },
            'mutate_add_dense_layer_weight': {
                'help': 'Weight of adding dense layer when choosing a random mutation',
                'default': 1,
            },
            'mutate_remove_dense_layer_weight': {
                'help': 'Weight of removing dense layer when choosing a random mutation',
                'default': 1,
            },
            'mutate_change_dense_layer_weight': {
                'help': 'Weight of changing dense layer when choosing a random mutation',
                'default': 1,
            },
            'mutate_change_final_layer_activation_weight': {
                'help': 'Weight of changing final layer activation when choosing a random mutation',
                'default': 0.5,
            },
            'mutate_change_final_layer_batch_normalization_weight': {
                'help': 'Weight of changing final layer batch normalization when choosing a random mutation',
                'default': 0.5,
            },
            'mutate_change_optimizer_weight': {
                'help': 'Weight of changing optimizer when choosing a random mutation',
                'default': 1,
            },
            'mutate_change_initial_learning_rate_weight': {
                'help': 'Weight of changing initial learning rate when choosing a random mutation',
                'default': 1,
            },
            'mutate_change_learning_rate_factor_per_epoch_weight': {
                'help': 'Weight of changing learning rate factor per epoch when choosing a random mutation',
                'default': 1,
            },
        }

    individuals = {}

    def __init__(self, task_api_client: ditef_router.api_client.ApiClient, configuration: dict, id: str, genome: dict, creation_type: str):
        self.task_api_client = task_api_client
        self.configuration = configuration
        self.id = id
        self.genome = genome
        self.creation_type = creation_type
        self.genealogy_parents = []
        self.genealogy_children = []
        self.accuracy: typing.Optional[float] = None
        self.compiledNN_result: typing.Optional[float] = None
        self.computational_cost: typing.Optional[float] = None
        self.evaluation_result: typing.Optional[dict] = None
        self.update_event = ditef_producer_shared.event.BroadcastEvent()

    @staticmethod
    def random(task_api_client: ditef_router.api_client.ApiClient, configuration: dict) -> 'Individual':
        '''Generates a new random individual'''

        individual_id = str(uuid.uuid4())
        genome = {}
        genome['training_epochs'] = random.randint(1, 4)
        genome['convolution_layers'] = []
        hiddenLayers = random.randint(1, 4)
        size = configuration['input_size_x']
        for _ in range(hiddenLayers):
            pooling_type = None
            pooling_size = random.choice([0, 2])
            if pooling_size != 0:
                pooling_type = random.choice(['maximum', 'average'])
                size /= abs(pooling_size)
            stride = 1
            if size > 2:
                stride = random.choice([1, 2])
            size /= stride
            genome['convolution_layers'].append({
                'type': random.choice(['SeparableConv2D', 'Conv2D']),
                'filters': random.choice([1, 2, 4, 8, 16, 32, 64, 128]),
                'kernel_size': random.choice([3, 5]),
                'activation_function': random.choice(configuration['conv_activation_functions']),
                'pooling_type': pooling_type,
                'pooling_size': pooling_size,
                'batch_normalization': random.choice([True, False]),
                'drop_out_rate': random.uniform(0, 0.5),
                'stride': stride,
            })
            if size == 2:
                break
        genome['dense_layers'] = []
        hiddenLayers = random.randint(1, 3)
        for _ in range(hiddenLayers):
            genome['dense_layers'].append({
                'units': random.randint(2, 128),
                'activation_function': random.choice(configuration['dense_activation_functions']),
                'batch_normalization': random.choice([True, False]),
                'drop_out_rate': random.uniform(0, 0.5),
            })

        genome['final_layer_activation_function'] = random.choice(configuration['final_activation_functions'])
        genome['final_layer_batch_normalization'] = random.choice([True, False])
        genome['optimizer'] = random.choice(configuration['optimizers'])
        genome['initial_learning_rate'] = random.uniform(0.001, 0.1)
        genome['learning_rate_factor_per_epoch'] = random.uniform(0.1, 0.8)

        Individual.individuals[individual_id] = Individual(
            task_api_client,
            configuration,
            individual_id,
            genome,
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
            {  #TODO: check for deepcopy need
                'training_epochs':
                    random.choice([parent_a.genome['training_epochs'], parent_b.genome['training_epochs']]),
                'convolution_layers':
                    copy.deepcopy(random.choice([parent_a.genome['convolution_layers'], parent_b.genome['convolution_layers']])),
                'dense_layers':
                    copy.deepcopy(random.choice([parent_a.genome['dense_layers'], parent_b.genome['dense_layers']])),
                'final_layer_activation_function':
                    random.choice([parent_a.genome['final_layer_activation_function'], parent_b.genome['final_layer_activation_function']]),
                'final_layer_batch_normalization':
                    random.choice([parent_a.genome['final_layer_batch_normalization'], parent_b.genome['final_layer_batch_normalization']]),
                'optimizer':
                    random.choice([parent_a.genome['optimizer'], parent_b.genome['optimizer']]),
                'initial_learning_rate':
                    random.choice([parent_a.genome['initial_learning_rate'], parent_b.genome['initial_learning_rate']]),
                'learning_rate_factor_per_epoch':
                    random.choice([parent_a.genome['learning_rate_factor_per_epoch'], parent_b.genome['learning_rate_factor_per_epoch']])
            },
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
        '''Mutate this individual in-place'''

        for _ in range(random.randint(0, self.configuration['max_mutations']) + 1):
            mutation_weights = {
                self.mutate_change_training_epochs:
                    self.configuration['mutate_change_training_epochs_weight'],
                self.mutate_add_convolution_layer:
                    self.configuration['mutate_add_convolution_layer_weight']
                    if self.size_after_convolution_layers() > 2 else 0,
                self.mutate_remove_convolution_layer:
                    self.configuration['mutate_remove_convolution_layer_weight']
                    if len(self.genome['convolution_layers']) > 1 else 0,
                self.mutate_change_convolution_layer_type:
                    self.configuration['mutate_change_convolution_layer_type_weight'],
                self.mutate_change_convolution_layer_kernels:
                    self.configuration['mutate_change_convolution_layer_kernels_weight'],
                self.mutate_change_convolution_layer_kernel_size:
                    self.configuration['mutate_change_convolution_layer_kernel_size_weight'],
                self.mutate_change_convolution_layer_activation_function:
                    self.configuration['mutate_change_convolution_layer_activation_function_weight'],
                self.mutate_change_convolution_layer_pooling:
                    self.configuration['mutate_change_convolution_layer_pooling_weight']
                    if self.size_after_convolution_layers() > 2 else 0,
                self.mutate_change_convolution_layer_batch_normalization:
                    self.configuration['mutate_change_convolution_layer_batch_normalization_weight'],
                self.mutate_change_convolution_layer_drop_out:
                    self.configuration['mutate_change_convolution_layer_drop_out_weight'],
                self.mutate_change_convolution_layer_stride:
                    self.configuration['mutate_change_convolution_layer_stride_weight']
                    if self.size_after_convolution_layers() > 2 else 0,
                self.mutate_add_dense_layer:
                    self.configuration['mutate_add_dense_layer_weight'],
                self.mutate_remove_dense_layer:
                    self.configuration['mutate_remove_dense_layer_weight']
                    if len(self.genome['dense_layers']) > 1 else 0,
                self.mutate_change_dense_layer:
                    self.configuration['mutate_change_dense_layer_weight'],
                self.mutate_change_final_layer_activation:
                    self.configuration['mutate_change_final_layer_activation_weight'],
                self.mutate_change_final_layer_batch_normalization:
                    self.configuration['mutate_change_final_layer_batch_normalization_weight'],
                self.mutate_change_optimizer:
                    self.configuration['mutate_change_optimizer_weight'],
                self.mutate_change_initial_learning_rate:
                    self.configuration['mutate_change_initial_learning_rate_weight'],
                self.mutate_change_learning_rate_factor_per_epoch:
                    self.configuration['mutate_change_learning_rate_factor_per_epoch_weight'],
            }
            mutations = list(mutation_weights.keys())
            random.choices(mutations, [mutation_weights[t] for t in mutations])[0]()
        self.update_event.notify()

    async def evaluate(self):
        self.update_computational_cost()
        self.evaluation_result = await self.task_api_client.run(
            'ditef_worker_genetic_individual_neuralnet',
            {
                'genome': self.genome,
                'configuration': self.configuration
            }
        )
        self.accuracy = self.evaluation_result['accuracy']
        self.compiledNN_result = self.evaluation_result['compiledNN_result']
        self.update_event.notify()

    def fitness(self) -> typing.Optional[float]:
        if self.accuracy is None:
            return None
        if 'exception' in self.evaluation_result:
            return -1
        if self.compiledNN_result > self.configuration['compiledNN_threshold']:
            return 0
        return self.accuracy - (self.computational_cost * self.configuration['computational_cost_factor'])

    def api_url(self) -> str:
        return f'/genetic_individual_positioner/api/{self.id}'

    async def api_write_update_to_websocket(self, websocket: aiohttp.web.WebSocketResponse):
        await websocket.send_json(
            data={
                'genome': self.genome,
                'configuration': self.configuration,
                'computational_cost': self.computational_cost,
                'evaluation_result': self.evaluation_result,
                'fitness': self.fitness(),
                'creation_type': self.creation_type,
                'genealogy_parents': {
                    parent_id: {
                        'fitness': Individual.individuals[parent_id].fitness(),
                        'url': Individual.individuals[parent_id].api_url(),
                    }
                    for parent_id in self.genealogy_parents
                },
                'genealogy_children': {
                    child_id: {
                        'fitness': Individual.individuals[child_id].fitness(),
                        'url': Individual.individuals[child_id].api_url(),
                    }
                    for child_id in self.genealogy_children
                },
            },
            dumps=ditef_producer_shared.json.json_formatter_compressed,
        )

    async def subscribe_to_update(self, websocket: aiohttp.web.WebSocketResponse):
        with self.update_event.subscribe() as subscription:
            while True:
                await self.api_write_update_to_websocket(websocket)
                last_websocket_message = datetime.datetime.now()
                await subscription.wait()
                seconds_spent_in_wait = (
                    datetime.datetime.now() - last_websocket_message
                ).total_seconds()
                if seconds_spent_in_wait < Individual.minimum_websocket_interval:
                    await asyncio.sleep(Individual.minimum_websocket_interval - seconds_spent_in_wait)

    minimum_websocket_interval = 0

    @staticmethod
    def api_add_routes(app: aiohttp.web.Application, minimum_websocket_interval: int):
        Individual.minimum_websocket_interval = minimum_websocket_interval
        app.add_routes([
            aiohttp.web.get(
                r'/genetic_individual_bitvector/api/{individual_id:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}}',
                Individual.api_handle_websocket,
            ),
        ])

    @staticmethod
    async def api_handle_websocket(request: aiohttp.web.Request):
        websocket = aiohttp.web.WebSocketResponse(heartbeat=10)
        await websocket.prepare(request)

        individual_id = request.match_info['individual_id']
        individual: Individual = Individual.individuals[individual_id]

        update_subscription_task = asyncio.create_task(
            individual.subscribe_to_update(
                websocket,
            ),
        )

        await individual.api_write_update_to_websocket(websocket)

        try:
            async for message in websocket:
                assert message.type == aiohttp.web.WSMsgType.TEXT
                print('Message not handled:', message)
        finally:
            update_subscription_task.cancel()
            try:
                await update_subscription_task
            except asyncio.CancelledError:
                pass

        return websocket

    def mutate_change_training_epochs(self):
        '''Changes training epochs to a new random value near the previous'''

        self.genome['training_epochs'] = random.randint(max(1, self.genome['training_epochs']-2),
                                                        min(20, self.genome['training_epochs']+2))

    def mutate_add_convolution_layer(self):
        '''Add convolution layer'''

        size = self.size_after_convolution_layers()
        layer_index = random.randrange(len(self.genome['convolution_layers']) + 1)
        pooling_type = None
        pooling_size = random.choice([0, 2])
        if pooling_size != 0:
            pooling_type = random.choice(['maximum', 'average'])
            size /= abs(pooling_size)
        self.genome['convolution_layers'].insert(layer_index, {
            'type': random.choice(['SeparableConv2D', 'Conv2D']),
            'filters': random.choice([1, 2, 4, 8, 16, 32, 64, 128]),
            'kernel_size': random.choice([3, 5]),
            'activation_function': random.choice(self.configuration['conv_activation_functions']),
            'pooling_type': pooling_type,
            'pooling_size': pooling_size,
            'batch_normalization': random.choice([True, False]),
            'drop_out_rate': random.uniform(0, 0.5),
            'stride': random.choice([1, 2]) if size > 2 else 1,
        })

    def mutate_remove_convolution_layer(self):
        '''Remove convolution layer'''

        if len(self.genome['convolution_layers']) > 1:
            layer_index = random.randrange(len(self.genome['convolution_layers']))
            del self.genome['convolution_layers'][layer_index]

    def mutate_change_convolution_layer_type(self):
        '''Change convolution layer type'''

        layer_index = random.randrange(len(self.genome['convolution_layers']))
        self.genome['convolution_layers'][layer_index]['type'] = random.choice(['SeparableConv2D', 'Conv2D'])

    def mutate_change_convolution_layer_kernels(self):
        '''Change convolution layer filters'''

        layer_index = random.randrange(len(self.genome['convolution_layers']))
        self.genome['convolution_layers'][layer_index]['filters'] = random.choice([1, 2, 4, 8, 16, 32, 64, 128])

    def mutate_change_convolution_layer_kernel_size(self):
        '''Change convolution layer kernel size'''

        layer_index = random.randrange(len(self.genome['convolution_layers']))
        self.genome['convolution_layers'][layer_index]['kernel_size'] = random.choice([3, 5])

    def mutate_change_convolution_layer_activation_function(self):
        '''Change convolution layer activation function'''

        layer_index = random.randrange(len(self.genome['convolution_layers']))
        self.genome['convolution_layers'][layer_index]['activation_function'] = random.choice(self.configuration['conv_activation_functions'])

    def mutate_change_convolution_layer_pooling(self):
        '''Change convolution layer pooling'''

        layer_index = random.randrange(len(self.genome['convolution_layers']))
        pooling_size = random.choice([0, 2])
        self.genome['convolution_layers'][layer_index]['pooling_size'] = pooling_size
        self.genome['convolution_layers'][layer_index]['pooling_type'] = random.choice(['maximum', 'average']) if pooling_size != 0 else None

    def mutate_change_convolution_layer_batch_normalization(self):
        '''Change convolution layer batch normalization'''

        layer_index = random.randrange(len(self.genome['convolution_layers']))
        self.genome['convolution_layers'][layer_index]['batch_normalization'] = random.choice([True, False])

    def mutate_change_convolution_layer_drop_out(self):
        '''Change convolution layer drop out'''

        layer_index = random.randrange(len(self.genome['convolution_layers']))
        drop_out_rate = self.genome['convolution_layers'][layer_index]['drop_out_rate']
        self.genome['convolution_layers'][layer_index]['drop_out_rate'] = random.uniform(drop_out_rate / 2, min(0.5, drop_out_rate * 2))

    def mutate_change_convolution_layer_stride(self):
        '''Change convolution layer stride'''

        layer_index = random.randrange(len(self.genome['convolution_layers']))
        size = self.size_after_convolution_layers(layer_index)
        self.genome['convolution_layers'][layer_index]['stride'] = random.choice([1, 2]) if size > 2 else 1

    def mutate_add_dense_layer(self):
        '''Add dense layer'''

        layer_index = random.randrange(len(self.genome['dense_layers']) + 1)
        self.genome['dense_layers'].insert(layer_index, {
            'units': random.randint(2, 128),
            'activation_function': random.choice(self.configuration['dense_activation_functions']),
            'batch_normalization': random.choice([True, False]),
            'drop_out_rate': random.uniform(0, 0.5),
        })

    def mutate_remove_dense_layer(self):
        '''Remove dense layer'''
        if len(self.genome['dense_layers']) > 1:
            layer_index = random.randrange(len(self.genome['dense_layers']))
            del self.genome['dense_layers'][layer_index]

    def mutate_change_dense_layer(self):
        '''Change whole dense layer'''

        layer_index = random.randrange(len(self.genome['dense_layers']))
        units = self.genome['dense_layers'][layer_index]['units']
        self.genome['dense_layers'][layer_index]['units'] = random.randint(int(max(2, units) / 2), 2 * units)
        self.genome['dense_layers'][layer_index]['activation_function'] = random.choice(self.configuration['dense_activation_functions'])
        self.genome['dense_layers'][layer_index]['batch_normalization'] = random.choice([True, False])
        drop_out_rate = self.genome['dense_layers'][layer_index]['drop_out_rate']
        self.genome['dense_layers'][layer_index]['drop_out_rate'] = random.uniform(drop_out_rate / 2, min(0.5, drop_out_rate * 2))

    def mutate_change_final_layer_activation(self):
        '''Change final layer activation function'''

        self.final_layer_activation_function = random.choice(self.configuration['final_activation_functions'])

    def mutate_change_final_layer_batch_normalization(self):
        '''Change final layer batch normalization'''

        self.genome['final_layer_batch_normalization'] = random.choice([True, False])

    def mutate_change_optimizer(self):
        '''Change training optimizer'''

        self.genome['optimizer'] = random.choice(self.configuration['optimizers'])

    def mutate_change_initial_learning_rate(self):
        '''Change initial learning rate'''

        self.genome['initial_learning_rate'] = random.uniform(self.genome['initial_learning_rate'] / 2, self.genome['initial_learning_rate'] * 2)

    def mutate_change_learning_rate_factor_per_epoch(self):
        '''Change learning rate decay factor per epoch'''

        self.genome['learning_rate_factor_per_epoch'] = random.uniform(self.genome['learning_rate_factor_per_epoch'] / 2, self.genome['learning_rate_factor_per_epoch'] * 2)

    def size_after_convolution_layers(self, up_to_index = None):
        if up_to_index is None or up_to_index > len(self.genome['convolution_layers']) - 1:
            up_to_index = len(self.genome['convolution_layers']) - 1
        size = self.configuration['input_size_x']
        for layer_index in range(up_to_index + 1):
            size /= self.genome['convolution_layers'][layer_index]['stride']
            if self.genome['convolution_layers'][layer_index]['pooling_type'] is not None:
                size /= self.genome['convolution_layers'][layer_index]['pooling_size']
        return size

    def update_computational_cost(self):
        # TODO: Wait for and then implement https://github.com/tensorflow/tensorflow/issues/32809 ?
        # TODO: Wait for and then implement https://github.com/tensorflow/tensorflow/issues/39834 ?

        df = 32
        cost = 0
        m = 1
        for layer in self.genome['convolution_layers']:
            if layer['type'] == 'SeparableConv2D':
                cost += ((m * layer['kernel_size'] * layer['kernel_size'] * df * df) + (m * layer['filters'] * df * df)) / (layer['stride']*layer['stride'])
            elif layer['type'] == 'Conv2D':
                cost += (m * layer['filters'] * layer['kernel_size'] * layer['kernel_size'] * df * df) / (layer['stride']*layer['stride'])
            m = layer['filters']
            resize_denominator = layer['stride']
            if layer['pooling_type'] is not None:
                cost += m * layer['pooling_size'] * layer['pooling_size'] * df * df
                resize_denominator *= layer['pooling_size']
            df /= resize_denominator

        previous_layer_neurons = m * df * df
        for layer in self.genome['dense_layers']:
            cost += previous_layer_neurons * layer['units']
            previous_layer_neurons = layer['units']

        cost += previous_layer_neurons * self.configuration['final_layer_neurons']

        self.computational_cost = cost
