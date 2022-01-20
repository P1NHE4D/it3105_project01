import numpy as np
import matplotlib as plt
import math
from tqdm import tqdm

from rl.environment import Domain


class ACM:
    def __init__(self, config):
        self.max_episodes = config["episodes"]
        self.steps = config["steps"]
        self.critic_type = config["critic_type"]
        self.critic_nn_dims = config["critic_nn_dims"]
        self.actor_lr = config["actor_lr"]
        self.critic_lr = config["critic_lr"]
        self.decay_factor = config["decay"]
        self.discount_rate = config["discount"]
        self.epsilon = config["epsilon"]
        self.epsilon_decay = config["epsilon_decay"]
        self.visualise = config["visualise"]
        self.verbose = config["verbose"]

    def fit(self, domain: Domain):
        """
        learns the target policy for a given domain

        :param domain: domain object for which the target policy should be learned
        """
        actor = TableBasedActor()
        if self.critic_type == "table":
            critic = TableBasedCritic()
        else:
            critic = NNBasedCritic()

        # used for the progressbar only
        steps_per_episode = []

        progress = tqdm(range(self.max_episodes), desc="Episode", colour="green")
        for episode_count in progress:
            # TODO: add visualisation

            # reset eligibilities
            actor.reset_eligibilities()
            critic.reset_eligibilities()

            # get initial state and action
            current_state, actions = domain.produce_initial_state()
            actor.add_state(current_state, actions)
            critic.add_state(current_state)
            current_action = actor.propose_action(current_state, self.epsilon)

            # initialise an empty episode
            episode = []

            step = 0
            while step < self.steps and not domain.is_current_state_terminal():
                step += 1

                # append the current state-action pair to the current episode and initialise required values
                # in the actor and critic
                episode.append((current_state, current_action))

                # obtain a successor state and the reinforcement from moving to that state from the domain
                successor_state, actions, reinforcement = domain.generate_child_state(current_action)

                # add successor states to actor and critic
                actor.add_state(successor_state, actions)
                critic.add_state(successor_state)

                # determine the best action from the successor based on the current policy
                successor_action = actor.propose_action(state=successor_state, epsilon=self.epsilon)
                # increase the eligibility of the current state
                actor.eligibilities[(current_state, current_action)] = 1
                # compute the td error using the current and the successor state
                td_error = critic.compute_td_error(
                    current_state=current_state,
                    successor_state=successor_state,
                    reinforcement=reinforcement,
                    discount_rate=self.discount_rate
                )
                critic.eligibilities[current_state] = 1

                # update the value function, eligibilities, and the policy for each state of the current episode
                for state, action in episode:
                    critic.update_value_function(state=state, learning_rate=self.critic_lr, td_error=td_error)
                    critic.update_eligibilities(state=state, discount_rate=self.discount_rate,
                                                decay_factor=self.decay_factor)
                    actor.update_policy(state=state, action=action, learning_rate=self.actor_lr, td_error=td_error)
                    actor.update_eligibilities(state=state, action=action, discount_rate=self.discount_rate,
                                               decay_factor=self.decay_factor)

                current_state = successor_state
                current_action = successor_action

            self.epsilon *= self.epsilon_decay
            if episode_count == self.max_episodes - 1 or episode_count == 0:
                domain.visualise()
            
            # update progressbar
            
            steps_per_episode.append(step)

            progress.set_description(
                f"[epsilon: {self.epsilon:.3f}] "
                f"[steps: (curr:{steps_per_episode[-1]} "
                f"min:{min(steps_per_episode)} "
                f"avg:{np.mean(steps_per_episode):.3f})] "
                f"[states: {critic.num_seen_states()}]"
            )

    def predict(self):
        pass


class TableBasedActor:
    # contains policy, which computes a score expressing how desirable an action is in a given state

    def __init__(self):
        # maps state-action pairs to desirability value
        self.policy = dict()
        self.eligibilities = dict()
        self.state_actions = {}

    def add_state(self, state, actions):
        """
        Adds the given state to the state-action dictionary

        :param state: state to be added
        :param actions: possible actions in given state
        """
        self.state_actions[state] = actions
        for action in actions:
            if (state, action) not in self.policy.keys():
                self.policy[(state, action)] = 0
            if (state, action) not in self.eligibilities.keys():
                self.eligibilities[(state, action)] = 0

    def reset_eligibilities(self):
        """
        Resets the eligibility for every state-action pair to 0
        """
        for state_action in self.eligibilities:
            self.eligibilities[state_action] = 0

    def propose_action(self, state, epsilon):
        """
        proposes an action in a given state based on the desirability determined by the policy
        :param state: state object for which an action should be selected
        :param
        :param epsilon: probability for selecting a random action
        :return: an action
        """
        actions = self.state_actions[state]
        if np.random.choice(np.array([0, 1]), p=[1 - epsilon, epsilon]) == 1:
            return np.random.choice(np.array(actions))
        best_action = None
        max_value = -math.inf
        for action in actions:
            state_value = self.policy[(state, action)] / len(actions)
            if state_value > max_value:
                best_action = action
                max_value = state_value
        return best_action

    def update_policy(self, state, action, learning_rate, td_error):
        """
        Updates the policy using the td error computed by the critic

        :param state: state for which the policy should be updated
        :param action: corresponding action of the state
        :param learning_rate: learning rate
        :param td_error: temporal difference error computed by the critic
        """
        self.policy[(state, action)] += learning_rate * td_error * self.eligibilities[(state, action)]

    def update_eligibilities(self, state, action, discount_rate, decay_factor):
        """
        Updates the eligibilities for the given state-action pair based on the discount rate and
        decay factor.

        :param state: state for which the eligibility should be updated
        :param action: corresponding action of the state
        :param discount_rate: discount rate
        :param decay_factor: decay factor of eligibility
        """
        self.eligibilities[(state, action)] *= discount_rate * decay_factor


class TableBasedCritic:

    def __init__(self, ):
        # maps states to values
        self.state_values = dict()
        self.eligibilities = dict()

    def add_state(self, state):
        """
        Adds the given state to the state-value dict

        :param state: state to be added
        """
        if state not in self.state_values.keys():
            self.state_values[state] = np.random.uniform()
        if state not in self.eligibilities.keys():
            self.eligibilities[state] = 0

    def reset_eligibilities(self):
        """
        Resets all eligibilities to 0
        """
        for state in self.eligibilities:
            self.eligibilities[state] = 0

    def compute_td_error(self, current_state, successor_state, reinforcement, discount_rate):
        """
        computes the temporal difference error based on the reinforcement and value of a state
        :return: td error
        """
        return reinforcement + (discount_rate * self.state_values[successor_state]) - self.state_values[current_state]

    def update_value_function(self, state, learning_rate, td_error):
        """
        Updates the value of the given state based on td_error and the learning_rate

        :param state: state for which the value should be updated
        :param learning_rate: learning rate
        :param td_error: temporal difference error
        """
        self.state_values[state] += learning_rate * td_error * self.eligibilities[state]

    def update_eligibilities(self, state, discount_rate, decay_factor):
        """
        Updates the eligibility traces of the given state using the given discount rate and decay factor

        :param state: state for which the eligibility should be updated
        :param discount_rate: discount rate
        :param decay_factor: decay factor
        """
        self.eligibilities[state] *= discount_rate * decay_factor
    
    def num_seen_states(self):
        return len(self.state_values)


class NNBasedCritic:
    # TODO: implement
    pass
