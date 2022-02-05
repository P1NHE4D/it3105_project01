import math
import numpy as np


class TableBasedActor:
    # contains policy, which computes a score expressing how desirable an action is in a given state

    def __init__(self, learning_rate, epsilon):
        # maps state-action pairs to desirability value
        self.policy = dict()
        self.eligibilities = dict()
        self.state_actions = {}
        self.learning_rate = learning_rate
        self.epsilon = epsilon

    def add_state(self, state, actions):
        """
        Adds the given state to the state-action dictionary

        :param state: state to be added
        :param actions: possible actions in given state
        """
        state_id = hash(tuple(state))
        self.state_actions[state_id] = actions
        for action in actions:
            if (state_id, action) not in self.policy.keys():
                self.policy[(state_id, action)] = 0
            if (state_id, action) not in self.eligibilities.keys():
                self.eligibilities[(state_id, action)] = 0

    def reset_eligibilities(self):
        """
        Resets the eligibility for every state-action pair to 0
        """
        for sa_id in self.eligibilities.keys():
            self.eligibilities[sa_id] = 0

    def increase_eligibility(self, state, action):
        state_id = hash(tuple(state))
        self.eligibilities[(state_id, action)] = 1

    def propose_action(self, state):
        """
        proposes an action in a given state based on the desirability determined by the policy
        :param state: state object for which an action should be selected
        :param
        :return: an action
        """
        state_id = hash(tuple(state))
        actions = self.state_actions[state_id]
        if np.random.choice(np.array([0, 1]), p=[1 - self.epsilon, self.epsilon]) == 1:
            return np.random.choice(np.array(actions))
        best_action = None
        max_value = -math.inf
        for action in actions:
            state_value = self.policy[(state_id, action)] / len(actions)
            if state_value > max_value:
                best_action = action
                max_value = state_value
        return best_action

    def update_policy(self, state, action, td_error):
        """
        Updates the policy using the td error computed by the critic

        :param state: state for which the policy should be updated
        :param action: corresponding action of the state
        :param td_error: temporal difference error computed by the critic
        """
        state_id = hash(tuple(state))
        self.policy[(state_id, action)] += self.learning_rate * td_error * self.eligibilities[(state_id, action)]

    def update_eligibilities(self, state, action, discount_rate, decay_factor):
        """
        Updates the eligibilities for the given state-action pair based on the discount rate and
        decay factor.

        :param state: state for which the eligibility should be updated
        :param action: corresponding action of the state
        :param discount_rate: discount rate
        :param decay_factor: decay factor of eligibility
        """
        state_id = hash(tuple(state))
        self.eligibilities[(state_id, action)] *= discount_rate * decay_factor
