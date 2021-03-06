#! /usr/bin/env python

import qt
from ui_mainwindow import MainWindowBase
from ui_connectprogresswindow import ConnectProgressWindowBase
import sys
import systray
import re 

SETTINGS = qt.QSettings()

def get_file(name):
    import binary_data
    return "".join([chr(i) for i in binary_data.get_file(name)])

def format_duration(second_count):
    second_count = int(second_count)
    if second_count == 1:
        return app.translate("dateformat", 
                "1 second")
    elif second_count in [0]+range(2,60):
        return app.translate("dateformat",
                "%1 seconds")\
                .arg(second_count)
    elif 60 <= second_count < 119:
        return app.translate("dateformat",
                "1 minute %1 seconds")\
                .arg(second_count-60)
    else:
        return app.translate("dateformat",
                "%1 minutes %2 seconds")\
                .arg(second_count/60)\
                .arg(second_count%60)

class ConnectionError(Exception):
    def __init__(self, reason):
        self.Reason = str(reason)

    def __str__(self):
        return self.Reason

class RequestError(Exception):
    def __init__(self, status, reason):
        self.Status = status
        self.Reason = reason

    def __str__(self):
        return "Request failed: %d %s" % (\
            self.Status, self.Reason)

    def status(self):
        return self.Status

    def reason(self):
        return self.Reason

class ConnectionManager(object):
    def __init__(self, base_url, station, password):
        self.BaseURL = base_url
        self.Station = station
        self.Password = password

        self.Connections = None

    def _station(self):
        return self.Station
    station = property(_station)

    def set_credentials(self, station, password):
        self.Station = station
        self.Password = password

    def request(self, op, **parameters):
        import httplib
        import urlparse
        import re
        import md5
        import socket

        scheme, netloc, path, query, fragment = urlparse.urlsplit(str(self.BaseURL))
        host_port_match = re.match("([a-zA-Z0-9\.]+)(\:[0-9]+)?", netloc)
        if host_port_match.group(2) is None:
            port = httplib.HTTP_PORT
        else:
            port = int(host_port_match.group(2))
        host = host_port_match.group(1)

        my_par = parameters.copy()
        my_par["auth"] = md5.new(self.Station+":"+self.Password).hexdigest()
        my_par["mode"] = op
        my_par["station"] = self.Station

        try:
            conn = httplib.HTTPConnection(netloc, 80)
            request = path + "?" + \
                    "&".join(["%s=%s" % (key,value) 
                        for key,value in my_par.iteritems()])
            conn.request("GET", request)
            response = conn.getresponse()
            result = response.read()
        except socket.error, err:
            raise ConnectionError, str(err)
        status_code = response.status
        reason = response.reason

        if status_code != 200:
            raise RequestError, (status_code, reason)
        return result

    def is_valid(self):
        try:
            return self.request("hello").startswith("olleh konnekte")
        except ConnectionError:
            return False
        except RequestError:
            return False

    def is_authenticated(self):
        try:
            self.request("state")
            return True
        except ConnectionError:
            return False
        except RequestError:
            return False

    def is_right_version(self):
        try:
            prot_ver = int(self.request("version"))
            return prot_ver == 1
        except ValueError:
            return False
        except ConnectionError:
            return False
        except RequestError:
            return False

    def get_state(self):
        s_text = self.request("state")
        s_lines = s_text.split("\n")
        vars = {}
        for line in s_lines:
            match = re.match("^([a-z]+)\: (.*)$", line)
            if match:
                vars[match.group(1)] = match.group(2)

        if not "state" in vars:
            raise ValueError, "Invalid state: no state variable"

        if vars["state"] == "connected":
            return UIState(self, UIState.CONNECTED,
                    connection=vars["connection"],
                    duration=int(vars["now"])-int(vars["start"]),
                    heldby=vars["holders"].split())
        elif vars["state"] == "disconnected":
            return UIState(self, UIState.DISCONNECTED)
        else:
            raise ValueError, "Invalid state: invalid state variable"

    def is_connected(self):
        return self.get_state().Code == UIState.CONNECTED

    def get_connections(self):
        c_text = self.request("connections")
        c_lines = c_text.split("\n")
        connections = {}
        for line in c_lines:
            match = re.match("^([a-z]+)\:([a-z]+)=(.*)$", line)
            if match:
                cnx = match.group(1)
                if cnx in connections:
                    connections[cnx][match.group(2)] = match.group(3)
                else:
                    connections[cnx] = {match.group(2): match.group(3)}

        return connections

    def _cached_connections(self):
        if self.Connections is None:
            self.Connections = self.get_connections()
            
        return self.Connections
    cached_connections = property(_cached_connections)

    def connect(self, connection):
        self.request("connect", connection=connection)

    def disconnect(self):
        self.request("disconnect")

    def force_disconnect(self):
        self.request("force_disconnect")

    def get_log(self):
        import time

        class ConnectionDetail:
            def __init__(self, stations=[], start=None, end=None, connection=None):
                self.Stations = stations[:]
                self.Start = start
                self.End = end
                self.Connection = connection

            def __str__(self):
                return "ConnectionDetail(%s, %s, %s, %s)" % \
                        (self.Stations, self.Start, self.End,
                                self.Connection)

        lines = self.request("log").split("\n")
        now_line = lines[0]
        lines = lines[1:]
        now = int(now_line.split()[1])
        real_now = time.time()
        delta_now = real_now - now

        connections = []
        curdetail = ConnectionDetail()
        for line in lines:
            if not line.strip():
                continue
            what = line.split()[1]
            when = int(line.split()[0]) + delta_now

            if what == "CONNECT":
                stationmatch = re.search("station:([a-zA-Z0-9_]+)", line)
                curdetail.Stations.append(stationmatch.group(1))
                if curdetail.Start is None:
                    curdetail.Start = when
            elif what == "PHYS_CONNECT":
                cnxmatch = re.search("cnx:([a-z0-9_]*)", line)
                curdetail.Connection = cnxmatch.group(1)
            elif what == "PHYS_DISCONNECT":
                if curdetail.Start is not None:
                    curdetail.End = when
                    connections.append(curdetail)
                    curdetail = ConnectionDetail()

        return connections

    def get_connect_log(self):
        return self.request("connectlog")

class UIState(object):
    DISABLED = 1
    DISCONNECTED = 2
    CONNECTED = 3

    def __init__(self, mgr, code, textual=None, connection=None, duration=None, heldby=None):
        self.Manager = mgr
        self.Code = code
        self.Textual = textual
        self.Connection = connection
        self.Duration = duration
        self.HeldBy = heldby

    def _text(self):
        if self.Textual is not None:
            return self.Textual
        else:
            return {UIState.DISABLED: app.translate("states", "Error"),
                    UIState.DISCONNECTED: app.translate("states", "Disconnected"),
                    UIState.CONNECTED: app.translate("states", "Connected")}[self.Code]
    text = property(_text)

    def are_we_holding_a_connection(self):
        return self.Code == UIState.CONNECTED and  self.Manager.station in self.HeldBy

class ConnectProgressWindow(ConnectProgressWindowBase):
    def __init__(self, parent, manager):
        ConnectProgressWindowBase.__init__(self, parent)
        self.Manager = manager
        self.Log = ""
        qt.QTimer.singleShot(1000, self.update)

    def update_once(self):
        if self.Manager.is_connected():
            self.close()
            return False

        self.progress.setProgress(self.progress.progress()+10)

        new_log = self.Manager.get_connect_log()
        if new_log != self.Log:
            self.textLog.setUpdatesEnabled(False)
            self.textLog.setText(new_log)
            self.textLog.scrollToBottom()
            self.textLog.setUpdatesEnabled(True)
            self.textLog.update()
            self.Log = new_log

        return True

    def update(self):
        continue_updates = True
        try:
            continue_updates = self.update_once()
        finally:
            if continue_updates:
                qt.QTimer.singleShot(1000, self.update)

    def exec_loop(self):
        ConnectProgressWindowBase.exec_loop(self)
        if not self.Manager.is_connected():
            self.Manager.disconnect()

class MainWindow(MainWindowBase):
    def __init__(self):
        MainWindowBase.__init__(self)

        base_url = str(SETTINGS.readEntry("/konnekte/base_url", "http://sprite/konnekte")[0])
        station = str(SETTINGS.readEntry("/konnekte/station")[0])
        password = str(SETTINGS.readEntry("/konnekte/password")[0])
        self.editStation.setText(station)
        self.editPassword.setText(password)

        self.Manager = ConnectionManager(base_url, station, password)

        self.load_icons()
        self.setIcon(self.Icon)

        self.TrayIcon = systray.SystrayIcon(self.SmallOffIcon, self)
        self.connect(self.TrayIcon, qt.PYSIGNAL("activated()"), 
                self.toggle_show)
        self.connect(self.TrayIcon, 
                qt.PYSIGNAL("contextMenuRequested(const QPoint &)"), 
                self.tray_rightclick)

        self.actionShowHide = qt.QAction("DOESNOTMATTER", qt.QKeySequence(), self)
        self.connect(self.actionShowHide,
                qt.SIGNAL("activated()"), self.toggle_show)

        self.actionDisconnect = qt.QAction(self.tr("&Disconnect"), qt.QKeySequence(), self)
        self.connect(self.actionDisconnect,
                qt.SIGNAL("activated()"), self.do_disconnect)

        self.PopupMenu = qt.QPopupMenu()
        self.actionShowHide.addTo(self.PopupMenu)
        self.actionDisconnect.addTo(self.PopupMenu)
        self.actionQuit.addTo(self.PopupMenu)

        self.toggle_show()

        self.connect(self.editStation, qt.SIGNAL("textChanged(const QString &)"), self.update_credentials)
        self.connect(self.editPassword, qt.SIGNAL("textChanged(const QString &)"), self.update_credentials)

        self.connect(self.btnConnect, qt.SIGNAL("clicked()"), self.do_connect)
        self.connect(self.btnDisconnect, qt.SIGNAL("clicked()"), self.do_disconnect)
        self.connect(self.btnViewLog, qt.SIGNAL("clicked()"), self.view_log)

        self.connect(self.actionAbout, qt.SIGNAL("activated()"), self.about)

        self.State = None
        self.update_state()

    def update_credentials(self, dummy):
        station = str(self.editStation.text())
        password = str(self.editPassword.text())
        self.Manager.set_credentials(station, password)

    def load_icons(self):
        icon_image = qt.QImage(qt.QByteArray(get_file("main.png")))
        small_icon_image = icon_image.smoothScale(22, 22, 
                qt.QImage.ScaleMin)
        self.Icon = qt.QPixmap(icon_image)
        self.SmallIcon = qt.QPixmap(small_icon_image)

        off_icon_image = qt.QImage(qt.QByteArray(get_file("main-off.png")))
        small_off_icon_image = off_icon_image.smoothScale(22, 22, 
                qt.QImage.ScaleMin)
        self.OffIcon = qt.QPixmap(off_icon_image)
        self.SmallOffIcon = qt.QPixmap(small_off_icon_image)

    def toggle_show(self):
        if self.isHidden():
            self.show()
            self.raiseW()
            if self.isMinimized():
                self.showNormal()
            self.actionShowHide.setMenuText(self.tr("&Hide Main Window"))
            self.actionShowHide.setText(self.tr("Hide main window"))
        else:
            self.hide()
            self.actionShowHide.setMenuText(self.tr("&Show Main Window"))
            self.actionShowHide.setText(self.tr("Show main window"))

    def tray_rightclick(self, pos):
        self.PopupMenu.popup(pos)

    def set_state(self, state):
        if self.State is None or self.State.Code != state.Code:
            if state.Code == UIState.CONNECTED:
                self.TrayIcon.setPixmap(self.SmallIcon)
            else:
                self.TrayIcon.setPixmap(self.SmallOffIcon)
            self.TrayIcon.update()

            self.btnConnect.setEnabled(not state.are_we_holding_a_connection())
            self.btnDisconnect.setEnabled(state.Code == UIState.CONNECTED)
            self.actionDisconnect.setEnabled(state.Code == UIState.CONNECTED)

            self.editStation.setEnabled(not state.are_we_holding_a_connection())
            self.editPassword.setEnabled(not state.are_we_holding_a_connection())
            self.btnViewLog.setEnabled(state.Code != UIState.DISABLED)

        def examine_and_change(attrname, widget, format_func=lambda x: x):
            if self.State is None or getattr(state, attrname) != getattr(self.State, attrname):
                if getattr(state, attrname) is None:
                    widget.setText("-/-")
                else:
                    widget.setText(format_func(getattr(state, attrname)))

        def format_connection(conn_id):
            return self.Manager.cached_connections[conn_id]["name"]

        examine_and_change("text", self.lblState)
        examine_and_change("Connection", self.lblConnection, format_connection)
        examine_and_change("Duration", self.lblDuration, format_duration)
        examine_and_change("HeldBy", self.lblStation, lambda x: ", ".join(x))

        self.State = state

    def update_state_once(self):
        try:
            self.set_state(self.Manager.get_state())
        except RequestError, e:
            self.set_state(UIState(self.Manager, UIState.DISABLED, self.diagnose_failure()))
        except ConnectionError, e:
            self.set_state(UIState(self.Manager, UIState.DISABLED, self.diagnose_failure()))

    def update_state(self):
        try:
            self.update_state_once()
        finally:
            qt.QTimer.singleShot(1000, self.update_state)

    def do_connect(self):
        if self.State.Code == UIState.CONNECTED:
            if not self.State.are_we_holding_a_connection():
                self.Manager.connect("tagalong")
            return

        connections = self.Manager.get_connections()
        conn_names = list(connections.keys())
        conn_names.sort()

        from ui_connectwindow import ConnectWindow

        cw = ConnectWindow(self)
        for name in conn_names:
            cw.comboConnection.insertItem(connections[name]["name"])

        def show_description(index):
            cw.lblDescription.setText(connections[conn_names[index]]["description"])

        self.connect(cw.comboConnection, qt.SIGNAL("highlighted(int)"), 
                show_description)
        show_description(cw.comboConnection.currentItem())
        if cw.exec_loop() == qt.QDialog.Accepted:
            self.Manager.connect(conn_names[cw.comboConnection.currentItem()])
            self.accompany_connect()

    def accompany_connect(self):
        cpw = ConnectProgressWindow(self, self.Manager)
        cpw.exec_loop()

    def do_disconnect(self):
        if self.State.are_we_holding_a_connection():
            self.Manager.disconnect()
            self.update_state_once()
        elif self.State.Code == UIState.CONNECTED:
            if qt.QMessageBox.information(self,
                    "Konnekte",
                    self.tr("Other stations are connected at present. Force disconnection?"),
                    qt.QMessageBox.Yes,
                    qt.QMessageBox.No) == qt.QMessageBox.Yes:
                self.Manager.force_disconnect()
                self.update_state_once()

    def view_log(self):
        from ui_logwindow import LogWindow
        import time

        def lookup_connection(cnx_id):
            try:
                return self.Manager.cached_connections[cnx_id]["name"]
            except KeyError:
                return str(cnx_id)

        def get_duration_str(start, end):
            if start is None or end is None:
                return self.tr("None")
            return format_duration(end-start)

        def get_time_str(secs):
            if secs is None:
                return self.tr("None")
            else:
                return time.strftime(
                        "%Y-%m-%d %H:%M",
                        time.localtime(cdetail.Start))

        lw = LogWindow(self)
        lw.listConnections.setSorting(-1, True)
        lw.textPPPLog.setText(self.Manager.get_connect_log())
        clog = self.Manager.get_log()
        last = None
        for cdetail in clog:
            columns = [get_time_str(cdetail.Start),
                    get_duration_str(cdetail.Start, cdetail.End),
                    ", ".join(cdetail.Stations),
                    lookup_connection(cdetail.Connection)]
            if last is not None:
                last = qt.QListViewItem(
                        lw.listConnections, last,
                        *columns)
            else:
                last = qt.QListViewItem(
                        lw.listConnections, *columns)

        lw.exec_loop()

    def diagnose_failure(self):
        if not self.Manager.is_valid():
            return self.tr("There was some trouble connecting to the gateway.")
        if not self.Manager.is_authenticated():
            return self.tr("The gateway did not accept the station/password combination.")
        if not self.Manager.is_right_version():
            return self.tr("The gateway uses an incompatible protocol.")

    def about(self):
        qt.QMessageBox.information(self,
                "Konnekte",
                self.tr("Konnekte (C) Andreas Kloeckner 2006"),
                qt.QMessageBox.Ok)
        
    def closeEvent(self, ev):
        if self.State.are_we_holding_a_connection():
            qt.QMessageBox.information(self,
                    "Konnekte",
                    self.tr("Cannot quit because there is still an active connection held."),
                    qt.QMessageBox.Ok)
            return

        station = str(self.editStation.text())
        password = str(self.editPassword.text())
        SETTINGS.writeEntry("/konnekte/station", station)
        SETTINGS.writeEntry("/konnekte/password", password)
        ev.accept()




app = qt.QApplication(sys.argv)

trans = qt.QTranslator(None)
qmfile = get_file("konnekte_%s.qm" % str(qt.QTextCodec.locale()[:2]))
trans.load(qmfile, len(qmfile))
app.installTranslator(trans)

mw = MainWindow()
app.setMainWidget(mw)
app.exec_loop()
