__author__ = 'olav'

import sys, os
import theano.tensor as T
import theano
import numpy as np

sys.path.append(os.path.abspath("./"))
from wrapper import create_output_func
from model import ConvModel


def create_threshold_image(image, threshold):
    binary_arr = np.ones(image.shape)
    low_values_indices = image <= threshold  # Where values are low
    binary_arr[low_values_indices] = 0  # All low values set to 0
    return binary_arr


def resize(image, size):
    return image.resize( [int(size * s) for s in image.size] )


def create_predictor(dataset, model_config, model_params, batch_size):
    x = T.matrix('x')
    y = T.imatrix('y')
    drop = T.iscalar('drop')
    index = T.lscalar()
    model = ConvModel(model_config, verbose=True)
    model.build(x, drop, batch_size, init_params=model_params)
    return create_output_func(dataset, x, y, drop, [index], model.get_output_layer(), batch_size)


def create_simple_predictor(model_config, model_params):
    #TODO: Does this single predictor even work?
    data = T.matrix('data')
    x = T.matrix('x')
    drop = T.iscalar('drop')
    batch_size = 1
    model = ConvModel(model_config, verbose=True)
    model.build(x, drop, batch_size, init_params=model_params)
    return model.create_predict_function(x, drop, data)


def batch_predict(predictor, dataset, dim, batch_size):
    examples = dataset[0].eval().shape[0]
    nr_of_batches = int(examples/ batch_size)
    result_output = np.empty((examples, dim*dim), dtype=theano.config.floatX)
    result_label = np.empty((examples, dim*dim), dtype=theano.config.floatX)

    for i in range(nr_of_batches):
        output, label = predictor(i)
        result_output[i*batch_size: (i+1)*batch_size] = output
        result_label[i*batch_size: (i+1)*batch_size] = label

    return result_output, result_label
