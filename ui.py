import argparse
import json
import os.path
import signal
import sys
import time


from PySide6.QtCore import QThread, Qt, QSize, QRectF, Signal, QObject
from PySide6.QtGui import QFont, QPen, QPainter, QIcon, QColor, QBrush, QPainterPath, QAction
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, \
    QGridLayout, QTextEdit, QSplitter, QMainWindow, QToolBar, QSpinBox, QHBoxLayout, \
    QInputDialog

from model import Storage, BLOXX_OFFSET_Y, BLOXX_OFFSET_X
from controller import Controller, STORAGE1_KEY, STORAGE2_KEY, BELT_PICKUP_KEY, BELT_DROPOFF_KEY, DELIVERY_KEY

signal.signal(signal.SIGINT, signal.SIG_DFL)

# number of student tasks
NUM_TASKS = 5

# font sizes for text labels
FONT_SIZE_TASK = 24
FONT_SIZE = 20  # font size for text labels
FONT_SIZE_POSE = 36  # font size for the robot pose
FONT_SIZE_TERMINAL = 18  # font size for text in the terminal

WINDOW_TITLE = "TecDay - Snack-o-mation"

def format_coordinates(data):
    """
    helper method to format coordinates. Replaces None values with '?'
    Input is expected as a list of coordinates [x, y, z]
    """
    text = '<span style="background-color:green">x=%d</span> ' % data.x if data.x is not None else 'x=? '
    text += '<span style="background-color:green">y=%d</span> ' % data.y if data.y is not None else 'y=? '
    text += '<span style="background-color:green">z=%d</span>' % data.z if data.z is not None else 'z=?'
    return text


def format_number(value):
    """
    helper method to format integer numbers. Replaces None values with '?'
    """
    return "%u " % value if value is not None else "?"


class SceneCanvas(QWidget):
    BRUSH_ROBOT_BASE = QBrush(QColor.fromRgb(51, 51, 51))
    BRUSH_CONVEYOR = QBrush(QColor.fromRgb(77, 77, 77))
    BRUSH_MAOAM = QBrush(QColor.fromRgb(255, 146, 72))
    BRUSH_EMPTY = QBrush(QColor.fromRgb(200, 200, 200))
    WIDTH_MM = 1200
    CIRCLE_RADIUS = 20

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.pose_left = None
        self.pose_right = None

    def set_pose(self, pose_left, pose_right):
        """
        Update the robot pose on the screen
        :param pose_left: pose of the left robot
        :param pose_right: pose of the right robot
        """
        self.pose_left = pose_left
        self.pose_right = pose_right
        self.update()

    def paintEvent(self, event):
        """
        paint method called to draw the UI elements
        """
        width = self.width()
        mm_to_pixel = width / self.WIDTH_MM
        center_x = width // 2
        base_length = int(160 * mm_to_pixel)  # length of robot base (16 cm)
        robot_left_center_x = center_x - int(125 * mm_to_pixel) - base_length // 2
        robot_left_center_y = base_length // 2 + int(20 * mm_to_pixel)
        robot_right_center_x = center_x + int(125 * mm_to_pixel) + base_length // 2
        robot_right_center_y = base_length // 2 + int(20 * mm_to_pixel)
        conveyor_width = int(695 * mm_to_pixel)  # 69.5 cm
        conveyor_height = int(120 * mm_to_pixel)  # 12 cm
        conveyor_center_y = robot_left_center_y + (base_length // 2) + int(
            130 * mm_to_pixel) + conveyor_height // 2  # 13cm
        conveyor_center_x = center_x

        # get a painter object
        painter = QPainter(self)
        # set default font
        font = QFont("Arial", 24, QFont.Weight.Bold)
        painter.setFont(font)

        # draw left robot base
        painter.setPen(QPen(QColor("black"), 2, Qt.PenStyle.SolidLine))
        painter.setBrush(self.BRUSH_ROBOT_BASE)
        path = QPainterPath()
        path.addRoundedRect(
            QRectF(robot_left_center_x - base_length // 2, robot_left_center_y - base_length // 2, base_length,
                   base_length), base_length // 10, base_length // 10)
        painter.fillPath(path, self.BRUSH_ROBOT_BASE)
        painter.drawPath(path)
        painter.setBrush(QColor("white"))
        painter.setPen(QColor("white"))
        painter.drawPie(robot_left_center_x - int(base_length * 0.45),
                        robot_left_center_y - int(base_length * 0.45),
                        int(base_length * 0.9), int(base_length * 0.9), 0,
                        360 * 16)  # angle = 1/16th of a degree

        # draw right robot base
        painter.setPen(QPen(QColor("black"), 2, Qt.PenStyle.SolidLine))
        painter.setBrush(self.BRUSH_ROBOT_BASE)
        path = QPainterPath()
        path.addRoundedRect(
            QRectF(robot_right_center_x - base_length // 2, robot_right_center_y - base_length // 2, base_length,
                   base_length), base_length // 10, base_length // 10)
        painter.fillPath(path, self.BRUSH_ROBOT_BASE)
        painter.drawPath(path)
        painter.setBrush(QColor("white"))
        painter.setPen(QColor("white"))
        painter.drawPie(robot_right_center_x - int(base_length * 0.45),
                        robot_right_center_y - int(base_length * 0.45),
                        int(base_length * 0.9), int(base_length * 0.9), 0,
                        360 * 16)  # angle = 1/16th of a degree

        # draw conveyor belt
        painter.setPen(QPen(QColor("black"), 2, Qt.PenStyle.SolidLine))
        painter.setBrush(self.BRUSH_CONVEYOR)
        painter.drawRect(conveyor_center_x - conveyor_width // 2,
                         conveyor_center_y - conveyor_height // 2,
                         conveyor_width, conveyor_height)

        # draw storage
        for key in [STORAGE1_KEY, STORAGE2_KEY]:

            storage_x = robot_right_center_x + int(default_coordinates[key].y * mm_to_pixel)
            storage_y = robot_right_center_y + int(default_coordinates[key].x * mm_to_pixel)

            next_pos = self.controller.storage[key].get_next_position()
            stock = self.controller.storage[key].get_stock()

            pos = 0
            for i in range(Storage.DIM_X):
                for k in range(Storage.DIM_Y):
                    if pos < next_pos or pos >= next_pos + stock:
                        # empty position
                        painter.setBrush(self.BRUSH_EMPTY)
                    else:
                        painter.setBrush(self.BRUSH_MAOAM)
                    painter.drawRect(storage_x + int((k-0.45)*BLOXX_OFFSET_Y*mm_to_pixel),
                                     storage_y - int((i+0.45)*BLOXX_OFFSET_X*mm_to_pixel),
                                     int(BLOXX_OFFSET_Y*mm_to_pixel*0.9), int(BLOXX_OFFSET_X*mm_to_pixel*0.9))
                    pos+=1

        # draw task coordinates at the correct location
        task = 1
        for key in [STORAGE1_KEY, STORAGE2_KEY, BELT_DROPOFF_KEY, BELT_PICKUP_KEY, DELIVERY_KEY]:

            if self.controller.coordinates[key].is_valid():
                pose = self.controller.coordinates[key]

                if task <= 3:
                    # robot right
                    point_x = robot_right_center_x + int(pose.y * mm_to_pixel)
                    point_y = robot_right_center_y + int(pose.x * mm_to_pixel)
                else:
                    # robot left
                    point_x = robot_left_center_x + int(pose.y * mm_to_pixel)
                    point_y = robot_left_center_y + int(pose.x * mm_to_pixel)

                painter.setPen(QPen(QColor("black"), 2, Qt.PenStyle.SolidLine))
                painter.setBrush(QColor("green"))
                painter.drawEllipse(point_x - SceneCanvas.CIRCLE_RADIUS,
                                    point_y - SceneCanvas.CIRCLE_RADIUS,
                                    40, 40)  # angle = 1/16th of a degree
                painter.drawText(point_x - SceneCanvas.CIRCLE_RADIUS, point_y - SceneCanvas.CIRCLE_RADIUS,
                                 2 * SceneCanvas.CIRCLE_RADIUS,
                                 2 * SceneCanvas.CIRCLE_RADIUS, Qt.AlignmentFlag.AlignCenter,
                                 "%u" % task, )

            task += 1

        if self.pose_left:
            # draw left end effector
            painter.setBrush(QColor("gray"))
            painter.setPen(QPen(QColor("black"), 30, Qt.PenStyle.SolidLine))
            painter.drawLine(robot_left_center_x, robot_left_center_y,
                             robot_left_center_x + int(self.pose_left.y * mm_to_pixel),
                             robot_left_center_y + int(self.pose_left.x * mm_to_pixel))

        if self.pose_right:
            # draw right end effector
            painter.setBrush(QColor("gray"))
            painter.setPen(QPen(QColor("black"), 30, Qt.PenStyle.SolidLine))
            painter.drawLine(robot_right_center_x, robot_right_center_y,
                             robot_right_center_x + int(self.pose_right.y * mm_to_pixel),
                             robot_right_center_y + int(self.pose_right.x * mm_to_pixel))

        painter.end()


class MainWidget(QWidget):
    def __init__(self, controller):
        super().__init__()
        vertical_layout = QVBoxLayout()
        layout_task_horizontal = QGridLayout()
        self.task_labels = []
        for i in range(NUM_TASKS):
            label = QLabel(language_dictionary["Task"] + " %u" % (i + 1))
            label.setFont(QFont("Arial", FONT_SIZE_TASK))
            label.setStyleSheet("background-color: gray;")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout_task_horizontal.addWidget(label, 0, i)
            self.task_labels.append(label)

        layout_task_horizontal.setRowStretch(0, 1)
        layout_task_horizontal.setRowStretch(1, 5)
        layout_task_horizontal.setRowStretch(2, 1)

        # Storage 1
        self.label_storage1 = QLabel()
        self.label_storage1.setFont(QFont("Arial", FONT_SIZE))
        layout_task_horizontal.addWidget(self.label_storage1, 1, 0, 1, 1,
                                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        # go to Storage 1 button
        self.button_storage1 = QPushButton(self)
        self.button_storage1.setVisible(False)
        self.button_storage1.setMinimumSize(50, 50)
        self.button_storage1.setStyleSheet("background-image : url(./icons/material-design-icons/target.png);")
        self.button_storage1.clicked.connect(
            lambda x: controller.robot_right.show(controller.coordinates[STORAGE1_KEY]))
        layout_task_horizontal.addWidget(self.button_storage1, 2, 0, 1, 1,
                                         Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)

        # Storage 2
        self.label_storage2 = QLabel()
        self.label_storage2.setFont(QFont("Arial", FONT_SIZE))
        layout_task_horizontal.addWidget(self.label_storage2, 1, 1, 1, 1,
                                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        # go to Storage 2 button
        self.button_storage2 = QPushButton(self)
        self.button_storage2.setVisible(False)
        self.button_storage2.setMinimumSize(50, 50)
        self.button_storage2.setStyleSheet("background-image : url(./icons/material-design-icons/target.png);")
        self.button_storage2.clicked.connect(
            lambda x: controller.robot_right.show(controller.coordinates[STORAGE2_KEY]))
        layout_task_horizontal.addWidget(self.button_storage2, 2, 1, 1, 1,
                                         Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)

        # drop-off belt
        self.label_dropoff_belt = QLabel()
        self.label_dropoff_belt.setFont(QFont("Arial", FONT_SIZE))
        layout_task_horizontal.addWidget(self.label_dropoff_belt, 1, 2, 1, 1,
                                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        # go to target button
        self.button_dropoff_belt = QPushButton(self)
        self.button_dropoff_belt.setVisible(False)
        self.button_dropoff_belt.setMinimumSize(50, 50)
        self.button_dropoff_belt.setStyleSheet("background-image : url(./icons/material-design-icons/target.png);")
        self.button_dropoff_belt.clicked.connect(
            lambda x: controller.robot_right.show(controller.coordinates[BELT_DROPOFF_KEY]))
        layout_task_horizontal.addWidget(self.button_dropoff_belt, 2, 2, 1, 1,
                                         Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)

        # pick-up belt
        self.label_pickup_belt = QLabel()
        self.label_pickup_belt.setFont(QFont("Arial", FONT_SIZE))
        layout_task_horizontal.addWidget(self.label_pickup_belt, 1, 3, 1, 1,
                                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        # go to target button
        self.button_pickup_belt = QPushButton(self)
        self.button_pickup_belt.setVisible(False)
        self.button_pickup_belt.setMinimumSize(50, 50)
        self.button_pickup_belt.setStyleSheet("background-image : url(./icons/material-design-icons/target.png);")
        self.button_pickup_belt.clicked.connect(
            lambda x: controller.robot_left.show(controller.coordinates[BELT_PICKUP_KEY]))
        layout_task_horizontal.addWidget(self.button_pickup_belt, 2, 3, 1, 1,
                                         Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)

        # dropoff
        self.label_dropoff = QLabel()
        self.label_dropoff.setFont(QFont("Arial", FONT_SIZE))
        layout_task_horizontal.addWidget(self.label_dropoff, 1, 4, 1, 1,
                                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        # go to target button
        self.button_dropoff = QPushButton(self)
        self.button_dropoff.setVisible(False)
        self.button_dropoff.setMinimumSize(50, 50)
        self.button_dropoff.setStyleSheet("background-image : url(./icons/material-design-icons/target.png);")
        self.button_dropoff.clicked.connect(
            lambda x: controller.robot_left.show(controller.coordinates[DELIVERY_KEY]))
        layout_task_horizontal.addWidget(self.button_dropoff, 2, 4, 1, 1,
                                         Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)

        vertical_layout.addLayout(layout_task_horizontal, 1)

        self.canvas = SceneCanvas(controller)
        # grid layout
        layout_grid = QGridLayout()
        layout_grid.addWidget(self.canvas, 0, 0, 1, 2)
        layout_grid.setRowStretch(0, 10)

        # robot left coordinates
        self.label_robot_left = QLabel()
        self.label_robot_left.setFont(QFont("Arial", FONT_SIZE_POSE))
        self.label_robot_left.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout_grid.addWidget(self.label_robot_left, 1, 0, 1, 1, Qt.AlignmentFlag.AlignCenter)
        # robot right coordinates
        self.label_robot_right = QLabel()
        self.label_robot_right.setFont(QFont("Arial", FONT_SIZE_POSE))
        self.label_robot_right.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout_grid.addWidget(self.label_robot_right, 1, 1, 1, 1, Qt.AlignmentFlag.AlignCenter)

        vertical_layout.addLayout(layout_grid, 10)
        self.setLayout(vertical_layout)


class Window(QMainWindow):
    def __init__(self, controller):
        super().__init__(None)
        self.setWindowTitle(WINDOW_TITLE)
        width = self.width()
        self.controller = controller
        self.worker_thread = BackgroundThread(self, controller)

        w = QSplitter(Qt.Orientation.Horizontal)

        self.main_widget = MainWidget(self.controller)
        w.addWidget(self.main_widget)

        self.right_widget = QWidget()
        w.addWidget(self.right_widget)
        self.vertical_layout_right = QVBoxLayout()
        self.right_widget.setLayout(self.vertical_layout_right)

        # text box with incoming radio messages
        self.textBox = QTextEdit()
        font = QFont()
        font.setPointSize(FONT_SIZE_TERMINAL)
        font.setStyleHint(QFont.StyleHint.TypeWriter)
        self.textBox.setFont(font)
        self.vertical_layout_right.addWidget(self.textBox)
        # button to clear the radio messages
        self.textClearButton = QPushButton("Clear Messages")
        self.textClearButton.setFont(QFont('Arial', 12))
        self.textClearButton.clicked.connect(self.textBox.clear)
        self.vertical_layout_right.addWidget(self.textClearButton, alignment=Qt.AlignmentFlag.AlignBottom)

        self.statusBar()

        menubar = self.menuBar()
        menubar.setNativeMenuBar(False)

        menu_app = menubar.addMenu('&Application')
        # exit action
        exit_action = QAction(QIcon('exit.png'), 'Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.setStatusTip('Exit application')
        exit_action.triggered.connect(app.quit)
        menu_app.addAction(exit_action)

        menu_controller = menubar.addMenu('&Controller')
        reset_state_action = QAction('Clear State', self)
        reset_state_action.setStatusTip('Reset to initial state')
        reset_state_action.triggered.connect(lambda index: self.controller.reset_state())
        menu_controller.addAction(reset_state_action)

        default_state_action = QAction('Default State', self)
        default_state_action.setStatusTip('Reset to default state')
        default_state_action.triggered.connect(lambda index: self.controller.set_default())
        menu_controller.addAction(default_state_action)

        menu_robot = menubar.addMenu('&Robot')
        # commands for left robot
        robot_left_menu = menu_robot.addMenu('Robot &Left')
        # calibrate
        calib_left_action = QAction('Calibrate', self)
        calib_left_action.setStatusTip('Calibrate left robot')
        calib_left_action.triggered.connect(self.controller.robot_left.calibrate)
        robot_left_menu.addAction(calib_left_action)
        # clear alarms
        alarm_left_action = QAction('Clear Alarms', self)
        alarm_left_action.setStatusTip('Clear alarms at left robot')
        alarm_left_action.triggered.connect(self.controller.robot_left.clear_alarms)
        robot_left_menu.addAction(alarm_left_action)
        # go home
        home_left_action = QAction('Go Home', self)
        home_left_action.setStatusTip('Home position for left robot')
        home_left_action.triggered.connect(self.controller.robot_left.home)
        robot_left_menu.addAction(home_left_action)
        # commands for right robot
        robot_right_menu = menu_robot.addMenu('Robot &Right')
        # calibrate
        calib_right_action = QAction('Calibrate', self)
        calib_right_action.setStatusTip('Calibrate right robot')
        calib_right_action.triggered.connect(self.controller.robot_right.calibrate)
        robot_right_menu.addAction(calib_right_action)
        # clear alarms
        alarm_right_action = QAction('Clear Alarms', self)
        alarm_right_action.setStatusTip('Clear alarms at right robot')
        alarm_right_action.triggered.connect(self.controller.robot_right.clear_alarms)
        robot_right_menu.addAction(alarm_right_action)
        # go home
        home_right_action = QAction('Go Home', self)
        home_right_action.setStatusTip('Home position for right robot')
        home_right_action.triggered.connect(self.controller.robot_right.home)
        robot_right_menu.addAction(home_right_action)

        conveyormenu = menubar.addMenu('&Conveyor')

        conveyorStartAction = QAction('Run Conveyor until stopped by light sensor', self)
        conveyorStartAction.setStatusTip('Run Conveyor until stopped by light sensor')
        conveyorStartAction.triggered.connect(lambda index: self.controller.start_conveyor_manually())
        conveyormenu.addAction(conveyorStartAction)

        conveyorStopAction = QAction('Stop Conveyor', self)
        conveyorStopAction.setStatusTip('Stop conveyor')
        conveyorStopAction.triggered.connect(lambda index: self.controller.stop_conveyor())
        conveyormenu.addAction(conveyorStopAction)

        debugmenu = menubar.addMenu('&Debug')

        dbgMsgAction = QAction('Simulate Radio Message', self)
        dbgMsgAction.setStatusTip('Input a radio message')
        dbgMsgAction.triggered.connect(self.prompt_for_radio_message)
        debugmenu.addAction(dbgMsgAction)

        toolbar = QToolBar('Main ToolBar')
        toolbar.setIconSize(QSize(32, 32))

        self.play_action = QAction(QIcon('./icons/material-design-icons/play.png'), '&Start', self)
        self.play_action.setStatusTip('Start delivery of the order')
        self.play_action.triggered.connect(lambda x: self.controller.start_delivery())
        self.play_action.setDisabled(True)
        toolbar.addAction(self.play_action)

        stop_action = QAction(QIcon('./icons/material-design-icons/stop.png'), '&Stop', self)
        stop_action.setStatusTip('Stop delivery of the order')
        stop_action.triggered.connect(lambda x: self.controller.stop_delivery())
        toolbar.addAction(stop_action)

        toolbar.addSeparator()

        # order storage 1
        self.order1_box = QSpinBox()
        self.order1_box.setMinimum(0)
        self.order1_box.setMaximum(6)
        self.order1_box.setValue(0)
        self.order1_box.setFont(QFont('Arial', 20))
        self.order1_box.valueChanged.connect(
            lambda x: self.controller.set_orders(STORAGE1_KEY, self.order1_box.value()))
        layout = QHBoxLayout()
        self.label_orders1 = QLabel(language_dictionary["Orders_1"] + ":")
        self.label_orders1.setFont(QFont('Arial', 20))
        self.label_orders1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label_orders1)
        layout.addWidget(self.order1_box)
        widget = QWidget()
        widget.setLayout(layout)
        toolbar.addWidget(widget)

        # order storage 2
        self.order2_box = QSpinBox()
        self.order2_box.setMinimum(0)
        self.order2_box.setMaximum(6)
        self.order2_box.setValue(0)
        self.order2_box.setFont(QFont('Arial', 20))
        self.order2_box.valueChanged.connect(
            lambda x: self.controller.set_orders(STORAGE2_KEY, self.order2_box.value()))
        layout = QHBoxLayout()
        self.label_orders2 = QLabel(language_dictionary["Orders_2"] + ":")
        self.label_orders2.setFont(QFont('Arial', 20))
        self.label_orders2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label_orders2)
        layout.addWidget(self.order2_box)
        widget = QWidget()
        widget.setLayout(layout)
        toolbar.addWidget(widget)

        toolbar.addSeparator()

        # storage 1 counter
        self.storage1_box = QSpinBox()
        self.storage1_box.setMinimum(0)
        self.storage1_box.setMaximum(6)
        self.storage1_box.setValue(0)
        self.storage1_box.setFont(QFont('Arial', 20))
        self.storage1_box.valueChanged.connect(
            lambda x: self.controller.set_storage(STORAGE1_KEY, self.storage1_box.value()))
        layout = QHBoxLayout()
        self.label_storage1 = QLabel(language_dictionary["Fill_1"] + ":")
        self.label_storage1.setFont(QFont('Arial', 20))
        self.label_storage1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label_storage1)
        layout.addWidget(self.storage1_box)
        widget = QWidget()
        widget.setLayout(layout)
        toolbar.addWidget(widget)

        # storage 2 counter
        self.storage2_box = QSpinBox()
        self.storage2_box.setMinimum(0)
        self.storage2_box.setMaximum(6)
        self.storage2_box.setValue(0)
        self.storage2_box.setFont(QFont('Arial', 20))
        self.storage2_box.valueChanged.connect(
            lambda x: self.controller.set_storage(STORAGE2_KEY, self.storage2_box.value()))
        layout = QHBoxLayout()
        self.label_storage2 = QLabel(language_dictionary["Fill_2"] + ":")
        self.label_storage2.setFont(QFont('Arial', 20))
        self.label_storage2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label_storage2)
        layout.addWidget(self.storage2_box)
        widget = QWidget()
        widget.setLayout(layout)
        toolbar.addWidget(widget)

        self.addToolBar(toolbar)

        # split horizontal view in 90/10%
        w.setSizes([int(width * 0.9), int(width * 0.1)])
        self.setCentralWidget(w)

    def update_pose(self, pose):
        pose_left, pose_right = pose[0], pose[1]

        if pose_left:
            self.main_widget.label_robot_left.setText(
                language_dictionary["Robot_L"] +
                ":<pre><code>x={:<4} y={:<4} z={:<4}</code></pre>".format(
                    int(pose_left.x), int(pose_left.y), int(pose_left.z)))

        if pose_right:
            self.main_widget.label_robot_right.setText(
                language_dictionary["Robot_R"] +
                ":<pre><code>x={:<4} y={:<4} z={:<4}</code></pre>".format(
                    int(pose_right.x), int(pose_right.y), int(pose_right.z)))

        self.main_widget.canvas.set_pose(pose_left, pose_right)

    def update_state(self, data):
        coordinates = data['coordinates']
        orders = data['orders']
        storage = data['storage']
        tasks = data['tasks']

        # update coordinates
        self.main_widget.label_storage1.setText(
            language_dictionary["Storage_1"]
            + "<br><code>" + format_coordinates(coordinates[STORAGE1_KEY]) + "</code>")
        self.main_widget.label_storage2.setText(
            language_dictionary["Storage_2"]
            + ":<br><code>" + format_coordinates(coordinates[STORAGE2_KEY]) + "</code>")
        self.main_widget.label_dropoff_belt.setText(
            language_dictionary["Release"]
            + "<br><code>" + format_coordinates(coordinates[BELT_DROPOFF_KEY]) + "</code>")
        self.main_widget.label_pickup_belt.setText(
            language_dictionary["Pickup"]
            + "<br><code>" + format_coordinates(coordinates[BELT_PICKUP_KEY]) + "</code>")
        self.main_widget.label_dropoff.setText(
            language_dictionary["Delivery"]
            + "<br><code>" + format_coordinates(coordinates[DELIVERY_KEY]) + "</code>")

        # update storage
        window.storage1_box.blockSignals(True)
        window.storage1_box.setValue(self.worker_thread.controller.storage[STORAGE1_KEY].get_stock())
        window.storage1_box.blockSignals(False)
        window.storage2_box.blockSignals(True)
        window.storage2_box.setValue(self.worker_thread.controller.storage[STORAGE2_KEY].get_stock())
        window.storage2_box.blockSignals(False)

        # update orders
        window.order1_box.setValue(self.worker_thread.controller.orders[STORAGE1_KEY])
        window.order2_box.setValue(self.worker_thread.controller.orders[STORAGE2_KEY])

        #  update tasks
        for i in range(NUM_TASKS):
            color = 'green' if tasks[i] else 'gray'
            self.main_widget.task_labels[i].setStyleSheet("background-color: %s;" % color)

        # update buttons
        self.main_widget.button_storage1.setVisible(coordinates[STORAGE1_KEY].is_valid())
        self.main_widget.button_storage2.setVisible(coordinates[STORAGE2_KEY].is_valid())
        self.main_widget.button_dropoff_belt.setVisible(coordinates[BELT_DROPOFF_KEY].is_valid())
        self.main_widget.button_pickup_belt.setVisible(coordinates[BELT_PICKUP_KEY].is_valid())
        self.main_widget.button_dropoff.setVisible(coordinates[DELIVERY_KEY].is_valid())

        if all(tasks) and not data['delivering']:
            window.play_action.setEnabled(True)
        else:
            window.play_action.setDisabled(True)

    def update_packet(self, packet, correct):
        cursor = window.textBox.textCursor()
        # append the new packet
        try:
            packet = packet.strip()
            if correct:
                cursor.insertHtml("<font color='black'>%s</font><br>" % (
                    packet))
            else:
                cursor.insertHtml('<span style="background-color:red">%s\n</span><br>' % packet)
        except:
            pass

        # scroll to bottom
        window.textBox.verticalScrollBar().setValue(window.textBox.verticalScrollBar().maximum())

    def prompt_for_radio_message(self):
        text, ok = QInputDialog.getText(window, 'Simulate Radio Message', 'Packet content:')
        if ok:
            self.worker_thread.controller.parse_message(text)

    def closeEvent(self, event):
        self.controller.terminate()
        while self.controller.is_running:
            time.sleep(0.01)


class ControllerSignals(QObject):
    update_pose = Signal(list)
    update_state = Signal(dict)
    update_packet = Signal(str, bool)


class BackgroundThread(QThread):
    def __init__(self, parent, controller):
        QThread.__init__(self, parent)
        self.controller = controller
        # connect signals
        self.signals = ControllerSignals()
        self.signals.update_pose.connect(parent.update_pose)
        self.signals.update_packet.connect(parent.update_packet)
        self.signals.update_state.connect(parent.update_state)
        controller.set_parent(self)

    def run(self):
        self.controller.loop()

    def terminate(self):
        self.controller.terminate()


def load_language(lan):
    with open('languages/translations.json', 'r', encoding='utf-8') as file:
        translations = json.load(file)
    language = lan
    if lan not in translations:
        language = 'de'  # Default language
    translation = translations[language]
    return translation


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='TecDay UI')
    parser.add_argument('-l', '--left', type=str, default="/dev/tty-dobot-left",
                        help="serial port device of the left Dobot")
    parser.add_argument('-r', '--right', type=str, default="/dev/tty-dobot-right",
                        help="serial port device of the right Dobot")
    parser.add_argument('-m', '--microbit', type=str, default="/dev/tty-microbit",
                        help="serial port device of the Micro:bit")
    parser.add_argument('-s', '--sim', default=False, action='store_true',
                        help="simulation mode (use without hardware)")
    parser.add_argument('-lang', '--language', default="de",
                        help="change language of the UI (options: de (default), en, it)")
    args = parser.parse_args()

    language_dictionary = load_language(args.language)

    # check if the serial port devices are available
    if not args.sim:
        if not os.path.exists(args.left):
            print("Error: Serial port device for left dobot does not exist: '%s'\nIs the dobot connected and powered up?" % args.left)
            sys.exit(1)

        if not os.path.exists(args.right):
            print("Error: Serial port device for right dobot does not exist: '%s'\nIs the dobot connected and powered up?" % args.right)
            sys.exit(1)

        if not os.path.exists(args.microbit):
            print("Error: Serial port device for the micro:bit radio sniffer does not exist: '%s'\nIs the micro:bit connected?" % args.microbit)
            sys.exit(1)
    else:
        print("Running in simulation mode")

    # initialize controller
    controller_instance = Controller(args.left, args.right, args.microbit, NUM_TASKS, args.sim)

    # initialize gui application
    app = QApplication(sys.argv)
    window = Window(controller_instance)
    window.showMaximized()
    window.worker_thread.start()
    sys.exit(app.exec())