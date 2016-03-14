__author__ = 'olav'

import numpy as np
import sys, os
import scipy.ndimage as morph

sys.path.append(os.path.abspath("./"))

from augmenter import Creator
from data import AerialDataset
import tools.util as util

'''
TODO: Save points to file.
'''

class PrecisionRecallCurve(object):

    def __init__(self, dataset_path, model_params, model_config, dataset_config):
        self.params = model_params
        self.model_config = model_config
        self.model_config.hidden_dropout = 0
        self.dataset_config = dataset_config
        self.dataset_path = dataset_path


    def get_curves_datapoints(self, batch_size, dataset=None):
        if not dataset:
            print('---- Creating dataset')
            dataset = self._create_dataset()

        print('---- Generating output predictions using current model')
        predictions, labels = self._predict_patches(dataset, batch_size)
        print('---- Calculating precision and recall')
        datapoints = self._get_datapoints(predictions, labels)
        print('---- Got {} datapoints from tests'.format(len(datapoints)))
        return datapoints


    def _create_dataset(self):
        dim = (self.dataset_config.input_dim, self.dataset_config.output_dim)
        path = self.dataset_path
        preprocessing = self.dataset_config.use_preprocessing
        print("---- Using preprossing: {}".format(preprocessing))
        std = self.dataset_config.dataset_std
        samples_per_image = 400
        creator = Creator(path, dim=dim, preproccessing=preprocessing, std=std)
        creator.load_dataset()
        #Creating a shared variable of sampled test data
        return AerialDataset.shared_dataset(creator.sample_data(creator.test, samples_per_image), cast_to_int=True)


    def _predict_patches(self, dataset, batch_size):
        '''
        Using the params.pkl or instantiated model to create patch predictions.
        '''
        dim = self.dataset_config.output_dim
        compute_output = util.create_predictor(dataset, self.model_config, self.params, batch_size)
        result_output, result_label = util.batch_predict(compute_output, dataset, dim, batch_size)

        return result_output, result_label


    def _get_datapoints(self, predictions, labels):
        '''
        Precision and recall found for different threshold values. For each value a binary output image is made.
        The threshold indicate that for a pixel value above threshold value is considered a road pixel.
        This generate different values for precision and recall and highlight the trade off between precision and recall.
        '''

        #Results in a slack of 3 pixels.
        labels_with_slack = self._apply_buffer(labels, 3)

        tests = np.arange(0.0001 , 0.995, 0.01)
        datapoints = []
        for threshold in tests:
            binary_arr = util.create_threshold_image(predictions, threshold)

            precision = self._get_precision(labels_with_slack, binary_arr)
            recall = self._get_recall(labels_with_slack, binary_arr)
            datapoints.append({"precision": precision, "recall": recall, "threshold": threshold})
        return datapoints


    def _apply_buffer(self, labels, buffer):
        dim = self.dataset_config.output_dim
        nr_labels = labels.shape[0]
        labels2D = np.array(labels)
        labels2D  = labels2D.reshape(nr_labels, dim, dim)
        struct_dim = (buffer * 2) + 1
        struct = np.ones((struct_dim, struct_dim), dtype=np.uint8)

        for i in range(nr_labels):
            labels2D[i] = morph.binary_dilation(labels2D[i], structure=struct).astype(np.uint8)
            #if np.amax(labels2D[i] > 0):
            #    print(labels2D[i].astype(np.uint8))
            #    print(morph.binary_dilation(labels2D[i], structure=struct).astype(np.uint8))
            #    raise
        labels_with_slack = labels2D.reshape(nr_labels, dim*dim)
        return labels_with_slack


    def _get_precision(self, labels, thresholded_output):
        '''
        Precision between label and output at threshold t.
        Calculate the accuracy of road pixel detection.
        First all positives are counted from output, as well as the true positive. That is road pixels both marked
        in the label and the output. All positives minus true positive gives the false positives. That is predicted
        road pixels which is not marked on the label.
        '''
        total_positive = np.count_nonzero(thresholded_output)
        true_positive = np.count_nonzero(np.array(np.logical_and(labels,  thresholded_output), dtype=np.uint8))

        if total_positive == 0:
            return 0.0

        return true_positive / float(total_positive)


    def _get_recall(self, labels, thresholded_output):
        '''
        Recall between label and output at threshold t.
        See the degree of which the prediction include all positive examples in label.
        So first all postive instances in label are counted (road pixels)
        Then the label and output is compared: In cells where both label and output are one, is
        considered an successful extraction. If output cells are all 1, for all postive pixels in label, the
        recall rate will be 1. If output misses some road pixels this rate will decline.
        '''
        total_positive = np.count_nonzero(labels)
        true_positive = np.count_nonzero(np.array(np.logical_and(labels,  thresholded_output), dtype=np.uint8))

        if total_positive == 0:
            return 0.0

        return true_positive / float(total_positive)

