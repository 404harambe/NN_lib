import numpy as np
import itertools
from NN_lib import optimizers 
from NN_lib import NN 
from NN_lib import regularizations
from NN_lib import loss_functions
from NN_lib import regularizations as  regs
import multiprocessing.pool
import copy


class grid_result:
    '''
    Object with the best hyperparameters and the NN built and trained with them
    '''
    def __init__(self, result_matrix, epochs, batch_size, neurons, activations, optimizer,
                 loss_fun, regularization, rlambda, n_layers, dataset):

        self.neurons = neurons
        self.activations = activations
        self.optimizer = optimizer
        self.loss_fun = loss_fun
        self.regularization = regularization
        self.result_matrix = result_matrix
        self.epochs = epochs
        self.batch_size = batch_size
        self.rlambda = rlambda

        net = NN.NeuralNetwork()
        in_l = dataset.train[0].shape[1]

        #Building the neural network
        for i in range(0, n_layers):

            if (i != n_layers - 1):
                net.addLayer(in_l, neurons[i], activations[i], regularization=regularization[i], rlambda=rlambda[i])
                in_l = neurons[i]
            else:
                net.addLayer(in_l, dataset.train[1].shape[1], activations[i], regularization=regularization[i],
                             rlambda=rlambda[i])
        #Re-train the best network on the whole dataset
        net.fit_ds(dataset, self.epochs, self.optimizer, self.batch_size, self.loss_fun)
        self.NN = net


def grid_search(dataset, epochs, n_layers, neurons, activations=None, regularizations=None,
                optimizers=None, batch_size=[32], loss_fun=None, cvfolds=None,
                val_split=0, rlambda=None, verbose=0, val_set=None, val_loss_fun=None, seed=1):
    '''
    Performs a grid search and returns the results on each configuration as well as an
    object containing the best one along with the re-trained network on the whole training+
    validation dataset. Moreover, returns the prediction of the test set, if contained
    in the dataset object
    :param dataset: input dataset
    :param epochs:
    :param n_layers: number of layers of the network.
    :param neurons: List of lists specifying the neurons configurations. Note that the length
    of each list must be equal to the number of layers.
    :param activations: List of lists specifying the activation functions configurations.
    Note that the length of each list must be equal to the number of layers.
    :param regularizations: List of lists specifying the regularization functions
    configurations. Note that the length of each list must be equal to the number of layers.
    :param optimizers: List specifying the optimizers.
    :param batch_size: List specifying the mini-batch sizes.
    :param loss_fun: List specifying the training loss functions.
    :param cvfolds: Specifies the number of folds in case of cross validation.
    :param val_split: Specifies the percentage of the dataset to be used for validaiton in case
    of hold-out validation.
    :param rlambda: List of lists specifying the regularization values.
    Note that the length of each list must be equal to the number of layers.
    :param verbose: A value of 1 will display the errors and accuracies at the end of
    the training on each configuration, a value >=2 will display the the errors and
    accuracies after every epoch.
    :param val_set: A separate set to be used for validation. Note that this not work in
    combination with hold-out validation or cross validation.
    :param val_loss_fun: The loss function to be used for validation purpose. Defaults to the
    training loss function if only one such function has been specified.
    :return:
    -full_grid: An object containing the configurations and the training and validation losses for
     each epoch as well as the final ones. In case of cross validation it also contains
     the in-fold std for each configuration.
     -best_config: An object containing the best configuration based on the validation loss,
     if validation was done or on the training loss otherwise. It also contains the loss values
     as well as the re-trained network on the whole training+validation sets.
     -prediction: the prediction on the test set if the dataset contained such a set. Otherwise
     None.
    '''
    #If no validation selected, default to 3-fold
    if (cvfolds == None and val_split == 0 and val_set==None): cvfolds = 3
    #If val_split was selected, default folds to 1 and ignore val_set
    if (val_split > 0):
        cvfolds = 1
        val_set = None

    if (cvfolds < 1):
        sys.exit("Specify a positive number of folds")
    if (val_split < 0 or val_split >= 100):
        sys.exit("Validation split must be in the range [0,100)")
    if (cvfolds != 1 and val_split > 0):
        sys.exit("Combined cross validation and validation split is currently unsupported")

    validating = False
    if (cvfolds > 1 or val_split > 0 or val_set!=None): validating = True

    # Build up grid for grid search
    grid = dict()
    grid['epochs'] = epochs
    grid['neurons'] = neurons
    grid['batch_size'] = batch_size
    grid['rlambda'] = rlambda

    if activations == None:
        grid['activations'] = [['linear'] * n_layers]
    else:
        grid['activations'] = activations

    if regularizations == None:
        grid['regularizations'] = [[regs.reguls['L2']] * n_layers]
    else:
        grid['regularizations'] = regularizations

    if optimizers == None:
        grid['optimizers'] = [optimizers.optimizers['SGD']]
    else:
        grid['optimizers'] = optimizers

    if loss_fun == None:
        grid['loss_fun'] = [loss_functions.losses['mse']]
    else:
        grid['loss_fun'] = loss_fun

    if rlambda == None:
        grid['rlambda'] = [[0.0] * n_layers]
    else:
        grid['rlambda'] = rlambda

    if (validating == False and len(grid['loss_fun']) > 1):
        print(grid['loss_fun'])
        sys.exit("Cannot compare multiple loss functions without validation")

    #If multiple loss functions, cannot automatically select validation one
    if (validating and val_loss_fun == None and len(loss_fun) > 1):
        sys.exit("Specify a validation function")

    # If validation and only one training func, use that as validation func as well
    if (validating and val_loss_fun == None and len(loss_fun) == 1):
        val_loss_fun = loss_fun[0]

    grid['val_loss_fun'] = [loss_functions.losses[val_loss_fun]]

    # Generate all possible hyperparameters configurations
    labels, terms = zip(*grid.items())
    # generate list to iterate on
    all_comb = [dict(zip(labels, term)) for term in itertools.product(*terms)]

    # calculate number of configurations
    comb_of_param = len(all_comb)

    # setup matrix to store results (an array is enough if cvfolds returns the avg)
    result_grid = np.zeros(comb_of_param)

    # This list will contain the results for each configuration
    full_grid = []
    k = 0
    tot= len(all_comb)
    for params in all_comb:
        np.random.seed(seed)

        print(k,"/",tot)
        print(params)
        net = NN.NeuralNetwork()
        in_l = dataset.train[0].shape[1]
        # Build NN according to current configuration
        for i in range(0, n_layers):
            net.addLayer(in_l, params['neurons'][i], params['activations'][i],
                         regularization=params['regularizations'][i], rlambda=params['rlambda'][i])
            in_l = params['neurons'][i]

        # Check what kind of validation should be performed
        if (val_split > 0 or cvfolds <= 1 or val_set != None):
            r, _, v, _, history = net.fit_ds(dataset, epochs=params['epochs'], val_split=val_split, val_set=val_set, \
                                             optimizer=params['optimizers'], batch_size=params['batch_size'],
                                             loss_func=params['loss_fun'], val_loss_fun=params['val_loss_fun'],verbose=verbose - 0)
            if v == None:
                #If no validation (val_split=0) then select best based on tr loss
                result_grid[k] = r
            else:
                result_grid[k] = v
            var = 0
        else:

            result_grid[k], var, _, _, _, history = k_fold_validation(dataset, net, epochs=params['epochs'], \
                                                                 optimizer=params['optimizers'], cvfolds=cvfolds,
                                                                 batch_size=params['batch_size'],val_loss_fun=val_loss_fun,
                                                                 loss_func=params['loss_fun'], verbose=verbose - 0)
        if (validating):
            full_grid.append({'configuration': params, 'val_loss': result_grid[k], 'in-fold var':var,'history': history})
        else:  # If no validation was done only put config and other stuff(to add..)
            predd = net.evaluate(dataset.test[0],dataset.test[1])
            print(predd)
            full_grid.append({'configuration': params, 'history': history, 'prediction': predd})
        k = k + 1

    #Fetch best configuration based on validation loss, or training if no validation was done
    min = np.amin(result_grid)
    ind = np.where(result_grid == min)[0][0]
    best_hyper_param = all_comb[ind]
    best_config = grid_result(result_grid, best_hyper_param['epochs'], best_hyper_param['batch_size'],
                              best_hyper_param['neurons'], best_hyper_param['activations'], \
                              best_hyper_param['optimizers'], best_hyper_param['loss_fun'],
                              best_hyper_param['regularizations'], best_hyper_param['rlambda'], n_layers, dataset)

    #Predict on test set, if available
    if (dataset.test != None):
        prediction = best_config.NN.predict(dataset.test[0])
    else:
        prediction = None
    return full_grid, best_config, prediction


def k_fold_validation(dataset, NN, epochs, optimizer, cvfolds=3, batch_size=32,
                      loss_func='mse',val_loss_fun=None, verbose=0):

    '''
    Performs a k-fold cross validation on the dataset
    :param dataset: The input dataset
    :param NN: The neural network to perform the k-cross validation on.
    :param epochs: Number of epochs for the training on each fold.
    :param optimizer: The optimizer to train the network with.
    :param cvfolds: Number of folds.
    :param batch_size: Size of mini-batches
    :param loss_func: The loss function to train with
    :param val_loss_fun: The loss function used for the validation set.
    :param verbose: A value of 1 will display the errors and accuracies at the end of
    the training, a value >=2 will display the the errors and accuracies after every epoch.
    :return: The average final and per epoch losses and accuracies over the folds
    and the in-fold variance
    '''
    x_list, y_list = dataset.split_train_k(cvfolds)
    # Arrays of result
    val_loss = np.zeros((cvfolds))
    val_acc = np.zeros((cvfolds))
    tr_loss = np.zeros((cvfolds))
    tr_acc = np.zeros((cvfolds))
    history = []

    for i in range(0, len(x_list)):

        #Initialize weights randomly
        NN.initialize_random_weights()

        #Prepare the folds
        if i == 0:
            train_x = np.concatenate(x_list[i + 1:])
            train_y = np.concatenate(y_list[i + 1:])
        elif i == len(x_list) - 1:
            train_x = np.concatenate(x_list[:i])
            train_y = np.concatenate(y_list[:i])
        else:
            train_x = np.concatenate((x_list[:i] + x_list[i + 1:]))
            train_y = np.concatenate((y_list[:i] + y_list[i + 1:]))

        validation_x = x_list[i]
        validation_y = y_list[i]

        #Train the model
        tr_loss[i], tr_acc[i], _, _, c = \
            NN.fit(train_x, train_y, epochs, optimizer, batch_size, loss_func, verbose=verbose,
                   val_set=(validation_x, validation_y),val_loss_fun=val_loss_fun)

        val_loss[i], val_acc[i] = NN.evaluate(validation_x, validation_y,loss_fun=val_loss_fun)

        history.append(c)

    r = {'tr_loss': [0] * epochs, 'tr_acc': [0] * epochs, 'val_loss': [0] * epochs, 'val_acc': [0] * epochs}

    #Sum and average over the folds
    for d in history:
        for k in d.keys():
            r[k] = [np.sum(x) for x in zip(d[k], r[k])]

    for k in r.keys():
        for z in range(0, len(r[k])):
            r[k][z] = r[k][z] / cvfolds

    return np.average(val_loss), np.var(val_loss), np.average(val_acc), np.average(tr_loss), np.average(tr_acc), r



#Multithreaded grid search
def grid_thread(dataset, epochs, n_layers, neurons, activations=None, regularizations=None,
                optimizers=None, batch_size=[32], loss_fun=None, cvfolds=None,
                val_split=0, rlambda=None, verbose=0, val_set=None, val_loss_fun=None, trials=1):
    
    def grid_call(seed):

        fg,grid_res, pred = grid_search(dataset, epochs=epochs, batch_size=batch_size,
                                                   n_layers=n_layers, val_split=val_split,activations=activations,
                                                   regularizations=regularizations, rlambda=rlambda,
                                                   cvfolds=cvfolds, val_set=val_set, verbose=verbose,
                                                   loss_fun=loss_fun, val_loss_fun=val_loss_fun,
                                                   neurons=neurons, optimizers=copy.deepcopy(optimizers),seed=seed)
    
        return fg

    fgs = list()
    t_trial = list(range(0, trials))

    pool = multiprocessing.pool.ThreadPool(processes=trials)
    return_list = pool.map(grid_call, t_trial, chunksize=1)

    pool.close()

    return return_list