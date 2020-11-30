import tensorflow as tf
import pathlib
import subprocess
import json


def run(payload):
    genome = payload['genome']
    configuration = payload['configuration']
    result = {
        'compiledNN_result': 500.0,
        'accuracy':0,
    }

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
                                    configuration['input_size_x'] * configuration['input_size_y'],
                                    configuration['augment_params'])

        test_dataset = get_dataset(tf.data.TFRecordDataset(configuration['test_dataset']),
                                configuration['batch_size'],
                                configuration['type'],
                                configuration['input_size_x'] * configuration['input_size_y'],
                                configuration['augment_params'])

        verify_dataset = get_dataset(tf.data.TFRecordDataset(configuration['test_dataset']),  #TODO: not use test_dataset here
                                    configuration['batch_size'],
                                    'verify',
                                    configuration['input_size_x'] * configuration['input_size_y'],
                                    configuration['augment_params'])

        current_lr = genome["initial_learning_rate"]

        for ep in range(genome["training_epochs"]):
            model.fit(
                train_dataset,
                epochs=1)
            current_lr *= genome["learning_rate_factor_per_epoch"]
            model.optimizer.lr.assign(current_lr)

        evaluate_result = {
            name: value
            for name, value in zip(['loss'] + configuration['metrics'],
                                model.evaluate(test_dataset))
        }

        for key in evaluate_result:
            result[key] = evaluate_result[key]

        #TODO: change tmp model path ?
        tmp_model_path = pathlib.Path("tmp_model.hdf5")
        tf.keras.models.save_model(
            model,
            str(tmp_model_path),
            save_format='h5')

        result['compiledNN_result'] = compiledNN_average_distance(model,
                                                                  tmp_model_path,
                                                                  verify_dataset,
                                                                  configuration)


        tmp_model_path.unlink()

    except Exception as e:
        result['exception'] = str(e)

    tf.keras.backend.clear_session()
    return result


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
                augment_params["random_brightness_delta"],
                seed=augment_params["random_brightness_seed"])
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
    if (nnType == "positioner"):
        tfr_ds = tfr_ds.map(lambda x: parse_tfrecord_circle(data_size, augment_params, x))
        tfr_ds = tfr_ds.batch(batch_size)
        tfr_ds = tfr_ds.prefetch(batch_size)
        return tfr_ds
    elif (nnType == "verify"):
        tfr_ds = tfr_ds.map(lambda x: parse_tfrecord_verify(data_size, x))
        return tfr_ds
    else:
        tfr_ds = tfr_ds.map(lambda x: parse_tfrecord_class(data_size, augment_params, x))
        tfr_ds = tfr_ds.batch(batch_size)
        tfr_ds = tfr_ds.prefetch(batch_size)
        return tfr_ds


def compiledNN_average_distance(model, model_path, verification_dataset, configuration):
    print("compiledNN check start")
    verification_dataset_size = sum(1 for _ in verification_dataset)
    model_predictions = model.predict(verification_dataset.batch(verification_dataset_size))

    compiled_nn_process = subprocess.Popen(
        args=[configuration['compiledNN_predicter'], model_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )

    verification_string = '\n'.join([
        json.dumps(sample.numpy().ravel().tolist())
        for sample in verification_dataset
    ])

    compiled_nn_output, compiled_nn_errors = compiled_nn_process.communicate(
        input=verification_string.encode('utf-8'),
    )

    if compiled_nn_errors is not None:
        raise RuntimeError(compiled_nn_errors)

    distance = 0
    value_counter = 0
    for model_prediction, compiled_nn_prediction in zip(model_predictions, compiled_nn_output.splitlines()):
        for model_value, compiled_nn_value in zip(model_prediction, json.loads(compiled_nn_prediction)):
            value_counter += 1
            if compiled_nn_value is None: #TODO: investigate this / log error
                print("compiled_nn_value is None...")
                #return 100.0
            distance += abs(model_value - compiled_nn_value)

    if value_counter == 0: #TODO: investigate this / log error
        print("compiledNN value_counter == 0...")
        #return 200.0

    print("compiledNN check finished")
    return (distance / value_counter)
