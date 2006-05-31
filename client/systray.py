import qt
import ctypes as c

# Code by
# Torsten Marek <shlomme@gmx.net
# http://mats.gmd.de/pipermail/pykde/2004-May/007894.html

class SystrayIcon(qt.QLabel):
    """On construction, you have to supply a QPixmap instance holding the application icon.
    The pixmap should not be bigger than 32x32, preferably 22x22. Currently, no check is made.

    The class can emits two signals:
    Leftclick on icon: activated()
    Rightclick on icon: contextMenuRequested(const QPoint&)
    """
    def __init__(self, icon, parent = None, name = ""):
        qt.QLabel.__init__(self, parent, name, qt.Qt.WMouseNoMask | qt.Qt.WRepaintNoErase | qt.Qt.WType_TopLevel | qt.Qt.WStyle_Customize | qt.Qt.WStyle_NoBorder | qt.Qt.WStyle_StaysOnTop)
        self.setMinimumSize(22, 22);
        self.setBackgroundMode(qt.Qt.X11ParentRelative)
        #self.setBackgroundOrigin(qt.QWidget.WindowOrigin)

        libX11 = c.cdll.LoadLibrary("libX11.so.6")
        # get all functions, set arguments + return types
        XDefaultScreenOfDisplay = libX11.XDefaultScreenOfDisplay
        XDefaultScreenOfDisplay.argtypes = [c.c_void_p]
        XDefaultScreenOfDisplay.restype = c.c_void_p
        
        XScreenNumberOfScreen = libX11.XScreenNumberOfScreen
        XScreenNumberOfScreen.argtypes = [c.c_void_p]
        
        XInternAtom = libX11.XInternAtom
        XInternAtom.argtypes = [c.c_void_p, c.c_char_p, c.c_int]
        
        XGrabServer = libX11.XGrabServer
        XGrabServer.argtypes = [c.c_void_p]
        
        XGetSelectionOwner = libX11.XGetSelectionOwner
        XGetSelectionOwner.argtypes = [c.c_void_p, c.c_int]
        
        XSelectInput = libX11.XSelectInput
        XSelectInput.argtypes = [c.c_void_p, c.c_int, c.c_long]
        
        
        XUngrabServer = libX11.XUngrabServer
        XUngrabServer.argtypes = [c.c_void_p]
        
        XFlush = libX11.XFlush
        XFlush.argtypes = [c.c_void_p]
        
        class data(c.Union):
            _fields_ = [("b", c.c_char * 20),
                        ("s", c.c_short * 10),
                        ("l", c.c_long * 5)]
        class XClientMessageEvent(c.Structure):
            _fields_ = [("type", c.c_int),
                        ("serial", c.c_ulong),
                        ("send_event", c.c_int),
                        ("display", c.c_void_p),
                        ("window", c.c_int),
                        ("message_type", c.c_int),
                        ("format", c.c_int),
                        ("data", data)]

        XSendEvent = libX11.XSendEvent
        XSendEvent.argtypes = [c.c_void_p, c.c_int, c.c_int, c.c_long, c.c_void_p]
                               
        XSync = libX11.XSync
        XSync.argtypes = [c.c_void_p, c.c_int]

        dpy = c.c_void_p(int(qt.qt_xdisplay()))

        iscreen = XScreenNumberOfScreen(c.c_void_p(XDefaultScreenOfDisplay(dpy)))
        # get systray window (holds _NET_SYSTEM_TRAY_S<screen> atom)
        selectionAtom = XInternAtom(dpy, "_NET_SYSTEM_TRAY_S%i" % iscreen, 0)
        XGrabServer(dpy)
        managerWin = XGetSelectionOwner(dpy, selectionAtom)
        if managerWin != 0:
            # set StructureNotifyMask (1L << 17)
            XSelectInput(dpy, managerWin, 1L << 17)
        XUngrabServer(dpy);
        XFlush(dpy);
        if managerWin != 0:
            # send "SYSTEM_TRAY_OPCODE_REQUEST_DOCK to managerWin
            k = data()
            k.l = (0, # CurrentTime
                   0, # REQUEST_DOCK
                   self.winId(), # window ID
                   0, # empty
                   0) # empty
            ev = XClientMessageEvent(33, #type: ClientMessage
                                     0, # serial
                                     0, # send_event
                                     dpy, # display
                                     managerWin, # systray manager
                                     XInternAtom(dpy, "_NET_SYSTEM_TRAY_OPCODE", 0), # message type
                                     32, # format
                                     k) # message data
            XSendEvent(dpy, managerWin, 0, 0, c.c_void_p(c.addressof(ev)))
            XSync(dpy, 0)
        
        self.show()
        self.setPixmap(icon)
        self.setAlignment(qt.Qt.AlignHCenter)

        if parent:
            qt.QToolTip.add(self, parent.caption())


    def setTooltipText(self, text):
        qt.QToolTip.add(self, text)

        
    def mousePressEvent(self, e):
        if e.button() == qt.Qt.RightButton:
            self.emit(qt.PYSIGNAL("contextMenuRequested(const QPoint&)"), (e.globalPos(),))
        elif e.button() == qt.Qt.LeftButton:
            self.emit(qt.PYSIGNAL("activated()"), ())
            
