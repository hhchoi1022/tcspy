

#%%
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QGridLayout, QLabel, QGroupBox, QMainWindow, QAction
from PyQt5.QtGui import QPainter, QColor, QFont
from PyQt5.QtCore import Qt, QTimer

# Sample status dictionary (replace with your actual status data)
status_data = {
    '7DT01': {'camera': 'idle', 'telescope': 'idle', 'filterwheel': 'busy', 'focuser': 'idle', 'weather': 'idle', 'safetymonitor' : 'idle'},
    '7DT02': {'camera': 'busy', 'telescope': 'tracking', 'filterwheel': 'idle', 'focuser': 'idle', 'weather': 'idle', 'safetymonitor' : 'idle'},
    '7DT03': {'camera': 'busy', 'telescope': 'tracking', 'filterwheel': 'idle', 'focuser': 'idle', 'weather': 'idle', 'safetymonitor' : 'idle'},
    '7DT04': {'camera': 'busy', 'telescope': 'tracking', 'filterwheel': 'idle', 'focuser': 'idle', 'weather': 'idle', 'safetymonitor' : 'idle'},
    '7DT05': {'camera': 'busy', 'telescope': 'tracking', 'filterwheel': 'idle', 'focuser': 'idle', 'weather': 'idle', 'safetymonitor' : 'idle'},
    '7DT06': {'camera': 'busy', 'telescope': 'tracking', 'filterwheel': 'idle', 'focuser': 'idle', 'weather': 'idle', 'safetymonitor' : 'idle'},
    '7DT07': {'camera': 'busy', 'telescope': 'tracking', 'filterwheel': 'idle', 'focuser': 'idle', 'weather': 'idle', 'safetymonitor' : 'idle'},
    '7DT08': {'camera': 'busy', 'telescope': 'tracking', 'filterwheel': 'idle', 'focuser': 'idle', 'weather': 'idle', 'safetymonitor' : 'idle'},
    '7DT09': {'camera': 'busy', 'telescope': 'tracking', 'filterwheel': 'idle', 'focuser': 'idle', 'weather': 'idle', 'safetymonitor' : 'idle'},
    '7DT10': {'camera': 'busy', 'telescope': 'tracking', 'filterwheel': 'idle', 'focuser': 'idle', 'weather': 'idle', 'safetymonitor' : 'idle'},
    '7DT11': {'camera': 'busy', 'telescope': 'tracking', 'filterwheel': 'idle', 'focuser': 'idle', 'weather': 'idle', 'safetymonitor' : 'idle'},
    '7DT12': {'camera': 'busy', 'telescope': 'tracking', 'filterwheel': 'idle', 'focuser': 'idle', 'weather': 'idle', 'safetymonitor' : 'idle'},
    '7DT13': {'camera': 'busy', 'telescope': 'tracking', 'filterwheel': 'idle', 'focuser': 'idle', 'weather': 'idle', 'safetymonitor' : 'idle'},
    '7DT14': {'camera': 'busy', 'telescope': 'tracking', 'filterwheel': 'idle', 'focuser': 'idle', 'weather': 'idle', 'safetymonitor' : 'idle'},
    '7DT15': {'camera': 'busy', 'telescope': 'tracking', 'filterwheel': 'idle', 'focuser': 'idle', 'weather': 'idle', 'safetymonitor' : 'idle'},
    '7DT16': {'camera': 'busy', 'telescope': 'tracking', 'filterwheel': 'idle', 'focuser': 'idle', 'weather': 'idle', 'safetymonitor' : 'idle'},
    '7DT17': {'camera': 'busy', 'telescope': 'tracking', 'filterwheel': 'idle', 'focuser': 'idle', 'weather': 'idle', 'safetymonitor' : 'idle'},
    '7DT18': {'camera': 'busy', 'telescope': 'tracking', 'filterwheel': 'idle', 'focuser': 'idle', 'weather': 'idle', 'safetymonitor' : 'idle'},
    '7DT19': {'camera': 'busy', 'telescope': 'tracking', 'filterwheel': 'idle', 'focuser': 'idle', 'weather': 'idle', 'safetymonitor' : 'idle'},
    '7DT20': {'camera': 'busy', 'telescope': 'tracking', 'filterwheel': 'idle', 'focuser': 'idle', 'weather': 'idle', 'safetymonitor' : 'idle'}
    # Add status data for other telescopes...
}

class TelescopeStatusWidget(QWidget):
    def __init__(self, tel_status):
        super().__init__()
        self.tel_status = tel_status

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        for i, (comp, status) in enumerate(self.tel_status.items()):
            color = self._get_color(status)
            painter.setBrush(QColor(color))
            painter.drawEllipse(50, 30 * i, 10, 10)  # Adjust circle dimensions

            painter.setFont(QFont('Arial', 8))  # Adjust font size
            painter.drawText(100, 10 + 30 * i, f"{comp.capitalize()}: {status.capitalize()}")

    def _get_color(self, status):
        if status == 'disconnected':
            return 'red'
        elif status == 'idle':
            return 'green'
        else:
            return 'yellow'

class StatusMonitorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Telescope Status Monitor')

        # Create menus
        status_menu = self.menuBar().addMenu('Status')
        other_menu = self.menuBar().addMenu('Other')

        # Add actions to the "Status" menu
        status_action = QAction('Telescope Status', self)
        status_action.triggered.connect(self.show_telescope_status)
        status_menu.addAction(status_action)

        # Add actions to the "Other" menu
        # Add your other actions here...

        self.layout = QGridLayout()
        self.layout.setVerticalSpacing(5)  # Adjust vertical spacing
        self.layout.setHorizontalSpacing(5)  # Adjust horizontal spacing

        self.update_status()  # Initial update

        # Create a QTimer object to trigger update every 5 seconds
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_status)
        self.timer.start(5000)  # 5000 milliseconds = 5 seconds

        central_widget = QWidget()
        central_widget.setLayout(self.layout)
        self.setCentralWidget(central_widget)

    def update_status(self):
        # Simulate updating status data dynamically (replace with your actual update mechanism)
        # For demonstration, simply toggle between 'idle' and 'busy' status for the telescopes
        for tel_name, tel_status in status_data.items():
            for comp in tel_status:
                if tel_status[comp] == 'idle':
                    tel_status[comp] = 'busy'
                else:
                    tel_status[comp] = 'idle'

        # Update the displayed status widgets
        self.update_status_widgets()

    def update_status_widgets(self):
        # Clear the layout
        for i in reversed(range(self.layout.count())):
            item = self.layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)

        # Add updated status widgets
        row = 0
        col = 0
        for tel_name, tel_status in status_data.items():
            group_box = QGroupBox()
            group_box_layout = QGridLayout()
            telescope_widget = TelescopeStatusWidget(tel_status)
            group_box_layout.addWidget(telescope_widget, 1, 0, 1, 2)
            title_label = QLabel(tel_name)
            title_label.setAlignment(Qt.AlignCenter)
            title_label.setFont(QFont('Arial', 12, QFont.Bold))  # Adjust font size
            group_box_layout.addWidget(title_label, 0, 0, 1, 2)
            group_box_layout.setRowStretch(0,1)
            group_box_layout.setRowStretch(1,4)
            group_box.setLayout(group_box_layout)
            self.layout.addWidget(group_box, row, col)
            col += 1
            if col == 5:
                col = 0
                row += 1

    def show_telescope_status(self):
        self.update_status()  # Update status before showing
        self.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_app = StatusMonitorApp()
    main_app.show()
    sys.exit(app.exec_())
    
# %%
