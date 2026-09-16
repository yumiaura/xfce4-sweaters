#!/usr/bin/env python3
"""Run under dbus-run-session + Xvfb with GTK3, xfwm4 and python-xlib installed."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['GDK_BACKEND']='x11'
os.environ['GDK_SCALE']='1'
import gi
gi.require_version('Gtk','3.0')
gi.require_version('GdkX11','3.0')
from gi.repository import Gtk,GdkX11
from Xlib.ext import shape
from xfce4_sweaters.desktop import Controller
from xfce4_sweaters.x11 import Tracker


def pump(seconds=0.15):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        while Gtk.events_pending(): Gtk.main_iteration_do(False)
        time.sleep(0.005)


def eventually(condition,message,timeout=6):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        pump()
        if condition(): return
    raise AssertionError(message)

wm=subprocess.Popen(['xfwm4','--replace','--compositor=on'],env={**os.environ,'XFWM4_VBLANK':'off'},stdout=subprocess.DEVNULL)
controller=None
windows=[]
try:
    probe=Tracker()
    eventually(probe.composited,'xfwm4 compositor did not start')
    probe.close()
    for name,x in [('SweatersSmokeOne',100),('SweatersSmokeTwo',280)]:
        win=Gtk.Window(title=name)
        win.set_wmclass(name.lower(),name)
        win.set_default_size(400,260)
        win.move(x,150)
        win.show_all()
        windows.append(win)
    xids=[GdkX11.X11Window.get_xid(w.get_window()) for w in windows]
    with tempfile.TemporaryDirectory() as temp:
        controller=Controller(Path(temp)/'config.json')
        eventually(lambda: all(x in controller.overlays for x in xids),'normal windows have no overlays')
        first=controller.overlays[xids[0]]
        xid=GdkX11.X11Window.get_xid(first.get_window())
        xwindow=controller.tracker.display.create_resource_object('window',xid)
        assert len(xwindow.shape_get_rectangles(shape.SK.Input).rectangles)==0,'overlay intercepts pointer input'
        # Restacking must put each overlay above its own frame and below the next client.
        children=[w.id for w in controller.tracker.root.query_tree().children]
        ordered=[c for c in controller.clients if c.xid in xids]
        for client in ordered:
            overlay_id=GdkX11.X11Window.get_xid(controller.overlays[client.xid].get_window())
            assert children.index(overlay_id)>children.index(client.frame)
        lower,higher=ordered
        low_overlay=GdkX11.X11Window.get_xid(controller.overlays[lower.xid].get_window())
        assert children.index(low_overlay)<children.index(higher.frame),'lower border covers higher window'
        before=first.geometry_key
        windows[0].move(170,240)
        windows[0].resize(520,300)
        eventually(lambda: first.geometry_key!=before,'border did not follow move/resize')
        controller.overrides[xids[0]]={'texture':'off'}; controller.dirty=True
        eventually(lambda: xids[0] not in controller.overlays,'per-window off override ignored')
        controller.overrides.clear(); controller.dirty=True
        eventually(lambda: xids[0] in controller.overlays,'override reset failed')
        windows[0].iconify()
        eventually(lambda: xids[0] not in controller.overlays,'minimized window still decorated')
        windows[0].deiconify(); windows[0].present()
        eventually(lambda: xids[0] in controller.overlays,'restored window has no border')
        windows[0].fullscreen()
        eventually(lambda: xids[0] not in controller.overlays,'fullscreen window still decorated')
        windows[0].unfullscreen()
        eventually(lambda: xids[0] in controller.overlays,'leaving fullscreen lost border')
        controller.open_settings(); pump()
        assert controller.settings.get_visible(),'settings did not open'
        controller.settings.destroy()
        controller.apply({**controller.cfg,'enabled':False})
        eventually(lambda: not controller.overlays,'pause did not remove borders')
        controller.apply({**controller.cfg,'enabled':True})
        eventually(lambda: xids[0] in controller.overlays,'resume failed')
        windows[0].destroy()
        eventually(lambda: xids[0] not in controller.overlays,'destroyed window leaked border')
        print('PASS: input shape, stacking, movement, resize, overrides, minimize, fullscreen, settings, pause and cleanup')
finally:
    if controller:
        controller.stop(); controller.tracker.close()
    for win in windows:
        win.destroy()
    wm.terminate()
    try: wm.wait(timeout=5)
    except subprocess.TimeoutExpired: wm.kill(); wm.wait()
