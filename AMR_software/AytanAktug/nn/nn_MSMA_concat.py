#!/usr/bin/python
#Python 3.6
#nested CV, modified by khu based on Derya Aytan's work: https://bitbucket.org/deaytan/neural_networks/src/master/Neural_networks.py

import os
os.environ["OMP_NUM_THREADS"] = "1" # export OMP_NUM_THREADS=4
os.environ["OPENBLAS_NUM_THREADS"] = "1" # export OPENBLAS_NUM_THREADS=4
os.environ["MKL_NUM_THREADS"] = "1" # export MKL_NUM_THREADS=6
os.environ["VECLIB_MAXIMUM_THREADS"] = "1" # export VECLIB_MAXIMUM_THREADS=4
os.environ["NUMEXPR_NUM_THREADS"] = "1" # export NUMEXPR_NUM_THREADS=6
import sys
# sys.path.append('../')
sys.path.insert(0, os.getcwd())
import time
import torch
import numpy as np
import torch.optim as optim
from torch.autograd import Variable
from sklearn.metrics import matthews_corrcoef
from sklearn.model_selection import ParameterGrid
from sklearn.metrics import roc_curve, auc,classification_report,f1_score
from sklearn import preprocessing
import itertools
import statistics
from src.cv_folds import name2index
from nn.hyperpara import hyper_range,training,OuterLoop_training,training_original,classifier_original,_classifier,_classifier2,_classifier3,Num2l

'''
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
'''
use_cuda = torch.cuda.is_available()
device = torch.device("cuda" if use_cuda else "cpu")
print(device)



def concat_eval(merge_name_train, antibiotics, level, xdata, ydata, p_names,folders_sample_name,path_x_test, path_y_test, cv,
                f_scaler,f_fixed_threshold,f_no_early_stop, f_phylotree,f_kma, f_optimize_score,name_weights):
    '''Normal CV, i.e. one loop of outer CV of nested CV.'''

    # data
    data_x = np.loadtxt(xdata, dtype="float")
    data_y = np.loadtxt(ydata)


    x_test = np.loadtxt(path_x_test, dtype="float")
    y_test = np.loadtxt(path_y_test)
    x_test = torch.from_numpy(x_test).float()
    y_test = torch.from_numpy(y_test).float()
    x_test = x_test.to(device)


    out_cv=0#only for saving scores purpose.
    # output results list
    pred_test = []  # probabilities are for the validation set
    pred_test_binary = []  # binary based on selected
    thresholds_selected_test = []  # cv len, each is the selected threshold.
    mcc_test = []  # MCC results for the test data
    f1_test = []
    score_report_test = []
    aucs_test = []  # all AUC values for the test data
    hyperparameters_test = []
    actual_epoc_test = []
    actual_epoc_test_std = []
    true_Y=[] #corresponding true Y
    sampleNames_test=[] #sample names
    predictY_test=[] ##predicted Y
    # -------------------------------------------------------------------------------------------------------------------
    # model varibales
    anti_number = data_y[0].size  # number of antibiotics
    nlabel = data_y[0].size  # number of neurons in the output layer
    D_input = len(data_x[0])  # number of neurons in the input layer



    # CV folds
    folders_sample=name2index.Get_index(folders_sample_name,p_names)
    train_val_samples = folders_sample


    #For validation scores output
    Validation_mcc_thresholds = []  # inner CV *11 thresholds value
    Validation_f1_thresholds = []  # inner CV *11 thresholds value
    Validation_auc = []  # inner CV
    Validation_actul_epoc = []


    hyper_space = hyper_range(anti_number, f_no_early_stop, antibiotics)
    for innerCV in range(cv):  # cv=6. e.g. 0,1,2,3,4,5 #todo check
        print('Starting outer: ', str(out_cv), '; inner: ', str(innerCV), ' inner loop...')

        val_samples = train_val_samples[innerCV]
        train_samples = train_val_samples[:innerCV] + train_val_samples[innerCV + 1:]  # only works for list, not np
        train_samples = list(itertools.chain.from_iterable(train_samples))


        x_train, x_val = data_x[train_samples], data_x[val_samples]  # only np
        y_train, y_val = data_y[train_samples], data_y[val_samples]
        print('sample length and feature length for inner CV(train & val):', len(x_train), len(x_train[0]), len(x_val),
              len(x_val[0]))

        # normalize the data
        if f_scaler == True:
            scaler = preprocessing.StandardScaler().fit(x_train)
            x_train = scaler.transform(x_train)
            x_val = scaler.transform(x_val)


        x_train = torch.from_numpy(x_train).float()
        y_train = torch.from_numpy(y_train).float()
        x_val = torch.from_numpy(x_val).float()
        y_val = torch.from_numpy(y_val).float()

        ###################
        # 1. train the model #
        ###################
        # print(hyper_space)
        Validation_mcc_thresholds_split = []  # inner CV *11 thresholds value.June 21: grid_number
        Validation_f1_thresholds_split = []  # inner CV *11 thresholds value.June 21: grid_number
        Validation_auc_split = []  # inner CV
        Validation_actul_epoc_split = []
        # only for validation score saving
        score_report_val_sub = []
        aucs_val_sub = []
        mcc_val_sub = []
        for grid_iteration in np.arange(len(list(ParameterGrid(hyper_space)))):

            # --------------------------------------------------------------------
            epochs = list(ParameterGrid(hyper_space))[grid_iteration]['epochs']
            n_hidden = list(ParameterGrid(hyper_space))[grid_iteration]['n_hidden']
            learning = list(ParameterGrid(hyper_space))[grid_iteration]['lr']
            n_cl = list(ParameterGrid(hyper_space))[grid_iteration]['classifier']
            dropout = list(ParameterGrid(hyper_space))[grid_iteration]['dropout']
            patience = list(ParameterGrid(hyper_space))[grid_iteration]['patience']
            # generate a NN model
            if n_cl == 1:
                classifier = _classifier(nlabel, D_input, n_hidden,dropout)
            elif n_cl == 2:
                classifier = _classifier2(nlabel, D_input, n_hidden, dropout)
            elif n_cl == 3:
                classifier = _classifier3(nlabel, D_input, n_hidden, dropout)

            classifier.to(device)
            # generate the optimizer - Stochastic Gradient Descent
            optimizer = optim.SGD(classifier.parameters(), lr=learning)
            optimizer.zero_grad()  # Clears existing gradients from previous epoch
            # loop:
            print(merge_name_train, antibiotics, level, out_cv, innerCV)
            start = time.time()
            if f_no_early_stop == True:
                classifier, actual_epoc = training_original(classifier, epochs, optimizer, x_train, y_train,
                                                            anti_number)
            else:
                classifier, actual_epoc = training(classifier, epochs, optimizer, x_train, y_train, x_val, y_val,
                                                   anti_number, patience)
            Validation_actul_epoc_split.append(actual_epoc)
            end = time.time()
            print('Time used: ', end - start)
            # ==================================================
            ######################
            # 2. validate the model #
            ######################

            classifier.eval()  # eval mode
            pred_val_sub = []
            x_val = x_val.to(device)
            for v, v_sample in enumerate(x_val):

                # val = Variable(torch.FloatTensor(v_sample)).view(1, -1)
                val = Variable(v_sample).view(1, -1)
                output_test = classifier(val)
                out = output_test
                temp = []
                for h in out[0]:
                    temp.append(float(h))
                pred_val_sub.append(temp)

            pred_val_sub = np.array(pred_val_sub)  # for this innerCV at this out_cv
            score_report_val_sub_anti = []
            mcc_val_sub_anti = []
            aucs_val_sub_anti = []


            if f_optimize_score == 'auc':
                for i in range(anti_number):
                    comp = []
                    if anti_number == 1:#no use.
                        print('Error: Please check your antibiotic number')
                        exit(1)
                    else:  # multi-out

                        for t in range(len(y_val)):
                            if -1 != y_val[t][i]:
                                comp.append(t)

                        y_val_anti = y_val[comp]
                        pred_val_sub_anti = pred_val_sub[comp]

                        fpr, tpr, _ = roc_curve(y_val_anti[:, i], pred_val_sub_anti[:, i], pos_label=1)
                        roc_auc = auc(fpr, tpr)
                        aucs_val_sub_anti.append(roc_auc)
                        #
                        # turn probability to binary.
                        threshold_matrix = np.full(pred_val_sub_anti.shape, 0.5)#use 0.5 as the threshold
                        pred_val_sub_anti_binary = (pred_val_sub_anti > threshold_matrix)
                        pred_val_sub_anti_binary = 1 * pred_val_sub_anti_binary

                        report = classification_report(y_val_anti[:, i], pred_val_sub_anti_binary[:, i], labels=[0, 1],
                                                       output_dict=True)
                        score_report_val_sub_anti.append(report)
                        mcc = matthews_corrcoef(y_val_anti[:, i], pred_val_sub_anti_binary[:, i])

                        mcc_val_sub_anti.append(mcc)


                if anti_number > 1:  # multi-out, scores based on mean of all the involved antibotics
                    aucs_val_sub_mean = statistics.mean(aucs_val_sub_anti)  # dimension: n_anti to 1
                    Validation_auc_split.append(aucs_val_sub_mean)  # D: n_innerCV

                    score_report_val_sub.append(score_report_val_sub_anti)
                    aucs_val_sub.append(aucs_val_sub_anti)
                    mcc_val_sub.append(mcc_val_sub_anti)

            # ====================================================
            elif f_optimize_score == 'f1_macro':
                # Calculate macro f1. for thresholds from 0 to 1.
                mcc_sub = []
                f1_sub = []

                for threshold in np.arange(0, 1.1, 0.1):
                    # predictions for the test data
                    # turn probabilty to binary
                    threshold_matrix = np.full(pred_val_sub.shape, threshold)
                    y_val_pred = (pred_val_sub > threshold_matrix)
                    y_val_pred = 1 * y_val_pred
                    mcc_sub_anti = []
                    f1_sub_anti = []
                    for i in range(anti_number):

                        comp = []  # becasue in the multi-species model, some species,anti combination are missing data
                        # so those won't be counted when evaluating scores.

                        if anti_number == 1:
                            print('please check your antibiotic number')
                            exit(1)
                            # mcc = matthews_corrcoef(y_val, y_val_pred)
                            # f1 = f1_score(y_val, y_val_pred, average='macro')
                            # mcc_sub.append(mcc)
                            # f1_sub.append(f1)

                        else:  # multi-out
                            for t in range(len(y_val)):
                                if -1 != y_val[t][i]:
                                    comp.append(t)
                            y_val_multi_sub = y_val[comp]
                            y_val_pred_multi_sub = y_val_pred[comp]
                            mcc = matthews_corrcoef(y_val_multi_sub[:, i], y_val_pred_multi_sub[:, i])
                            f1 = f1_score(y_val_multi_sub[:, i], y_val_pred_multi_sub[:, i], average='macro')
                            mcc_sub_anti.append(mcc)
                            f1_sub_anti.append(f1)

                            fpr, tpr, _ = roc_curve(y_val_multi_sub[:, i], y_val_pred_multi_sub[:, i], pos_label=1)
                            roc_auc = auc(fpr, tpr)
                            report = classification_report(y_val_multi_sub[:, i], y_val_pred_multi_sub[:, i],
                                                           labels=[0, 1],
                                                           output_dict=True)
                            mcc_val_sub_anti.append(mcc)
                            score_report_val_sub_anti.append(report)
                            aucs_val_sub_anti.append(roc_auc)
                    if anti_number > 1:  # multi-out, scores based on mean of all the involved antibotics
                        mcc_sub.append(statistics.mean(mcc_sub_anti))  # mcc_sub_anti dimension: n_anti
                        f1_sub.append(statistics.mean(f1_sub_anti))
                        # --for validation scores output
                        score_report_val_sub.append(score_report_val_sub_anti)
                        aucs_val_sub.append(aucs_val_sub_anti)
                        mcc_val_sub.append(mcc_val_sub_anti) #wrong, Sep 28th 2022
                #finish one grid combination.
                Validation_mcc_thresholds_split.append(mcc_sub)
                Validation_f1_thresholds_split.append(f1_sub)


        #finish grid search in one inner loop
        Validation_mcc_thresholds.append(Validation_mcc_thresholds_split)  # inner CV * hyperpara_combination
        Validation_f1_thresholds.append(Validation_f1_thresholds_split)  # inner CV * hyperpara_combination
        Validation_auc.append(Validation_auc_split)  # inner CV * hyperpara_combination
        Validation_actul_epoc.append(Validation_actul_epoc_split)  # inner CV * hyperpara_combination




    # finish evaluation in the inner loop.
    if f_fixed_threshold == True and f_optimize_score == 'f1_macro':  # finished.May 30. 7am
        thresholds_selected = 0.5
        Validation_f1_thresholds = np.array(Validation_f1_thresholds)
        Validation_f1_thresholds = Validation_f1_thresholds.mean(axis=0)
        Validation_actul_epoc = np.array(Validation_actul_epoc)
        Validation_actul_epoc_std = Validation_actul_epoc.std(axis=0)
        Validation_actul_epoc = Validation_actul_epoc.mean(axis=0)

        # select the inner loop index with the highest f1 score in the column w.r.t. 0.5
        aim_column = np.where(np.arange(0, 1.1, 0.1) == 0.5)
        aim_f1 = Validation_f1_thresholds[:, aim_column]
        ind = np.unravel_index(np.argmax(aim_f1, axis=None), aim_f1.shape)
        hyperparameters_test.append(list(ParameterGrid(hyper_space))[ind[0]])
        actual_epoc_test.append(Validation_actul_epoc[ind[0]])
        actual_epoc_test_std.append(Validation_actul_epoc_std[ind[0]])



    elif f_fixed_threshold == False and f_optimize_score == 'f1_macro':  # finished.May 30. 7am
        # select the inner loop index,and threshold with the highest f1 score in the matrix
        Validation_f1_thresholds = np.array(Validation_f1_thresholds)
        Validation_f1_thresholds = Validation_f1_thresholds.mean(axis=0)
        Validation_actul_epoc = np.array(Validation_actul_epoc)

        Validation_actul_epoc_std = Validation_actul_epoc.std(axis=0)
        Validation_actul_epoc = Validation_actul_epoc.mean(axis=0)
        ind = np.unravel_index(np.argmax(Validation_f1_thresholds, axis=None), Validation_f1_thresholds.shape)
        thresholds_selected = np.arange(0, 1.1, 0.1)[ind[1]]
        hyperparameters_test.append(list(ParameterGrid(hyper_space))[ind[0]])
        actual_epoc_test.append(Validation_actul_epoc[ind[0]])
        actual_epoc_test_std.append(Validation_actul_epoc_std[ind[0]])


    elif f_optimize_score == 'auc':  # finished.May 30. 7am

        thresholds_selected = 0.5
        Validation_auc = np.array(Validation_auc)
        Validation_auc = Validation_auc.mean(axis=0)
        Validation_actul_epoc = np.array(Validation_actul_epoc)#innerCV*hyper_number
        Validation_actul_epoc_std = Validation_actul_epoc.std(axis=0)
        Validation_actul_epoc = Validation_actul_epoc.mean(axis=0)#hyper_number
        ind = np.unravel_index(np.argmax(Validation_auc, axis=None), Validation_auc.shape)
        hyperparameters_test.append(list(ParameterGrid(hyper_space))[ind[0]])
        actual_epoc_test.append(Validation_actul_epoc[ind[0]])  # actually it's mean epoch for that hyperpara.
        actual_epoc_test_std.append(Validation_actul_epoc_std[ind[0]])


    thresholds_selected_test.append(thresholds_selected)

    # finish innner loop
    # =======================================================
    # 3. Re-train on both train and val data with the selected hyper-para

    print('Outer loop, testing.')
    train_val_samples = list(itertools.chain.from_iterable(train_val_samples))
    x_train_val = data_x[train_val_samples]  # only np
    y_train_val = data_y[train_val_samples]

    if f_scaler == True:
        scaler = preprocessing.StandardScaler().fit(x_train_val)
        x_train_val = scaler.transform(x_train_val)
        x_test = scaler.transform(x_test)

    x_train_val = torch.from_numpy(x_train_val).float()
    y_train_val = torch.from_numpy(y_train_val).float()

    # -
    # epochs_testing = hyperparameters_test[out_cv]['epochs']
    n_hidden = hyperparameters_test[out_cv]['n_hidden']
    learning = hyperparameters_test[out_cv]['lr']
    n_cl = hyperparameters_test[out_cv]['classifier']
    dropout = hyperparameters_test[out_cv]['dropout']
    # generate a NN model
    if n_cl == 1:
        classifier = _classifier(nlabel, D_input, n_hidden,
                                 dropout)  # reload, after testing(there is fine tune traning!)
    elif n_cl == 2:
        classifier = _classifier2(nlabel, D_input, n_hidden, dropout)
    elif n_cl == 3:
        classifier = _classifier3(nlabel, D_input, n_hidden, dropout)
    print('testing hyper-parameter: ', hyperparameters_test[out_cv])
    classifier.to(device)
    # generate the optimizer - Stochastic Gradient Descent
    optimizer = optim.SGD(classifier.parameters(), lr=learning)
    optimizer.zero_grad()  # Clears existing gradients from previous epoch
    classifier.train()
    print('actual_epoc_test[out_cv]', actual_epoc_test[out_cv])
    classifier = training_after_optimize(classifier, int(actual_epoc_test[out_cv]), optimizer, x_train_val, y_train_val,
                                    anti_number)



    torch.save(classifier.state_dict(), name_weights)
    classifier.eval()

    pred_test_sub = []
    for a, a_sample in enumerate(x_test):
        tested = Variable(a_sample).view(1, -1)
        # tested = Variable(torch.FloatTensor(a_sample)).view(1, -1)
        output_test = classifier(tested)
        out = output_test
        temp = []
        for h in out[0]:
            temp.append(float(h))
        pred_test_sub.append(temp)
    pred_test_sub = np.array(pred_test_sub)
    pred_test.append(pred_test_sub)  # len= y_test
    print('x_test', x_test.shape)
    print('pred_test_sub', pred_test_sub.shape)
    print('y_test', y_test.shape)

    # turn probability to binary.
    threshold_matrix = np.full(pred_test_sub.shape, thresholds_selected)
    pred_test_binary_sub = (pred_test_sub > threshold_matrix)
    pred_test_binary_sub = 1 * pred_test_binary_sub

    y_test = np.array(y_test)
    pred_test_binary.append(pred_test_binary_sub)


    f1_test_anti = []  # multi-out
    score_report_test_anti = []  # multi-out
    aucs_test_anti = []  # multi-out
    mcc_test_anti = []  # multi-out

    for i in range(anti_number):
        comp = []
        if anti_number == 1:
            mcc = matthews_corrcoef(y_test, pred_test_binary_sub)
            f1 = f1_score(y_test, pred_test_binary_sub, average='macro')
            report = classification_report(y_test, pred_test_binary_sub, labels=[0, 1], output_dict=True)
            roc_auc = auc(fpr, tpr)
        else:  # multi-out

            for t in range(len(y_test)):
                if -1 != y_test[t][i]:
                    comp.append(t)
            y_test_anti = y_test[comp]
            pred_test_binary_sub_anti = pred_test_binary_sub[comp]
            pred_test_sub_anti = pred_test_sub[comp]  # June 21st, auc bugs
            if comp != []:
                mcc = matthews_corrcoef(y_test_anti[:, i], pred_test_binary_sub_anti[:, i])
                f1 = f1_score(y_test_anti[:, i], pred_test_binary_sub_anti[:, i], average='macro')
                fpr, tpr, _ = roc_curve(y_test_anti[:, i], pred_test_sub_anti[:, i], pos_label=1)# June 21st, auc bugs
                report = classification_report(y_test_anti[:, i], pred_test_binary_sub_anti[:, i], labels=[0, 1],
                                               output_dict=True)
                roc_auc = auc(fpr, tpr)
                f1_test_anti.append(f1)
                score_report_test_anti.append(report)
                aucs_test_anti.append(roc_auc)
                mcc_test_anti.append(mcc)
            else:
                f1_test_anti.append(None)
                score_report_test_anti.append(None)
                aucs_test_anti.append(None)
                mcc_test_anti.append(None)

    # summarise each outer loop's results.
    if anti_number > 1:
        f1_test.append(f1_test_anti)
        score_report_test.append(score_report_test_anti)
        aucs_test.append(aucs_test_anti)  # multi-out
        mcc_test.append(mcc_test_anti)
    else:
        f1_test.append(f1)
        score_report_test.append(report)
        aucs_test.append(roc_auc)  # single-out
        mcc_test.append(mcc)

    # aucs_test_all.append(aucs)  ## multi-out
    true_Y.append(y_test.tolist())

    predictY_test.append(pred_test_binary_sub.tolist())

    print('thresholds_selected_test', thresholds_selected_test)
    print('f1_test', f1_test)
    print('mcc_test', mcc_test)
    print('hyperparameters_test', hyperparameters_test)

    actual_epoc_test=Num2l(actual_epoc_test)
    actual_epoc_test_std=Num2l(actual_epoc_test_std)


    score = {'f1_test':f1_test,'score_report_test':score_report_test,'aucs_test':aucs_test,'mcc_test':mcc_test,
             'predictY_test':predictY_test,'ture_Y':true_Y, 'thresholds_selected_test':thresholds_selected_test,
             'hyperparameters_test':hyperparameters_test,'actual_epoc_test':actual_epoc_test,'actual_epoc_test_std':actual_epoc_test_std}

    torch.cuda.empty_cache()
    return score


