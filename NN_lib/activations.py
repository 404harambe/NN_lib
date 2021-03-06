import sys
import numpy as np

class Activation:

    def __init__(self, f, dxf):
        self.f = f
        self.dxf = dxf

def validate_activation(activation):
    # Check whether the user provided a properly formatted loss function
    if isinstance(activation, Activation):
        return activation
    else:
        # Otherwise check whether a the specified loss function exists
        try:
            return activations[activation]
        except KeyError:
            sys.exit("Activation undefined")


def sigmoid(x):
    return 1 / (1 + np.exp(-x))

def sigmoddxf(x):
    return x * (1 - x)


def linear(x):
    return x

def lineardxf(x):
    return np.ones_like(x)


def tanh(x):
    return np.tanh(x)

def tanhdx(x):
    return (1 - (np.power(x, 2)))


def relu(x):
    return np.maximum(x, 0)

def reludx(x):
    return 1 * (x > 0)


def softmax(x):
    e = np.exp(x - np.max(x, axis=-1)[..., None])
    e /= np.sum(e, axis=-1)[..., None]
    #Clip to avoid numerical errors
    e[e < 1e-10] = 1e-10
    return e

def softmaxdx(x):
    res = []
    for i in range(0,len(x)):
        s = x[i].reshape(-1,1)
        r = np.diagflat(s) - np.dot(s, s.T)
        res.append(r)
    return np.array(res)

activations = dict()
activations["linear"] = Activation(linear, lineardxf)
activations["sigmoid"] = Activation(sigmoid, sigmoddxf)
activations["tanh"] = Activation(tanh, tanhdx)
activations["softmax"] = Activation(softmax, softmaxdx)
activations["relu"] = Activation(relu, reludx)
