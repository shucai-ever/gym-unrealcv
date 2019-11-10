import numpy as np
class Reward():
    '''
    define different type reward function
    '''

    def __init__(self, setting):

        self.dis2target_last = 0
        self.dis_exp = setting['exp_distance']
        self.dis_max = setting['max_distance']
        self.r_target = 0
        self.r_tracker = 0
        self.dis2target = 250
        self.angle2target = 0

    def reward_distance(self, dis2target_now, direction_error, dis_exp=None):
        #  reward = (100.0 / max(dis2target_now,100)) * np.cos(direction_error/360.0*np.pi)
        if dis_exp is None:
            dis_exp = self.dis_exp
        self.dis2target = dis2target_now
        self.angle2target = direction_error
        direction_error = abs(direction_error)/45.0
        e_dis = abs(dis_exp - dis2target_now)
        #  e_dis_relative = e_dis / self.dis_exp
        e_dis_relative = e_dis / dis_exp
        # reward = 1 - min(e_dis_relative, 1) - min(direction_error, 1)
        reward = 1 - direction_error - e_dis_relative
        reward = max(reward, -1)
        self.r_tracker = reward
        return reward

    def reward_target(self, dis2target_now, direction_error, dis_exp=None, w=1.0):
        #  reward = (100.0 / max(dis2target_now,100)) * np.cos(direction_error/360.0*np.pi)
        if dis_exp is None:
            dis_exp = self.dis_exp
        direction_error = max(abs(direction_error) - 45, 0)/45.0
        e_dis = max(abs(dis_exp - dis2target_now) - dis_exp, 0) / dis_exp
        # reward = 1 - 2 * min(abs(e_dis_relative), 1) + min(abs(direction_error/(np.pi/4)), 2)
        # reward = 1 - min(e_dis, 1) - min(direction_error, 1)
        reward = -self.r_tracker - w * (e_dis + direction_error)
        reward = max(reward, -1)
        self.r_target = reward
        return reward

    def reward_distractor(self, dis2distractor, direction_error, num, dis_exp=None):
        if dis_exp is None:
            dis_exp = self.dis_exp
        mislead = 0
        direction_error_abs = abs(direction_error)
        relative_dis = abs(dis2distractor - dis_exp)
        r_dis = 0
        observed = 0
        collision = 0
        if dis2distractor < self.dis_max and direction_error_abs < 45:
            # observed but not absolute
            # reward = abs(dis2distractor) / self.dis_max
            observed = 1
            if self.target_inarea:  # target is observed
                relative_target = abs(self.dis2target - dis_exp)
                if abs(self.angle2target - direction_error) < 10:
                    # occluded by target
                    if self.dis2target < dis2distractor:
                        mislead = 0
                        observed = 0
                    else:  # dis2distractor < self.dis2target
                        # print ('target is occluded')
                        mislead = 1
                        # closer to expected position, higher
                        distance_factor = abs(self.dis2target - dis_exp)/dis_exp
                        angle_factor = direction_error_abs / 45
                        r_dis = max(1 - (distance_factor + angle_factor), 0)
                else: # no overlap, the one closer to the expected location
                    r_dis = max(relative_target - relative_dis, 0) / dis_exp + \
                            max(abs(self.angle2target) - direction_error_abs, 0) / 45
                    if r_dis > 0.5:
                        mislead = 2
                        # print ('DR')
                        # print (r_dis)
                    else:
                        mislead = 0  # appear but not cause mislead
            else:  # target is not observed
                distance_factor = abs(self.dis2target - dis_exp) / self.dis_exp
                angle_factor = direction_error_abs / 45
                r_dis = max(1 - (distance_factor + angle_factor), 0)
                mislead = 3
            if dis2distractor < 80 and direction_error_abs < 45:
                collision = 1
            if observed == 1:
                reward = min(1-self.r_tracker + r_dis, 2)
                # print (reward)
            elif collision == 1:
                reward = -1
            else:
                reward = 0
            '''
            elif direction_error_abs < 10:

            if direction_error_abs < 10 and direction_error_abs < abs(self.angle2target):  # potential mislead
                # if self.dis2target < dis2distractor and abs(self.angle2target) < direction_error_abs:
                if abs(self.angle2target - direction_error) < 10:
                    if dis2distractor >= self.dis2target:
                        # occluded by target, skip this case
                        mislead =False
                    else:
                        print ('occluded')
                        mislead = True
                else:
                    relative_target = abs(self.dis2target - dis_exp)
                    if relative_target - relative_dis > 0 and self.angle2target - direction_error_abs > 0:
                        r_dis = max(relative_target - relative_dis, 0) / dis_exp + max(
                            self.angle2target - direction_error_abs, 0) / 40
                        mislead = True

                    distance_factor = max(abs(self.dis2target - dis_exp) / self.dis_exp, 0)
                    angle_factor = max(abs(self.angle2target) - direction_error_abs, 0) / 45
                    r_dis = distance_factor + angle_factor
                    print (r_dis)
                    mislead = True
                    print ('mislead')
            reward = 1-self.r_tracker + r_dis
            observed = 1
            '''
        else:
            # reward = -1.0
            direction_error = max(abs(direction_error)-45, 0) / 180.0
            e_dis = max(relative_dis-self.dis_max, 0) / self.dis_max
            reward = (-e_dis - direction_error)/2
            reward = max(reward, -1)
        return reward, mislead, r_dis, observed, collision

    def target_inarea(self):
        if abs(self.angle2target) < 45 and self.dis2target < self.dis_max:
            return True
        else:
            return False