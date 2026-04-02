

class pathStruct:
    def __init__(self):

        self.timestamps = []
        self.tcp_speed = []
        self.tcp_acceleration = []
        self.tcp_position = []
        self.joints_speed= [[] for _ in range(6)]
        self.joints_acceleration = [[] for _ in range(6)]
        self.joints_angles = [tuple(0 for _ in range(6))]

    def append(self, timestamp, tcp_speed, tcp_acceleration, tcp_position, joints_speed, joints_acceleration, joints_angles):
        self.timestamps.append(timestamp)
        self.tcp_speed.append(tcp_speed)
        self.tcp_acceleration.append(tcp_acceleration)
        self.tcp_position.append(tcp_position)

        joints_speed_list = list(joints_speed)
        joints_acceleration_list = list(joints_acceleration)

        for i in range(6):
            self.joints_speed[i].append(joints_speed_list[i])
            self.joints_acceleration[i].append(joints_acceleration_list[i])

        self.joints_angles.append(tuple(joints_angles))

    def if_empty(self):
        return len(self.timestamps) == 0

    def clear(self):
        self.timestamps.clear()
        self.tcp_speed.clear()
        self.tcp_acceleration.clear()
        self.tcp_position.clear()

        for i in range(6):
            self.joints_speed[i].clear()
            self.joints_acceleration[i].clear()

        self.joints_angles.clear()

    def get_length(self):
        return len(self.timestamps)

    def copy_from(self, source):
        self.timestamps = source.timestamps.copy()
        self.tcp_speed = source.tcp_speed.copy()
        self.tcp_acceleration = source.tcp_acceleration.copy()
        self.tcp_position = source.tcp_position.copy()

        for i in range(6):
            self.joints_speed[i] = source.joints_speed[i].copy()
            self.joints_acceleration[i] = source.joints_acceleration[i].copy()

        self.joints_angles = source.joints_angles.copy()

    def sum_paths(self, source):
        self.timestamps.extend(source.timestamps)
        self.tcp_speed.extend(source.tcp_speed)
        self.tcp_acceleration.extend(source.tcp_acceleration)
        self.tcp_position.extend(source.tcp_position)

        for i in range(6):
            self.joints_speed[i].extend(source.joints_speed[i])
            self.joints_acceleration[i].extend(source.joints_acceleration[i])

        self.joints_angles.extend(source.joints_angles)
