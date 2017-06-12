import time
from distutils.dir_util import copy_tree
import os
import json
import random
import numpy as np

import tensorflow as tf
import memory
import keras.backend as K
from ActorNetwork import ActorNetwork
from CriticNetwork import CriticNetwork

class DDPG:
    def __init__(self, outputs, memorySize, discountFactor,
                 learningRate_Critic, learningRate_Actor, target_update_rate,
                 img_rows, img_cols, img_channels, target_size):
        """
        Parameters:
            - outputs: output size
            - memorySize: size of the memory that will store each state
            - discountFactor: the discount factor (gamma)
            - learningRate: learning rate
            - learnStart: steps to happen before for learning. Set to 128
        """
        self.action_size = outputs
        self.memory = memory.Memory(memorySize)
        self.discountFactor = discountFactor
        self.learningRateCritic = learningRate_Critic
        self.learningRateActor = learningRate_Actor
        self.img_rows = img_rows
        self.img_cols = img_cols
        self.img_channels = img_channels
        self.target_update_rate = target_update_rate
        self.target_size = target_size

        self.img_shape = (self.img_channels, self.img_rows, self.img_cols)
        if K.image_dim_ordering() == 'tf':
            self.img_shape = (self.img_rows, self.img_cols, self.img_channels)


        with tf.device('/gpu:1'):
            config = tf.ConfigProto()
            config.gpu_options.allow_growth = True
            self.sess = tf.Session(config=config)
            K.set_session(self.sess)

        print 'tf config!'

        self.actor = ActorNetwork(self.sess, self.img_shape, self.action_size,  self.target_update_rate, self.learningRateActor, self.target_size)
        print 'actor'
        self.critic = CriticNetwork(self.sess, self.img_shape, self.action_size,  self.target_update_rate, self.learningRateCritic, self.target_size)
        print 'critic'


    def updateTargetNetwork(self,model,target,updaterate):
        weightMatrix = []
        for layer in model.layers:
            weights = layer.get_weights()
            weightMatrix.append(weights)
        i = 0
        for layer in target.layers:
            weights_pre = layer.get_weights()
            weights = updaterate * weightMatrix[i] + (1 - updaterate) * weights_pre
            layer.set_weights(weights)
            i += 1


    # select the action with the highest Q value
    def Action_Noise(self, action_pred, explorationRate):

        #theta = np.array([0.6,1,1])
        #sigma = np.array([0.3,0.1,0.05])
        #noise = explorationRate * self.OU_noise(action_pred,  0.0 , theta = 0.6, sigma = 0.3)

        #action = action_pred + noise
        action = action_pred
        for i in range(len(action[0])):
            noise = np.random.normal(0.5,0.5)
            action[0][i] = (1 - explorationRate) * action_pred[0][i] + explorationRate * noise
            action[0][i] = max(0,action[0][i])
            action[0][i] = min(1,action[0][i])


        return action[0]

    def addMemory(self, state, action, reward, newState, isFinal, targetID):
        self.memory.addMemory(state, action, reward, newState, isFinal, targetID)


    def getMemorySize(self):
        return self.memory.getCurrentSize()


    def learnOnMiniBatch(self, miniBatchSize):
        # sample experience memory
        state_batch, action_batch, reward_batch, newState_batch, isFinal_batch, targetID_batch \
            = self.memory.getMiniBatch(miniBatchSize)

        isFinal_batch = np.array(isFinal_batch) + 0
        targetID_batch = np.array(targetID_batch)
        action_batch = np.array(action_batch)
        state_batch = np.array(state_batch)

        # feed forward actor
        actor_input = [np.array(newState_batch),targetID_batch]
        actor_output = self.actor.target_model.predict_on_batch(actor_input)

        # feed forward critic
        critic_input = [np.array(newState_batch),np.array(actor_output),targetID_batch]
        qValuesNewState_batch = self.critic.target_model.predict_on_batch(critic_input)

        # update Value
        Y_value = np.zeros([miniBatchSize, self.action_size])
        for k in range(miniBatchSize):
            Y_value[k] = reward_batch[k] + (1 - isFinal_batch[k]) * self.discountFactor * qValuesNewState_batch[k]

        #print action_batch
        #print Y_value.shape

        X_input = [state_batch, action_batch,targetID_batch]
        self.critic.model.train_on_batch(X_input, Y_value)

        a_for_grad = self.actor.model.predict([state_batch,targetID_batch])
        grads = self.critic.gradients(state_batch, a_for_grad, targetID_batch)

        self.actor.train(state_batch, grads,targetID_batch)

        self.actor.target_train()
        self.critic.target_train()


    def saveModel(self, path):
        self.critic.model.save_weights(path+'Critic_model.h5')
        self.actor.model.save_weights(path+'Actor_model.h5')

    def loadWeights(self, critic_weight_path, actor_weight_path):
        self.critic.model.load_weights(critic_weight_path)
        self.critic.target_model.load_weights(critic_weight_path)
        self.actor.model.load_weights(actor_weight_path)
        self.actor.target_model.load_weights(actor_weight_path)

    def OU_noise(self,x, mu, theta, sigma):
        return theta * (mu - x) + sigma * np.random.randn(1)

    def random_noise(self):
        return np.random.normal(0,0.5)




