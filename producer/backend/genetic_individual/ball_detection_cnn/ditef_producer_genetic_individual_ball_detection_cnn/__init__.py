import copy
import pathlib
import random
import typing
import uuid

import ditef_producer_shared.genetic_individual
import ditef_router.api_client


class Individual(ditef_producer_shared.genetic_individual.AbstractIndividual):
    def individual_type(self) -> str:
        return ('ball_detection_cnn')

    @staticmethod
    def configuration_values() -> dict:
        return {
            # Maximum amount of mutations (suitable for changing online)
            'max_mutations':
            10,
            # NN type (positioner, classifier, preclassifier)
            'type':
            'positioner',
            # Number of output neurons
            'final_layer_neurons':
            3,
            # loss function
            'loss':
            'mean_squared_error',
            # Pixel columns in input images
            'input_size_x':
            32,
            # Pixel rows in input images
            'input_size_y':
            32,
            # Values per pixel
            'input_channels':
            1,
            # Metrics used for evaluation
            'metrics': ['mean_squared_error'],
            # Whether the metric should be negated in the fitness
            'negate_metric_in_fitness':
            True,
            # Available activation functions for convolutional layers
            'conv_activation_functions': [
                'elu',
                'hard_sigmoid',
                'linear',
                'relu',
                'selu',
                'sigmoid',
                #'softmax', not supported for conv layers by CompiledNN
                #'softplus', not supported by CompiledNN
                #'softsign', suspicious
                'tanh'
            ],
            # Available activation functions for dense layers
            'dense_activation_functions': [
                'elu',
                'hard_sigmoid',
                'linear',
                'relu',
                'selu',
                'sigmoid',
                #'softmax', not supported for conv layers by CompiledNN
                #'softplus', not supported by CompiledNN
                #'softsign', suspicious
                'tanh'
            ],
            # Available activation functions for the final layer
            'final_activation_functions': [
                'elu',  # good
                #'hard_sigmoid', not useful when working with confidence thesholds
                'linear',
                'relu',
                'selu'
            ],
            # Available optimizers
            'optimizers':
            ['Adadelta', 'Adam', 'Adamax', 'Nadam', 'RMSprop', 'SGD'],
            # Size of batches datasets are being split into
            'batch_size':
            32,
            # CompiledNN descrepency threshold
            'compiledNN_threshold':
            0.001,
            # Scalar for computational costs in fitness function (suitable for changing online)
            'computational_cost_factor':
            0.000000005,
            # Path to dataset used for fitting
            'train_dataset':
            'data/HULKs/datasets/ball_detection/positives-v1-train.tfrecord',
            # Path to dataset used for evaluating
            'test_dataset':
            'data/HULKs/datasets/ball_detection/positives-v1-test.tfrecord',
            # Path to compiledNN predicter
            'compiledNN_predicter':
            'predicter/build/predicter',
            # Parameters for online data augmentation
            'augment_params': {
                'random_brightness_delta': 0.25 * 255.0,
                'random_brightness_seed': 42,
            },
            # Weight of changing training epochs when choosing a random mutation
            'mutate_change_training_epochs_weight':
            1,
            # Weight of adding convolution layer when choosing a random mutation
            'mutate_add_convolution_layer_weight':
            0.5,
            # Weight of removing convolution layer when choosing a random mutation
            'mutate_remove_convolution_layer_weight':
            0.5,
            # Weight of changing convolution layer type when choosing a random mutation
            'mutate_change_convolution_layer_type_weight':
            0.25,
            # Weight of changing convolution layer kernels when choosing a random mutation
            'mutate_change_convolution_layer_kernels_weight':
            0.25,
            # Weight of changing convolution layer kernel size when choosing a random mutation
            'mutate_change_convolution_layer_kernel_size_weight':
            0.25,
            # Weight of changing convolution layer activation function when choosing a random mutation
            'mutate_change_convolution_layer_activation_function_weight':
            0.25,
            # Weight of changing convolution layer pooling when choosing a random mutation
            'mutate_change_convolution_layer_pooling_weight':
            0.25,
            # Weight of changing convolution layer batch normalization when choosing a random mutation
            'mutate_change_convolution_layer_batch_normalization_weight':
            0.25,
            # Weight of changing convolution layer drop out when choosing a random mutation
            'mutate_change_convolution_layer_drop_out_weight':
            0.25,
            # Weight of changing convolution layer stride when choosing a random mutation
            'mutate_change_convolution_layer_stride_weight':
            0.25,
            # Weight of adding dense layer when choosing a random mutation
            'mutate_add_dense_layer_weight':
            1,
            # Weight of removing dense layer when choosing a random mutation
            'mutate_remove_dense_layer_weight':
            1,
            # Weight of changing dense layer when choosing a random mutation
            'mutate_change_dense_layer_weight':
            1,
            # Weight of changing final layer activation when choosing a random mutation
            'mutate_change_final_layer_activation_weight':
            0.5,
            # Weight of changing final layer batch normalization when choosing a random mutation
            'mutate_change_final_layer_batch_normalization_weight':
            0.5,
            # Weight of changing optimizer when choosing a random mutation
            'mutate_change_optimizer_weight':
            1,
            # Weight of changing initial learning rate when choosing a random mutation
            'mutate_change_initial_learning_rate_weight':
            1,
            # Weight of changing learning rate factor per epoch when choosing a random mutation
            'mutate_change_learning_rate_factor_per_epoch_weight':
            1,
        }

    @staticmethod
    def random(task_api_client: ditef_router.api_client.ApiClient,
               configuration: dict, state_path: pathlib.Path) -> 'Individual':
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
                'type':
                random.choice(['SeparableConv2D', 'Conv2D']),
                'filters':
                random.choice([1, 2, 4, 8, 16, 32, 64, 128]),
                'kernel_size':
                random.choice([3, 5]),
                'activation_function':
                random.choice(configuration['conv_activation_functions']),
                'pooling_type':
                pooling_type,
                'pooling_size':
                pooling_size,
                'batch_normalization':
                random.choice([True, False]),
                'drop_out_rate':
                random.uniform(0, 0.5),
                'stride':
                stride,
            })
            if size == 2:
                break
        genome['dense_layers'] = []
        hiddenLayers = random.randint(1, 3)
        for _ in range(hiddenLayers):
            genome['dense_layers'].append({
                'units':
                random.randint(2, 128),
                'activation_function':
                random.choice(configuration['dense_activation_functions']),
                'batch_normalization':
                random.choice([True, False]),
                'drop_out_rate':
                random.uniform(0, 0.5),
            })

        genome['final_layer_activation_function'] = random.choice(
            configuration['final_activation_functions'])
        genome['final_layer_batch_normalization'] = random.choice(
            [True, False])
        genome['optimizer'] = random.choice(configuration['optimizers'])
        genome['initial_learning_rate'] = random.uniform(0.001, 0.1)
        genome['learning_rate_factor_per_epoch'] = random.uniform(0.1, 0.8)

        Individual.individuals[individual_id] = Individual(
            task_api_client,
            configuration,
            individual_id,
            genome,
            'random',
            state_path / 'individuals' / f'{individual_id}.json',
        )
        Individual.individuals[individual_id].write_to_file()

        return Individual.individuals[individual_id]

    @staticmethod
    def clone(parent: 'Individual',
              task_api_client: ditef_router.api_client.ApiClient,
              configuration: dict, creation_type: str,
              state_path: pathlib.Path) -> 'Individual':
        '''Creates a copy of a parent individual'''

        individual_id = str(uuid.uuid4())
        Individual.individuals[individual_id] = Individual(
            task_api_client,
            configuration,
            individual_id,
            copy.deepcopy(parent.genome),
            creation_type,
            state_path / 'individuals' / f'{individual_id}.json',
        )
        Individual.individuals[individual_id].genealogy_parents = [parent.id]
        Individual.individuals[individual_id].write_to_file()
        parent.add_child(individual_id)

        return Individual.individuals[individual_id]

    @staticmethod
    def cross_over_one(parent_a: 'Individual', parent_b: 'Individual',
                       task_api_client: ditef_router.api_client.ApiClient,
                       configuration: dict,
                       state_path: pathlib.Path) -> 'Individual':
        '''Creates one cross-overed individual from two parent individuals'''

        individual_id = str(uuid.uuid4())
        Individual.individuals[individual_id] = Individual(
            task_api_client,
            configuration,
            individual_id,
            {  #TODO: check for deepcopy need
                'training_epochs':
                random.choice([
                    parent_a.genome['training_epochs'],
                    parent_b.genome['training_epochs']
                ]),
                'convolution_layers':
                copy.deepcopy(
                    random.choice([
                        parent_a.genome['convolution_layers'],
                        parent_b.genome['convolution_layers']
                    ])),
                'dense_layers':
                copy.deepcopy(
                    random.choice([
                        parent_a.genome['dense_layers'],
                        parent_b.genome['dense_layers']
                    ])),
                'final_layer_activation_function':
                random.choice([
                    parent_a.genome['final_layer_activation_function'],
                    parent_b.genome['final_layer_activation_function']
                ]),
                'final_layer_batch_normalization':
                random.choice([
                    parent_a.genome['final_layer_batch_normalization'],
                    parent_b.genome['final_layer_batch_normalization']
                ]),
                'optimizer':
                random.choice([
                    parent_a.genome['optimizer'], parent_b.genome['optimizer']
                ]),
                'initial_learning_rate':
                random.choice([
                    parent_a.genome['initial_learning_rate'],
                    parent_b.genome['initial_learning_rate']
                ]),
                'learning_rate_factor_per_epoch':
                random.choice([
                    parent_a.genome['learning_rate_factor_per_epoch'],
                    parent_b.genome['learning_rate_factor_per_epoch']
                ])
            },
            'cross_over_one',
            state_path / 'individuals' / f'{individual_id}.json',
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
        '''Mutate this individual in-place'''

        for _ in range(
                random.randint(0, self.configuration['max_mutations']) + 1):
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
                self.
                configuration['mutate_change_convolution_layer_type_weight'],
                self.mutate_change_convolution_layer_kernels:
                self.configuration[
                    'mutate_change_convolution_layer_kernels_weight'],
                self.mutate_change_convolution_layer_kernel_size:
                self.configuration[
                    'mutate_change_convolution_layer_kernel_size_weight'],
                self.mutate_change_convolution_layer_activation_function:
                self.configuration[
                    'mutate_change_convolution_layer_activation_function_weight'],
                self.mutate_change_convolution_layer_pooling:
                self.
                configuration['mutate_change_convolution_layer_pooling_weight']
                if self.size_after_convolution_layers() > 2 else 0,
                self.mutate_change_convolution_layer_batch_normalization:
                self.configuration[
                    'mutate_change_convolution_layer_batch_normalization_weight'],
                self.mutate_change_convolution_layer_drop_out:
                self.configuration[
                    'mutate_change_convolution_layer_drop_out_weight'],
                self.mutate_change_convolution_layer_stride:
                self.
                configuration['mutate_change_convolution_layer_stride_weight']
                if self.size_after_convolution_layers() > 2 else 0,
                self.mutate_add_dense_layer:
                self.configuration['mutate_add_dense_layer_weight'],
                self.mutate_remove_dense_layer:
                self.configuration['mutate_remove_dense_layer_weight']
                if len(self.genome['dense_layers']) > 1 else 0,
                self.mutate_change_dense_layer:
                self.configuration['mutate_change_dense_layer_weight'],
                self.mutate_change_final_layer_activation:
                self.
                configuration['mutate_change_final_layer_activation_weight'],
                self.mutate_change_final_layer_batch_normalization:
                self.configuration[
                    'mutate_change_final_layer_batch_normalization_weight'],
                self.mutate_change_optimizer:
                self.configuration['mutate_change_optimizer_weight'],
                self.mutate_change_initial_learning_rate:
                self.
                configuration['mutate_change_initial_learning_rate_weight'],
                self.mutate_change_learning_rate_factor_per_epoch:
                self.configuration[
                    'mutate_change_learning_rate_factor_per_epoch_weight'],
            }
            mutations = list(mutation_weights.keys())
            random.choices(mutations,
                           [mutation_weights[t] for t in mutations])[0]()
        self.write_to_file()
        self.update_event.notify()

    async def evaluate(self):
        self.evaluation_result = await self.task_api_client.run(
            'ditef_worker_genetic_individual_neuralnet', {
                'id': self.id,
                'genome': self.genome,
                'configuration': self.configuration
            })
        self.evaluation_result['computational_cost'] = self.computational_cost(
        )
        self.write_to_file()
        self.update_event.notify()

    def fitness(self) -> typing.Optional[float]:
        if self.evaluation_result is None:
            return None
        if 'exception' in self.evaluation_result:
            return -1
        if self.evaluation_result['compiledNN_result'] > self.configuration[
                'compiledNN_threshold']:
            return 0
        metric_factor = -1 if self.configuration[
            'negate_metric_in_fitness'] else 1
        return (metric_factor *
                self.evaluation_result[self.configuration['metrics'][0]]) - (
                    self.computational_cost() *
                    self.configuration['computational_cost_factor'])

    def mutate_change_training_epochs(self):
        '''Changes training epochs to a new random value near the previous'''

        self.genome['training_epochs'] = random.randint(
            max(1, self.genome['training_epochs'] - 2),
            min(20, self.genome['training_epochs'] + 2))

    def mutate_add_convolution_layer(self):
        '''Add convolution layer'''

        size = self.size_after_convolution_layers()
        layer_index = random.randrange(
            len(self.genome['convolution_layers']) + 1)
        pooling_type = None
        pooling_size = random.choice([0, 2])
        if pooling_size != 0:
            pooling_type = random.choice(['maximum', 'average'])
            size /= abs(pooling_size)
        self.genome['convolution_layers'].insert(
            layer_index, {
                'type':
                random.choice(['SeparableConv2D', 'Conv2D']),
                'filters':
                random.choice([1, 2, 4, 8, 16, 32, 64, 128]),
                'kernel_size':
                random.choice([3, 5]),
                'activation_function':
                random.choice(self.configuration['conv_activation_functions']),
                'pooling_type':
                pooling_type,
                'pooling_size':
                pooling_size,
                'batch_normalization':
                random.choice([True, False]),
                'drop_out_rate':
                random.uniform(0, 0.5),
                'stride':
                random.choice([1, 2]) if size > 2 else 1,
            })

    def mutate_remove_convolution_layer(self):
        '''Remove convolution layer'''

        if len(self.genome['convolution_layers']) > 1:
            layer_index = random.randrange(
                len(self.genome['convolution_layers']))
            del self.genome['convolution_layers'][layer_index]

    def mutate_change_convolution_layer_type(self):
        '''Change convolution layer type'''

        layer_index = random.randrange(len(self.genome['convolution_layers']))
        self.genome['convolution_layers'][layer_index]['type'] = random.choice(
            ['SeparableConv2D', 'Conv2D'])

    def mutate_change_convolution_layer_kernels(self):
        '''Change convolution layer filters'''

        layer_index = random.randrange(len(self.genome['convolution_layers']))
        self.genome['convolution_layers'][layer_index][
            'filters'] = random.choice([1, 2, 4, 8, 16, 32, 64, 128])

    def mutate_change_convolution_layer_kernel_size(self):
        '''Change convolution layer kernel size'''

        layer_index = random.randrange(len(self.genome['convolution_layers']))
        self.genome['convolution_layers'][layer_index][
            'kernel_size'] = random.choice([3, 5])

    def mutate_change_convolution_layer_activation_function(self):
        '''Change convolution layer activation function'''

        layer_index = random.randrange(len(self.genome['convolution_layers']))
        self.genome['convolution_layers'][layer_index][
            'activation_function'] = random.choice(
                self.configuration['conv_activation_functions'])

    def mutate_change_convolution_layer_pooling(self):
        '''Change convolution layer pooling'''

        layer_index = random.randrange(len(self.genome['convolution_layers']))
        pooling_size = random.choice([0, 2])
        self.genome['convolution_layers'][layer_index][
            'pooling_size'] = pooling_size
        self.genome['convolution_layers'][layer_index][
            'pooling_type'] = random.choice(['maximum', 'average'
                                             ]) if pooling_size != 0 else None

    def mutate_change_convolution_layer_batch_normalization(self):
        '''Change convolution layer batch normalization'''

        layer_index = random.randrange(len(self.genome['convolution_layers']))
        self.genome['convolution_layers'][layer_index][
            'batch_normalization'] = random.choice([True, False])

    def mutate_change_convolution_layer_drop_out(self):
        '''Change convolution layer drop out'''

        layer_index = random.randrange(len(self.genome['convolution_layers']))
        drop_out_rate = self.genome['convolution_layers'][layer_index][
            'drop_out_rate']
        self.genome['convolution_layers'][layer_index][
            'drop_out_rate'] = random.uniform(drop_out_rate / 2,
                                              min(0.5, drop_out_rate * 2))

    def mutate_change_convolution_layer_stride(self):
        '''Change convolution layer stride'''

        layer_index = random.randrange(len(self.genome['convolution_layers']))
        size = self.size_after_convolution_layers(layer_index)
        self.genome['convolution_layers'][layer_index][
            'stride'] = random.choice([1, 2]) if size > 2 else 1

    def mutate_add_dense_layer(self):
        '''Add dense layer'''

        layer_index = random.randrange(len(self.genome['dense_layers']) + 1)
        self.genome['dense_layers'].insert(
            layer_index, {
                'units':
                random.randint(2, 128),
                'activation_function':
                random.choice(
                    self.configuration['dense_activation_functions']),
                'batch_normalization':
                random.choice([True, False]),
                'drop_out_rate':
                random.uniform(0, 0.5),
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
        self.genome['dense_layers'][layer_index]['units'] = random.randint(
            int(max(2, units) / 2), 2 * units)
        self.genome['dense_layers'][layer_index][
            'activation_function'] = random.choice(
                self.configuration['dense_activation_functions'])
        self.genome['dense_layers'][layer_index][
            'batch_normalization'] = random.choice([True, False])
        drop_out_rate = self.genome['dense_layers'][layer_index][
            'drop_out_rate']
        self.genome['dense_layers'][layer_index][
            'drop_out_rate'] = random.uniform(drop_out_rate / 2,
                                              min(0.5, drop_out_rate * 2))

    def mutate_change_final_layer_activation(self):
        '''Change final layer activation function'''

        self.final_layer_activation_function = random.choice(
            self.configuration['final_activation_functions'])

    def mutate_change_final_layer_batch_normalization(self):
        '''Change final layer batch normalization'''

        self.genome['final_layer_batch_normalization'] = random.choice(
            [True, False])

    def mutate_change_optimizer(self):
        '''Change training optimizer'''

        self.genome['optimizer'] = random.choice(
            self.configuration['optimizers'])

    def mutate_change_initial_learning_rate(self):
        '''Change initial learning rate'''

        self.genome['initial_learning_rate'] = random.uniform(
            self.genome['initial_learning_rate'] / 2,
            self.genome['initial_learning_rate'] * 2)

    def mutate_change_learning_rate_factor_per_epoch(self):
        '''Change learning rate decay factor per epoch'''

        self.genome['learning_rate_factor_per_epoch'] = random.uniform(
            self.genome['learning_rate_factor_per_epoch'] / 2,
            self.genome['learning_rate_factor_per_epoch'] * 2)

    def size_after_convolution_layers(self, up_to_index=None):
        if up_to_index is None or up_to_index > len(
                self.genome['convolution_layers']) - 1:
            up_to_index = len(self.genome['convolution_layers']) - 1
        size = self.configuration['input_size_x']
        for layer_index in range(up_to_index + 1):
            size /= self.genome['convolution_layers'][layer_index]['stride']
            if self.genome['convolution_layers'][layer_index][
                    'pooling_type'] is not None:
                size /= self.genome['convolution_layers'][layer_index][
                    'pooling_size']
        return size

    def computational_cost(self):
        # TODO: Wait for and then implement https://github.com/tensorflow/tensorflow/issues/32809 ?
        # TODO: Wait for and then implement https://github.com/tensorflow/tensorflow/issues/39834 ?

        df = 32
        cost = 0
        m = 1
        for layer in self.genome['convolution_layers']:
            if layer['type'] == 'SeparableConv2D':
                cost += ((m * layer['kernel_size'] * layer['kernel_size'] *
                          df * df) +
                         (m * layer['filters'] * df * df)) / (layer['stride'] *
                                                              layer['stride'])
            elif layer['type'] == 'Conv2D':
                cost += (m * layer['filters'] * layer['kernel_size'] *
                         layer['kernel_size'] * df * df) / (layer['stride'] *
                                                            layer['stride'])
            m = layer['filters']
            resize_denominator = layer['stride']
            if layer['pooling_type'] is not None:
                cost += m * layer['pooling_size'] * layer[
                    'pooling_size'] * df * df
                resize_denominator *= layer['pooling_size']
            df /= resize_denominator

        previous_layer_neurons = m * df * df
        for layer in self.genome['dense_layers']:
            cost += previous_layer_neurons * layer['units']
            previous_layer_neurons = layer['units']

        cost += previous_layer_neurons * self.configuration[
            'final_layer_neurons']

        return cost
