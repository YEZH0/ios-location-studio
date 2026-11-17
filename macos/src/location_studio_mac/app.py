"""Native Qt desktop control panel. GPL-3.0-only."""
import sys

# Worker dispatch must precede GUI initialization, including in the frozen bundle.
if '--worker' in sys.argv:
    from .worker import run
    run()
    raise SystemExit

import time
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, Signal, QPointF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QFormLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QFileDialog,
    QComboBox, QMessageBox, QPlainTextEdit, QSplitter)
from .engine import Engine, State, validate

CITIES = {'纽约 · New York': (40.7128,-74.0060), '伦敦 · London': (51.5074,-0.1278),
          '东京 · Tokyo': (35.6762,139.6503), '悉尼 · Sydney': (-33.8688,151.2093),
          '巴黎 · Paris': (48.8566,2.3522), '新加坡 · Singapore': (1.3521,103.8198)}


class Grid(QWidget):
    selected = Signal(float,float)
    def __init__(self):
        super().__init__(); self.lat = 40.7128; self.lon = -74.0060
        self.setMinimumSize(380,240)
        self.setAccessibleName('离线经纬度网格；也可使用左侧坐标输入')
        self.setCursor(Qt.CrossCursor)

    def paintEvent(self, event):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor('#0d131b'))
        w,h=self.width(),self.height()
        p.setPen(QPen(QColor('#263748'),1))
        for lon in range(-180,181,30):
            x=(lon+180)/360*w; p.drawLine(QPointF(x,0),QPointF(x,h))
        for lat in range(-90,91,30):
            y=(90-lat)/180*h; p.drawLine(QPointF(0,y),QPointF(w,y))
        p.setPen(QColor('#a4b5c9'))
        p.drawText(16,26,'90° N'); p.drawText(16,h-16,'90° S')
        p.drawText(w-76,26,'180° E')
        x=(self.lon+180)/360*w; y=(90-self.lat)/180*h
        p.setPen(QPen(QColor('#22d3ee'),2)); p.setBrush(QColor('#22d3ee'))
        p.drawEllipse(QPointF(x,y),6,6)
        p.drawLine(QPointF(x-16,y),QPointF(x+16,y)); p.drawLine(QPointF(x,y-16),QPointF(x,y+16))

    def mousePressEvent(self, event):
        if self.isEnabled():
            self.selected.emit(90-event.position().y()/self.height()*180,
                               event.position().x()/self.width()*360-180)


class Window(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle('iOS Location Studio · macOS'); self.resize(1080,800)
        self.engine=Engine(); self.state=State(); self.mode=None; self.deadline=None
        self.closing=False; self.sending=False; self.needs_restore=False
        self.engine.event.connect(self.on_event); self.engine.ended.connect(self.on_end)
        root=QWidget(); self.setCentralWidget(root); outer=QVBoxLayout(root); outer.setContentsMargins(28,24,28,24); outer.setSpacing(16)
        title=QLabel('iOS Location Studio'); title.setObjectName('title'); outer.addWidget(title)
        outer.addWidget(QLabel('macOS · USB iAP2 定位实验室   /   欧耶哥爱数码'))
        warning=QLabel('实验性方案：认证成功或收到 ACK 不等于 iPhone 采用了模拟位置。请在手机上验证，并在结束后确认恢复。')
        warning.setWordWrap(True); warning.setObjectName('warning'); outer.addWidget(warning)
        split=QSplitter(); outer.addWidget(split,1)
        left=QWidget(); form=QVBoxLayout(left); form.setContentsMargins(0,0,22,0); form.setSpacing(12)
        self.device=QLabel('USB：尚未检测。请连接、解锁并信任此电脑。'); self.device.setWordWrap(True); form.addWidget(self.device)
        self.detect=QPushButton('检测 USB 设备'); self.detect.clicked.connect(lambda:self.launch('device')); form.addWidget(self.detect)
        self.cert=QLineEdit(); self.key=QLineEdit()
        default=Path.home()/'Library/Application Support/accessory-location/identity'
        for field,name in ((self.cert,'certificate.p7b'),(self.key,'identity.pk8')):
            if (default/name).is_file(): field.setText(str(default/name))
            field.setPlaceholderText('选择本地文件，不上传'); field.setReadOnly(True)
        form.addWidget(QLabel('MFi-v3 认证材料 · 仅本机'))
        for label,field in [('证书',self.cert),('私钥',self.key)]:
            row=QHBoxLayout(); row.addWidget(field); button=QPushButton('选择'+label)
            button.clicked.connect(lambda checked=False,f=field:self.pick(f)); row.addWidget(button); form.addLayout(row)
        self.probe=QPushButton('仅检查通信与认证（20 秒）'); self.probe.clicked.connect(lambda:self.launch('probe')); form.addWidget(self.probe)
        form.addWidget(QLabel('目标位置 · WGS-84'))
        self.city=QComboBox(); self.city.setEditable(True); self.city.addItems(CITIES)
        self.city.setToolTip('离线搜索内置城市；其他位置请输入坐标')
        self.city.currentTextChanged.connect(self.city_changed); form.addWidget(self.city)
        fields=QFormLayout(); self.lat=QLineEdit('40.712800'); self.lon=QLineEdit('-74.006000')
        fields.addRow('纬度',self.lat); fields.addRow('经度',self.lon)
        self.duration=QSpinBox(); self.duration.setRange(1,3600); self.duration.setValue(180); self.duration.setSuffix(' 秒')
        fields.addRow('测试时长',self.duration); form.addLayout(fields)
        self.start=QPushButton('开始限时模拟'); self.start.setObjectName('primary'); self.start.clicked.connect(lambda:self.launch('send')); form.addWidget(self.start)
        self.stop=QPushButton('停止发送 / 断开会话'); self.stop.clicked.connect(self.engine.stop); self.stop.setEnabled(False); form.addWidget(self.stop)
        self.countdown=QLabel('未运行'); form.addWidget(self.countdown); form.addStretch()
        right=QWidget(); r=QVBoxLayout(right); r.setContentsMargins(16,0,0,0); r.setSpacing(12)
        r.addWidget(QLabel('离线坐标网格 · 点击选点（不是街道地图）'))
        self.grid=Grid(); self.grid.selected.connect(self.set_coordinates); r.addWidget(self.grid,1)
        self.status=QLabel(); self.status.setWordWrap(True); r.addWidget(self.status)
        self.map_button=QPushButton('我已在 iPhone 地图确认位置改变'); self.map_button.setEnabled(False)
        self.map_button.clicked.connect(self.confirm_map); r.addWidget(self.map_button)
        self.restore=QPushButton('确认已断开 USB 并恢复真实定位'); self.restore.setEnabled(False)
        self.restore.clicked.connect(self.confirm_restore); r.addWidget(self.restore)
        self.log=QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumBlockCount(120); self.log.setMaximumHeight(160); r.addWidget(self.log)
        split.addWidget(left); split.addWidget(right); split.setSizes([390,640])
        footer=QLabel('仅用于合法定位测试。上游：aur3l14no/accessory-location · GPL-3.0-only\n不内置共享身份，不自动安装认证材料，不发送设备标识或坐标至第三方。')
        footer.setWordWrap(True); outer.addWidget(footer)
        self.timer=QTimer(self); self.timer.timeout.connect(self.tick); self.timer.start(250)
        self.refresh()

    def pick(self,field):
        if self.engine.running: return
        path,_=QFileDialog.getOpenFileName(self,'选择本地 MFi 身份文件')
        if path: field.setText(path)

    def city_changed(self,text):
        if text in CITIES: self.set_coordinates(*CITIES[text])

    def set_coordinates(self,lat,lon):
        self.lat.setText(f'{lat:.6f}'); self.lon.setText(f'{lon:.6f}')
        self.grid.lat=lat; self.grid.lon=lon; self.grid.update()

    def launch(self,mode):
        try:
            if self.needs_restore and mode=='send':
                raise ValueError('请先完成上次会话的真实定位恢复确认')
            lat,lon,duration=validate(self.lat.text(),self.lon.text(),self.duration.value()) if mode=='send' else (0,0,20)
            if mode=='send':
                answer=QMessageBox.question(self,'确认定位测试',f'向 iPhone 发送 WGS-84 坐标 {lat:.6f}, {lon:.6f}，持续 {duration} 秒？\n请在手机苹果地图点击当前位置。')
                if answer!=QMessageBox.Yes: return
            if mode!='device':
                from .worker import resources
                import importlib.util
                spec=importlib.util.spec_from_file_location('mfi_validation',resources()/'tools/local_mfi_v3_helper.py')
                module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
                module.validate_identity(Path(self.cert.text()).read_bytes(),Path(self.key.text()).read_bytes())
            self.state=State(); self.mode=mode
            self.engine.start(mode,self.cert.text(),self.key.text(),lat,lon,duration)
            self.deadline=time.monotonic()+duration; self.sending=mode=='send'
            if self.sending: self.needs_restore=True
            self.log.clear(); self.refresh()
        except Exception as e:
            # Do not display file data or identifiers in arbitrary exception messages.
            text=str(e) if isinstance(e,ValueError) else '请检查所选证书、私钥的格式与匹配关系。'
            QMessageBox.warning(self,'无法启动',text)

    def on_event(self,event):
        self.state.consume(event)
        name=event.get('event','unknown')
        labels={'device_connected':'USB 已连接','identification_accepted':'身份识别已接受',
                'authentication_succeeded':'认证成功','location_requested':'手机请求定位订阅',
                'location_stopped':'手机停止订阅','location_link_acknowledged':'链路 ACK（不代表位置采纳）',
                'error':'协议错误，请检查手机连接、身份有效性与兼容性',
                'process_error':'进程启动失败，请检查沙箱和应用完整性',
                'interrupted':'会话已停止','finished':'限时会话已结束','process_exit':'工作进程已退出'}
        if name=='device_ready': self.device.setText(f'USB 已配对 · {event["model"]} · iOS {event["ios"]}')
        if name=='device_count': self.device.setText('请仅连接一台 USB iPhone，再解锁并信任后重试。')
        if name=='device_error': self.device.setText('连接失败：检查 USB、解锁与信任授权。')
        if name in labels: self.log.appendPlainText(labels[name])
        self.refresh()

    def refresh(self):
        busy=self.engine.running
        for widget in (self.detect,self.probe,self.start,self.city,self.lat,self.lon,self.duration,self.grid): widget.setEnabled(not busy)
        self.stop.setEnabled(busy)
        self.map_button.setEnabled(busy and self.sending and self.state.acks>0 and not self.state.map_verified)
        self.restore.setEnabled(not busy and self.needs_restore)
        self.status.setText(f'身份识别：{"已接受" if self.state.identified else "未验证"}   ·   认证：{"成功" if self.state.authenticated else "未验证"}\n订阅：{"活跃" if self.state.subscribed else "未订阅 / 已停止"}   ·   ACK：{self.state.acks}\n手机位置：{"用户已确认改变" if self.state.map_verified else "尚未人工验证"}   ·   恢复：{"用户已确认" if self.state.restored else "未确认"}')

    def tick(self):
        if self.engine.running and self.deadline:
            self.countdown.setText(f'会话剩余约 {max(0,int(self.deadline-time.monotonic()))} 秒 · 连接握手最多额外 30 秒')
        else: self.countdown.setText('未运行 · 无后台定位任务' if not self.engine.running else '正在停止')
        self.refresh()

    def on_end(self):
        self.deadline=None; self.refresh()
        if self.needs_restore:
            self.log.appendPlainText('请断开 USB，在苹果地图确认真实位置。若仍保留模拟位置，关闭定位服务约 10 秒再开启。')
        if self.closing: self.close()

    def confirm_map(self):
        self.state.map_verified=True; self.refresh()

    def confirm_restore(self):
        if QMessageBox.question(self,'真实定位验证','已断开 USB，并在苹果地图看到真实位置了吗？')==QMessageBox.Yes:
            self.state.restored=True; self.needs_restore=False; self.refresh()

    def closeEvent(self,event):
        if self.engine.running:
            self.closing=True; self.engine.stop(); event.ignore()
        else:
            if self.needs_restore:
                QMessageBox.information(self,'恢复提醒','发送已停止。请断开 USB 并在手机确认真实定位恢复；本应用未验证恢复结果。')
            event.accept()


def main():
    app=QApplication(sys.argv); app.setApplicationName('iOS Location Studio')
    app.setStyleSheet('''
    QWidget {background:#070a0f;color:#e8eef7;font-size:13px;}
    QLabel#title {font-size:28px;font-weight:600;}
    QLabel#warning {color:#fbbf24;padding:12px;background:#1c1910;}
    QLineEdit,QComboBox,QSpinBox,QPlainTextEdit {background:#111922;border:1px solid #35485e;padding:8px;border-radius:5px;}
    QPushButton {background:#16202b;border:1px solid #35485e;border-radius:5px;padding:10px;}
    QPushButton:hover {border-color:#22d3ee;} QPushButton:focus {border:2px solid #22d3ee;}
    QPushButton#primary {background:#22d3ee;color:#070a0f;font-weight:600;}
    QPushButton:disabled {color:#8c9daf;background:#111922;}
    QSplitter::handle {background:#263748;width:1px;}
    ''')
    window=Window(); window.show(); return app.exec()

if __name__=='__main__': raise SystemExit(main())
