from imports import *

class OdriveMotor:
    def __init__(self, odrive_serial_number = "207C34975748", current_limit=None, velocity_limit=None):
        self.serial_number = odrive_serial_number
        self.current_limit = current_limit
        self.velocity_limit = velocity_limit
        self.odrive_board = odrive.find_any(serial_number=self.serial_number)
        self.ax = ODrive_Axis(self.odrive_board.axis0, self.current_limit, self.velocity_limit)
        self.homing_sensor = -7
        self.ball_enter_sensor = -9
        self.ball_exit_sensor = -8
        self.homing_sensor_tripped = False
        self.ball_enter_sensor_tripped = False
        self.ball_exit_sensor_tripped = False

    def kinect_motor_calibrate(self):
        if not self.ax.is_calibrated():
            print("calibrating wheel ... ")
            self.ax.calibrate()
            self.ax.gainz(20, 0.16, 0.32, False)
            self.ax.idle()
            dump_errors(self.odrive_board)

    def check_sensors(self):
        states = bin(self.odrive_board.get_gpio_states())
        if int(states[self.homing_sensor]) == 0:
            self.homing_sensor_tripped = True

        if int(states[self.ball_exit_sensor]) == 0:
            self.ball_exit_sensor_tripped = True
            self.ball_enter_sensor_tripped = False

        if int(states[self.ball_enter_sensor]) == 0:
            self.ball_enter_sensor_tripped = True
            self.ball_exit_sensor_tripped = False

    def check_prox_constantly(self):
        Thread(target=self.check_constantly_thread, daemon=True).start()

    def check_constantly_thread(self):
        print("checking prox constantly")
        self.ball_exit_sensor_tripped, self.ball_enter_sensor_tripped, self.homing_sensor_tripped = False, False, False
        while True:
            self.check_sensors()
