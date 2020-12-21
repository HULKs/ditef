import json
import multiprocessing
import multiprocessing.sharedctypes
import numpy
import pathlib
import PyCompiledNN
import subprocess
import tensorflow as tf


def run(payload):
    genome = payload['genome']
    configuration = payload['configuration']
    run_result = {
        'compiledNN_result': 500.0,
        'accuracy': 0,
        'training_progression': [],
    }
    tmp_model_path = pathlib.Path('tmp_' + payload['id'] + '.hdf5')
    print("start evaluation of", payload['id'])
    try:
        model = build_model(genome, configuration)
        model.compile(
            optimizer=genome['optimizer'],
            loss=configuration['loss'],
            metrics=configuration['metrics']
        )

        train_dataset = get_dataset(tf.data.TFRecordDataset(configuration['train_dataset']),
                                    configuration['batch_size'],
                                    configuration['type'],
                                    configuration['input_size_x'] *
                                    configuration['input_size_y'],
                                    configuration['augment_params'])

        test_dataset = get_dataset(tf.data.TFRecordDataset(configuration['test_dataset']),
                                   configuration['batch_size'],
                                   configuration['type'],
                                   configuration['input_size_x'] *
                                   configuration['input_size_y'],
                                   configuration['augment_params'])

        verify_dataset = get_dataset(tf.data.TFRecordDataset(configuration['test_dataset']),  # TODO: not use test_dataset here
                                     configuration['batch_size'],
                                     'verify',
                                     configuration['input_size_x'] * \
                                     configuration['input_size_y'],
                                     configuration['augment_params'])

        model.optimizer.lr.assign(genome['initial_learning_rate'])

        tf_train_result = model.fit(
            train_dataset,
            epochs=genome['training_epochs'])

        run_result['training_progression'] = [
            {
                name: tf_train_result.history[name][ep]
                for name in (['loss'] + configuration['metrics'])
            }
            for ep in range(genome['training_epochs'])
        ]

        epoch = 0
        for _ in run_result['training_progression']:
            run_result['training_progression'][epoch]['epoch'] = epoch + 1
            epoch += 1

        evaluate_result = {
            name: value
            for name, value in zip(['loss'] + configuration['metrics'],
                                   model.evaluate(test_dataset))
        }

        for key in evaluate_result:
            run_result[key] = evaluate_result[key]

        tf.keras.models.save_model(
            model,
            str(tmp_model_path),
            save_format='h5')

        run_result['compiledNN_result'] = compiledNN_average_distance(model,
                                                                      tmp_model_path,
                                                                      verify_dataset,
                                                                      configuration)

    except Exception as e:
        print(e)
        run_result['exception'] = str(e)

    tmp_model_path.unlink()
    tf.keras.backend.clear_session()
    return run_result


def build_convolution_layers(genome):
    '''Build sequential layer list of convolution layers'''

    layers = []
    for layer in genome['convolution_layers']:
        if layer['type'] == 'SeparableConv2D':
            layers.append(tf.keras.layers.SeparableConv2D(
                filters=layer['filters'],
                kernel_size=layer['kernel_size'],
                strides=layer['stride'],
                padding='same',
                use_bias=False,
            ))
        elif layer['type'] == 'Conv2D':
            layers.append(tf.keras.layers.Conv2D(
                filters=layer['filters'],
                kernel_size=layer['kernel_size'],
                strides=layer['stride'],
                padding='same',
                use_bias=False,
            ))
        else:
            raise NotImplementedError

        if layer['batch_normalization']:
            layers.append(tf.keras.layers.BatchNormalization())

        layers.append(tf.keras.layers.Activation(
            activation=layer['activation_function'],
        ))

        if layer['pooling_type'] is not None:
            if layer['pooling_type'] == 'maximum':
                layers.append(tf.keras.layers.MaxPooling2D(
                    pool_size=layer['pooling_size'],
                ))
            elif layer['pooling_type'] == 'average':
                layers.append(tf.keras.layers.AveragePooling2D(
                    pool_size=layer['pooling_size'],
                ))
            else:
                raise NotImplementedError

        if layer['drop_out_rate'] > 0.01:
            layers.append(tf.keras.layers.Dropout(
                rate=layer['drop_out_rate'],
            ))

    return layers


def build_dense_layers(genome):
    '''Build sequential layer list of dense layers'''

    layers = []
    for layer in genome['dense_layers']:
        layers.append(tf.keras.layers.Dense(
            layer['units'],
            activation=layer['activation_function'],
        ))

        if layer['batch_normalization']:
            layers.append(tf.keras.layers.BatchNormalization())

        if layer['drop_out_rate'] > 0.01:
            layers.append(tf.keras.layers.Dropout(
                rate=layer['drop_out_rate'],
            ))

    return layers


def build_layers(genome, configuration):
    '''Build sequential layer list'''

    # input layer
    layers = [
        tf.keras.Input(
            shape=(configuration['input_size_x'],
                   configuration['input_size_y'],
                   configuration['input_channels']),
        )
    ]

    # convolution layers
    layers += build_convolution_layers(genome)

    # flatten between convolutions and denses
    layers.append(tf.keras.layers.Flatten())

    # dense layers
    layers += build_dense_layers(genome)

    # final layer
    layers.append(tf.keras.layers.Dense(
        configuration['final_layer_neurons'],
        activation=genome['final_layer_activation_function'],
    ))

    if genome['final_layer_batch_normalization']:
        layers.append(tf.keras.layers.BatchNormalization())

    return layers


def build_model(genome, configuration):
    '''Build sequential model'''

    return tf.keras.Sequential(
        layers=build_layers(genome, configuration),
    )


def shape_and_augment_sample(data, shape, augment_params):
    image = tf.reshape(tf.cast(data, tf.float32), shape)
    image = tf.image.random_brightness(
        image,
        augment_params['random_brightness_delta'],
        seed=augment_params['random_brightness_seed'])
    image = tf.clip_by_value(image, 0.0, 255.0, name=None)
    return(image)


def parse_tfrecord_class(data_size, augment_params, example):
    parsed = tf.io.parse_single_example(example, features={
        'data': tf.io.FixedLenFeature([data_size], tf.int64),
        'dataShape': tf.io.FixedLenFeature([3], tf.int64),
        'isPositive': tf.io.FixedLenFeature([1], tf.int64),
        'circle': tf.io.FixedLenFeature([3], tf.float32)
    })
    return(shape_and_augment_sample(parsed['data'], parsed['dataShape'], augment_params),
           tf.cast(parsed['isPositive'], tf.float32))


def parse_tfrecord_circle(data_size, augment_params, example):
    parsed = tf.io.parse_single_example(example, features={
        'data': tf.io.FixedLenFeature([data_size], tf.int64),
        'dataShape': tf.io.FixedLenFeature([3], tf.int64),
        'isPositive': tf.io.FixedLenFeature([1], tf.int64),
        'circle': tf.io.FixedLenFeature([3], tf.float32)
    })
    return(shape_and_augment_sample(parsed['data'], parsed['dataShape'], augment_params),
           tf.math.multiply(parsed['circle'], tf.constant([1.0/32.0, 1.0/32.0, 1.0/16.0])))


def parse_tfrecord_verify(data_size, example):
    parsed = tf.io.parse_single_example(example, features={
        'data': tf.io.FixedLenFeature([data_size], tf.int64),
        'dataShape': tf.io.FixedLenFeature([3], tf.int64),
        'isPositive': tf.io.FixedLenFeature([1], tf.int64),
        'circle': tf.io.FixedLenFeature([3], tf.float32)
    })
    return tf.reshape(tf.cast(parsed['data'], tf.float32), parsed['dataShape'])


def get_dataset(tfr_ds, batch_size, nnType, data_size, augment_params):
    if (nnType == 'positioner'):
        tfr_ds = tfr_ds.map(lambda x: parse_tfrecord_circle(
            data_size, augment_params, x))
        tfr_ds = tfr_ds.batch(batch_size)
        tfr_ds = tfr_ds.prefetch(batch_size)
        return tfr_ds
    elif (nnType == 'verify'):
        tfr_ds = tfr_ds.map(lambda x: parse_tfrecord_verify(data_size, x))
        return tfr_ds
    else:
        tfr_ds = tfr_ds.map(lambda x: parse_tfrecord_class(
            data_size, augment_params, x))
        tfr_ds = tfr_ds.batch(batch_size)
        tfr_ds = tfr_ds.prefetch(batch_size)
        return tfr_ds


def compiledNN_average_distance(model, model_path, verification_dataset, configuration):
    print('CompiledNN check start')
    predictions_tensorflow = model.predict(
        verification_dataset.batch(configuration['batch_size']),
    )

    def execute(configuration: dict, batched_verification_dataset: numpy.ndarray, result_type: str, result_shape: tuple, result: multiprocessing.sharedctypes.Array, success: multiprocessing.Value):
        model = PyCompiledNN.Model(model_path)
        nn = PyCompiledNN.CompiledNN()
        nn.compile(model)
        predictions_compiled_nn = numpy.frombuffer(
            buffer=result,
            dtype=result_type,
        ).reshape(result_shape)
        for index, sample in enumerate(batched_verification_dataset):
            numpy.copyto(nn.input(0), sample, casting='no')
            nn.apply()
            predictions_compiled_nn[index] = nn.output(0)
        success.value = 1

    success = multiprocessing.Value('b', 0, lock=False)
    batched_verification_dataset = numpy.array([
        sample.numpy()
        for sample in verification_dataset
    ])
    result = multiprocessing.Array(
        typecode_or_type=predictions_tensorflow.dtype.char,
        size_or_initializer=int(numpy.product(predictions_tensorflow.shape)),
        lock=False,
    )
    p = multiprocessing.Process(target=execute, args=(
        configuration,
        batched_verification_dataset,
        predictions_tensorflow.dtype.char,
        predictions_tensorflow.shape,
        result,
        success,
    ))
    p.start()
    p.join()
    if success.value == 1:
        predictions_compiled_nn = numpy.frombuffer(
            buffer=result,
            dtype=predictions_tensorflow.dtype.char,
        ).reshape(predictions_tensorflow.shape)
        mean_squared_error = numpy.square(
            predictions_tensorflow - predictions_compiled_nn,
        ).mean()
        if numpy.isnan(mean_squared_error):
            raise RuntimeError('CompiledNN check mean squared error was NaN')
        print('CompiledNN check finished')
        return float(mean_squared_error)
    print('CompiledNN check finished')
