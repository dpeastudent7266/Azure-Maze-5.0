import threading

from final.imports.imports import *

from maze_motor import OdriveMotor


class Kinect:

    def __init__(self):
        # Initialize the library, if the library is not found, add the library path as argument
        self.combined_image = None
        self.body_image_color = None
        self.depth_color_image = None
        self.body_frame = None
        self.capture = None
        self.motor_is_on = True
        self.kinect_is_on = True
        pykinect.initialize_libraries(module_k4abt_path="/usr/lib/libk4abt.so", track_body=True)
        self.device_config = pykinect.default_configuration
        self.device_config.color_resolution = pykinect.K4A_COLOR_RESOLUTION_OFF
        self.device_config.depth_mode = pykinect.K4A_DEPTH_MODE_WFOV_2X2BINNED
        self.device = pykinect.start_device(config=self.device_config)
        self.bodyTracker = pykinect.start_body_tracker()
        self.close_body = None  # phase into closest centered body, reject left and right bounds
        self.motor = OdriveMotor("207C34975748", 15, 5)  # TODO: changed from 10 to 5 # why
        self.time = 0

        self.movement_text = ""
        self.recognized_body = False

        self.summon_ball = False

        self.key_left = False
        self.key_right = False
        self.row_top = False
        self.row_middle = False
        self.row_bottom = False
        self.row_enter = False
        self.clicked = False
        self.delete = False

    def start(self):
        Thread(target=self.start_thread, daemon=True).start()

    def time(self):
        return self.time

    def kinect_setup_image(self, showImage: bool = True):
        self.capture = self.device.update()

        self.body_frame = self.bodyTracker.update()

        ret, self.depth_color_image = self.capture.get_colored_depth_image()

        ret, self.body_image_color = self.body_frame.get_segmentation_image()
        if not ret:
            return

        self.combined_image = cv2.addWeighted(self.depth_color_image, 0.6, self.body_image_color, 0.4, 0)

        self.combined_image = self.body_frame.draw_bodies(self.combined_image)

        self.combined_image = numpy.fliplr(self.combined_image)
        # self.search_for_closest_body(self.body_frame)
        self.findClosestCenteredIndex()
        # new
        self.combined_image = cv2.cvtColor(self.combined_image, cv2.COLOR_BGR2RGB)

        self.combined_image = cv2.putText(self.combined_image, self.movement_text, (100, 100),
                                          cv2.FONT_HERSHEY_SIMPLEX,
                                          1, (255, 0, 0), 2, cv2.LINE_AA)
        # if self.recognized_body:
        #
        #     self.combined_image = cv2.putText(self.combined_image, "player recognized", (100, 400),
        #                                       cv2.FONT_HERSHEY_SIMPLEX,
        #                                       1, (255, 0, 0), 2, cv2.LINE_AA)
        # if not self.recognized_body:
        #
        #     self.combined_image = cv2.putText(self.combined_image, "step closer to play", (100, 400),
        #                                       cv2.FONT_HERSHEY_SIMPLEX,
        #                                       1, (255, 0, 0), 2, cv2.LINE_AA)

        if showImage:
            cv2.imshow('Depth image with skeleton', self.combined_image)
        cv2.waitKey(1)

    def findClosestCenteredIndex(
            self):  # Expected return: Index of closest body, their head's x value, their head's y value
        head_x_values = []
        head_z_values = []
        for body_index in range(self.body_frame.get_num_bodies()):
            body_skel = self.body_frame.get_body_skeleton(body_index)
            head_x = abs(body_skel.joints[K4ABT_JOINT_NAMES.index("head")].position.xyz.x)
            head_x_values.append(head_x)
            head_z = body_skel.joints[K4ABT_JOINT_NAMES.index("head")].position.xyz.z
            head_z_values.append(head_z)
        for body_index in range(self.body_frame.get_num_bodies()):
            if head_z_values[body_index] > 3000: # was 3500
                head_x_values[body_index] = 10000
        if len(head_x_values) > 0:
            closest_body_skel = self.body_frame.get_body_skeleton(head_x_values.index(min(head_x_values)))
            head_depth_z = closest_body_skel.joints[K4ABT_JOINT_NAMES.index("head")].position.xyz.z

            joint_names = ["nose", "right shoulder", "left shoulder", "left knee", "right knee"]
            joints_out_of_bounds = [closest_body_skel.joints[K4ABT_JOINT_NAMES.index(name)].position.xyz.x == 0 for name
                                    in joint_names]
            if any(joints_out_of_bounds):
                self.close_body = None
            else:
                self.close_body = closest_body_skel

        else:
            self.close_body = None

    def search_for_closest_body(self, frame):

        body_list = [frame.get_body_skeleton(body_num) for body_num in
                     range(frame.get_num_bodies())]  # creates bodylist
        try:
            self.close_body = min(body_list, key=lambda body: body.joints[
                26].position.xyz.z)  # grabs the minimum body according to the head z depth
        except ValueError:
            self.close_body = None

    def generate_points(self, joint: str):
        if self.close_body is not None:
            return self.close_body.joints[K4ABT_JOINT_NAMES.index(joint)].position.xyz

    def type_on_frame(self, text: str):
        self.combined_image = cv2.cvtColor(self.combined_image, cv2.COLOR_BGR2RGB)

        self.combined_image = cv2.putText(self.combined_image, text, (100, 100),
                                          cv2.FONT_HERSHEY_SIMPLEX,
                                          1, (255, 0, 0), 2, cv2.LINE_AA)

    def home_maze(self):
        # self.motor.ax.set_pos_traj(-3.11, 0.3, 2, 1)
        self.motor.home_maze()
        sleep(1)
        while self.motor.ax.is_busy():
            sleep(1)

    def start_thread(self):
        cv2.namedWindow('Depth image with skeleton', cv2.WINDOW_NORMAL)
        while self.kinect_is_on:
            # turn toff the ewatchdog and clear the error
            while self.motor_is_on:

                self.kinect_setup_image()

                # print(self.motor.ax.get_vel())
                if abs(self.motor.ax.get_vel()) <= 2.5:
                    self.motor.ax.axis.watchdog_feed()

                if self.close_body is not None:

                    if not self.motor.ax.axis.config.enable_watchdog:
                        self.motor.ax.axis.error = 0
                        self.motor.ax.axis.config.enable_watchdog = True

                    vel = float(int(self.generate_points("head").z)) / 1900  # changed back after presentation

                    hand_left_y = self.generate_points("left hand").y
                    hand_right_y = self.generate_points("right hand").y
                    hand_right_x = self.generate_points("right hand").x
                    hand_left_x = self.generate_points("left hand").x
                    hand_right_z = self.generate_points("right hand").z
                    hand_left_z = self.generate_points("left hand").z

                    head_x = self.generate_points("head").x
                    head_y = self.generate_points("head").y
                    head_z = self.generate_points("head").z

                    hand_slope = (hand_left_y - hand_right_y) / (hand_left_x - hand_right_x)

                    head_x = self.generate_points("head").x
                    head_y = self.generate_points("head").y
                    head_x_adjusted = head_x + 1000
                    # 2000
                    if 0 < head_x_adjusted < 600:  # right side
                        self.row_bottom = True
                    if 660 < head_x_adjusted < 1260:  # middle side
                        self.row_middle = True
                    if 1320 < head_x_adjusted < 1920:  # left side
                        self.row_top = True
                    if hand_slope > 0.2:  # key left
                        self.key_left = True
                    if hand_slope < -0.2:  # key right
                        self.key_right = True
                    if hand_left_z > head_z and hand_right_z > head_z:
                        self.delete = True
                    # if abs(hand_slope) < 0.2 and head_y > hand_right_y + 100 and head_y > hand_left_y + 100:
                    #     self.row_enter = True

                    if hand_left_y < (head_y + 100) and hand_left_y > (head_y - 100) and hand_left_x < (
                            head_x + 100) and hand_left_x > (head_x - 100) or hand_right_y < (
                            head_y + 100) and hand_right_y > (head_y - 100) and hand_right_x < (
                            head_x + 100) and hand_right_x > (head_x - 100):
                        self.clicked = True
                    if abs(hand_slope) < 0.2 and head_y > hand_right_y + 10 and head_y > hand_left_y + 10:
                        self.summon_ball = True
                    # if head_y > hand_right_y and head_y > hand_left_y and hand_left_x - hand_right_x < 50:  # clap above head
                    #     self.summon_ball = True

                    if self.motor.ball_enter_sensor_tripped:
                        # print("entered")
                        if -0.2 < hand_slope < 0.2:
                            self.movement_text = "stopping"
                            self.motor.ax.set_vel(-(self.motor.ax.get_vel()))
                        if abs(vel) <= 2 and self.summon_ball:
                            if hand_slope > 0.2:  # left
                                self.movement_text = "counterclockwise"
                                self.motor.ax.set_vel(vel)

                            if hand_slope < -0.2:  # right
                                self.motor.ax.set_vel(-vel)
                                self.movement_text = "clockwise"

                        if hand_right_x < -700 or hand_right_x > 700:
                            self.motor.ax.set_ramped_vel(0, 2)
                        if hand_left_x < -700 or hand_left_x > 700:
                            self.motor.ax.set_ramped_vel(0, 2)
                else:

                    sleep(self.motor.watchdog_sleep + 0.5)  # greater than or equal to watchdog sleep
                    self.motor.ax.axis.config.enable_watchdog = False
                if self.motor.ball_exit_sensor_tripped:
                    print("exit")
                    self.movement_text = "please wait for maze to home"
                    self.motor.is_homed = False
                    self.summon_ball = False
                    self.motor.ax.axis.error = 0
                    self.motor.ax.axis.config.enable_watchdog = False
                    self.home_maze()
                    self.motor.ax.idle()
                    sleep(1)
                    self.movement_text = "ready!"
                    self.motor.is_homed = True
                    self.motor.ball_enter_sensor_tripped = False
                    self.motor.ball_exit_sensor_tripped = False


if __name__ == '__main__':
    k = Kinect()
    k.start()
    while True:
        try:
            sleep(10)
        finally:
            k.motor.ax.idle()
