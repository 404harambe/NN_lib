import csv
import numpy as np
import matplotlib.pyplot as plt


class Dataset:
    def __init__(self):# TODO option initialization
        self.train = None
        self.test = None

    def init_train(self, train):
        self.train = train

    def init_test(self, test):
        self.test = test

    def split_train_k(self, k):
        '''Splits training data into k equal or near-equal subarrays
        result is returned as a tuple where the first element is an array containing
        the input data subarrays and the second element is an array containing the
        target data subarrays'''
        input = np.array_split(self.train[0],k)
        target = np.array_split(self.train[1],k)
        return (input, target)

    def split_train_percent(self, percent):
        '''Splits training data into 2 according to percent. Result is returned as a tuple
        where the first element is an array containing the input data subarrays
        and the second element is an array containing the target data subarrays'''
        l = int(len(self.train[0])*percent/100)
        return (np.array([self.train[0][0:l],self.train[0][l::]]),
                np.array([self.train[1][0:l], self.train[1][l::]]))

class Preprocessor:

    def normalize(self, dataset, method='min-max', norm_output=False):
        if method=='zscore':
            mean = self.get_means(dataset)
            dataset.train[0] = (dataset.train[0] - mean) / \
                               np.std(dataset.train[0])
            if norm_output:
                dataset.train[1] = (dataset.train[1] - np.mean(dataset.train[1],axis=0)) / \
                                   np.std(dataset.train[1])
        elif method=='min-max':
            dataset.train[0] =  (dataset.train[0] - dataset.train[0].min(axis=0)) / \
                               (dataset.train[0].max(axis=0) - dataset.train[0].min(axis=0))
            if norm_output:
                dataset.train[1] = (dataset.train[1] - dataset.train[1].min(axis=0)) / \
                               (dataset.train[1].max(axis=0) - dataset.train[1].min(axis=0))

    def shuffle(self,dataset):
        '''randomly shuffles training data'''
        perm = np.random.permutation(len(dataset.train[0]))
        dataset.train = [dataset.train[0][perm], dataset.train[1][perm]]

    def get_means(self,dataset):
        return np.mean(dataset.train[0],axis=0)

    def get_variance(self,dataset):
        return np.var(dataset.train[0],axis=0)

    def remove_outliers(self, dataset, sensitivity=3):
        mean = self.get_means(dataset)
        var = self.get_variance(dataset)
        out = []
        for el in range(0,len(dataset.train[0])):
            for i in range(0,len(var)):
                if np.abs(dataset.train[0][el][i])>np.abs(mean[i])+sensitivity*var[i]:
                    out.append(el)
        dataset.train[0]=np.delete(dataset.train[0],out,axis=0)
        dataset.train[1]=np.delete(dataset.train[1],out,axis=0)
        return len(out)

    def outlier_range(self,dataset,hop,start,end):
        mean = self.get_means(dataset)
        var = self.get_variance(dataset)
        ax=[]

        x=start
        while x<end:
            c=0
            x=x+hop
            print(x)
            for el in range(0,len(dataset.train[0])):
                for i in range(0,len(var)):
                    if np.abs(dataset.train[0][el][i])>np.abs(mean[i])+x*var[i]:
                        c=c+1
                        break
            ax.append(c)
        
        plt.plot(ax)
        plt.ylabel('outlier detection')
        plt.show()


def load_data(path=None, target=True, header_l=0, targets=0):                       
    '''Loads data into numpy arrays from given path. File at specified path
    must be in CSV format. If target output is in the file it is assumed to occupy
    the last targets columns.
    Attributes:
        path: the path of the CSV file containing the data
        target: set to true to indicate CSV contains target outputs
        header_l: specifies the number of header rows
        targets: specifies the number of targets
        '''
    data = []
    if path==None:
        sys.exit("Path not specified")
    with open(path,'r') as f:
        reader = csv.reader(f)
        for row in reader:
            data.append(row)
    data = data[header_l::]
    if target:
        x = [d[1:-targets] for d in data]
        y = [d[-targets:] for d in data]
        return [np.array(x).astype('float32'), np.array(y).astype('float32')]
    else:
        x = [d[1:] for d in data]
        return [np.array(x).astype('float32'), None]

def split_percent(x_in, y_in, percent):
        '''Splits data into 2 according to percent. Result is returned as a tuple
        where the first element is an array containing the input data subarrays
        and the second element is an array containing the target data subarrays'''
        l = int(len(x_in)*(100-percent)/100)
        return (np.array([x_in[0:l],x_in[l::]]),
                np.array([y_in[0:l], y_in[l::]]))


def load_monk(path):

    data = []
    with open(path, 'r') as f:
        reader = csv.reader(f,delimiter=" ")
        for row in reader:
            data.append(row)

    x = np.array([d[2:-1] for d in data]).astype('int')
    y = [(2*float(d[1])-1) for d in data]


    x = np.array(lazy_one_hot_monk(x)).astype('float32')
    y = np.array(y).astype('int')

    y = y.reshape((y.shape[0],1))

    return x, y



#Don't look at this!#TODO
def lazy_one_hot_monk(x):
    k = [0, 3, 6, 8, 11, 15]
    one_hot_x = []
    for row in x:
        i = 0
        g = np.zeros(17)
        for col in row:
            g[k[i] + col - 1] = 1
            i += 1
        one_hot_x.append(g)
    return one_hot_x


