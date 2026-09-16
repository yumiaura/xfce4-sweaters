"""Read EWMH clients and restack unmanaged borders above their own frames."""
from dataclasses import dataclass
from Xlib import X, display, error

@dataclass(frozen=True)
class Client:
    xid: int
    frame: int
    wm_class: str
    title: str
    x: int
    y: int
    width: int
    height: int
    active: bool

class Tracker:
    def __init__(self):
        self.display = display.Display()
        self.root = self.display.screen().root
        self.atoms = {}
        self.watched = set()
        self.ignored = set()
        self.display.set_error_handler(lambda exc, request: None)
        if not self.display.has_extension('SHAPE'):
            raise RuntimeError('X11 SHAPE extension is required for click-through borders')
        self.root.change_attributes(event_mask=X.PropertyChangeMask | X.SubstructureNotifyMask)
        self.display.flush()

    def atom(self, name):
        if name not in self.atoms:
            self.atoms[name] = self.display.intern_atom(name)
        return self.atoms[name]

    def prop(self, window, name, default=()):
        p = window.get_full_property(self.atom(name), X.AnyPropertyType)
        return p.value if p is not None else default

    def number(self, window, name, default=0):
        p = self.prop(window,name)
        return int(p[0]) if len(p) else default

    def composited(self):
        owner = self.display.get_selection_owner(self.atom(f'_NET_WM_CM_S{self.display.get_default_screen()}'))
        return bool(owner)

    def changed(self):
        dirty = False
        while self.display.pending_events():
            event = self.display.next_event()
            target = getattr(event, 'window', None)
            if getattr(target, 'id', target) not in self.ignored:
                dirty = True
        return dirty

    def clients(self, hide_maximized=True):
        if not self.composited() or self.number(self.root,'_NET_SHOWING_DESKTOP'):
            return []
        desktop = self.number(self.root,'_NET_CURRENT_DESKTOP')
        active = self.number(self.root,'_NET_ACTIVE_WINDOW')
        excluded = {self.atom('_NET_WM_STATE_HIDDEN'), self.atom('_NET_WM_STATE_FULLSCREEN'), self.atom('_NET_WM_STATE_SHADED')}
        if hide_maximized:
            excluded.update({self.atom('_NET_WM_STATE_MAXIMIZED_HORZ'),self.atom('_NET_WM_STATE_MAXIMIZED_VERT')})
        allowed = {self.atom('_NET_WM_WINDOW_TYPE_NORMAL'),self.atom('_NET_WM_WINDOW_TYPE_DIALOG')}
        result, watched = [], set()
        for xid in self.prop(self.root,'_NET_CLIENT_LIST_STACKING'):
            try:
                win = self.display.create_resource_object('window',int(xid))
                if win.get_attributes().map_state != X.IsViewable:
                    continue
                if self.number(win,'_NET_WM_DESKTOP',desktop) not in (desktop,0xffffffff):
                    continue
                if excluded.intersection(self.prop(win,'_NET_WM_STATE')):
                    continue
                kinds = set(self.prop(win,'_NET_WM_WINDOW_TYPE'))
                if kinds and not kinds.intersection(allowed):
                    continue
                # Walk to the WM reparenting frame. Frame coordinates include titlebar.
                frame = win
                for _ in range(16):
                    parent = frame.query_tree().parent
                    if parent.id == self.root.id:
                        break
                    frame = parent
                else:
                    continue
                for target in (win,frame):
                    watched.add(target.id)
                    if target.id not in self.watched:
                        target.change_attributes(event_mask=X.PropertyChangeMask | X.StructureNotifyMask)
                geom = frame.get_geometry()
                pos = self.root.translate_coords(frame,0,0)
                wm_class = win.get_wm_class() or ('','')
                title = self.prop(win,'_NET_WM_NAME',b'')
                if isinstance(title,bytes):
                    title = title.decode('utf-8','replace')
                if not isinstance(title,str) or not title:
                    title = win.get_wm_name() or ''
                result.append(Client(int(xid),frame.id,wm_class[-1] or wm_class[0],str(title),
                                     pos.x,pos.y,geom.width,geom.height,int(xid)==active))
            except (error.XError, AttributeError, UnicodeError):
                # A client may disappear between any two X requests.
                continue
        self.watched = watched
        self.display.flush()
        return result

    def restack(self, overlay, frame):
        self.display.create_resource_object('window',overlay).configure(sibling=frame,stack_mode=X.Above)

    def close(self):
        self.display.close()
