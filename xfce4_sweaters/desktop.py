"""GTK3 click-through overlay lifecycle. Only this module needs GTK/X11."""
import io
import logging
import os
import time
import gi

gi.require_version('Gtk','3.0')
gi.require_version('Gdk','3.0')
gi.require_version('GdkX11','3.0')
gi.require_foreign('cairo')
from gi.repository import Gtk, Gdk, GdkPixbuf, GdkX11, GLib
import cairo
from . import config
from .textures import Registry, border
from .x11 import Tracker

log = logging.getLogger(__name__)

def pixbuf(image):
    data = io.BytesIO()
    image.save(data,format='PNG')
    loader = GdkPixbuf.PixbufLoader.new_with_type('png')
    loader.write(data.getvalue())
    loader.close()
    return loader.get_pixbuf()

class Overlay(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.set_title('XFCE4 Sweaters Border')
        self.set_decorated(False)
        self.set_accept_focus(False)
        self.set_focus_on_map(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_app_paintable(True)
        visual = self.get_screen().get_rgba_visual()
        if not visual:
            raise RuntimeError('No RGBA visual available')
        self.set_visual(visual)
        self.buffer = None
        self.render_key = None
        self.geometry_key = None
        self.connect('draw', self.draw)
        self.realize()
        self.get_window().input_shape_combine_region(cairo.Region(),0,0)

    def draw(self, widget, ctx):
        ctx.set_operator(cairo.OPERATOR_SOURCE)
        ctx.set_source_rgba(0,0,0,0)
        ctx.paint()
        if self.buffer:
            ctx.set_operator(cairo.OPERATOR_OVER)
            Gdk.cairo_set_source_pixbuf(ctx,self.buffer,0,0)
            ctx.paint()
        return True

    def update(self, client, style, registry, opacity):
        band = style['width']
        width,height = client.width+2*band,client.height+2*band
        key = (width,height,*style.values(),opacity)
        if key != self.render_key:
            self.buffer = pixbuf(border(registry,width,height,style,opacity))
            self.render_key = key
            self.queue_draw()
        geometry = (client.x-band,client.y-band,width,height)
        if geometry != self.geometry_key:
            self.move(geometry[0],geometry[1])
            self.resize(width,height)
            self.geometry_key = geometry
        if not self.get_visible():
            self.show()
        return GdkX11.X11Window.get_xid(self.get_window())

class Controller:
    def __init__(self, path):
        if not isinstance(Gdk.Display.get_default(),GdkX11.X11Display):
            raise RuntimeError('XFCE4 Sweaters requires an X11 session; Wayland is not supported')
        if Gdk.Screen.get_default().get_monitor_scale_factor(0) != 1:
            raise RuntimeError('Launch with GDK_SCALE=1 (border dimensions use physical pixels)')
        self.path = path
        self.registry = Registry(config.texture_dir())
        for warning in self.registry.errors:
            log.warning('%s',warning)
        self.cfg = config.load(path,self.registry.ids)
        self.tracker = Tracker()
        if not self.tracker.composited():
            raise RuntimeError('Enable Display compositing in XFCE Window Manager Tweaks → Compositor')
        self.overlays = {}
        self.overrides = {}
        self.clients = []
        self.settings = None
        self.dirty = True
        self.last_refresh = 0
        self.last_config_check = 0
        self.failed = False
        self.last_config_stamp = self.stamp()
        self.tray = Gtk.StatusIcon.new_from_icon_name('preferences-desktop-theme')
        self.tray.set_tooltip_text('XFCE4 Sweaters: click for settings')
        self.tray.connect('activate',lambda *_: self.open_settings())
        self.tray.connect('popup-menu',self.popup)
        self.tray.set_visible(True)
        self.timer = GLib.timeout_add(33,self.tick)

    def stamp(self):
        try:
            return self.path.stat().st_mtime_ns
        except FileNotFoundError:
            return None

    def tick(self):
        now = time.monotonic()
        changed = self.tracker.changed()
        if now-self.last_config_check >= 1:
            self.last_config_check = now
            stamp = self.stamp()
            if stamp != self.last_config_stamp:
                try:
                    self.cfg = config.load(self.path,self.registry.ids)
                    self.dirty = True
                except (ValueError,OSError) as exc:
                    log.error('Keeping last valid configuration: %s',exc)
                self.last_config_stamp = stamp
            changed = True
        if not (changed or self.dirty):
            return True
        self.last_refresh = now
        self.tracker.ignored = {GdkX11.X11Window.get_xid(o.get_window()) for o in self.overlays.values()}
        self.dirty = False
        try:
            self.clients = self.tracker.clients(self.cfg['hide_maximized'])
            # Session overrides survive minimize/workspace changes; expire only on close.
            open_ids = {int(x) for x in self.tracker.prop(self.tracker.root,'_NET_CLIENT_LIST')}
            self.overrides = {k:v for k,v in self.overrides.items() if k in open_ids}
            keep = set()
            if self.cfg['enabled']:
                for client in self.clients:
                    style = config.style_for(self.cfg,client.wm_class,client.title)
                    style.update(self.overrides.get(client.xid,{}))
                    style = self.registry.resolve(style,f'{client.wm_class}:{client.xid}',self.cfg['seed'])
                    if style['texture'] == 'off' or min(client.width,client.height) < 2:
                        continue
                    if max(client.width,client.height)+2*style['width'] > 16384:
                        continue
                    overlay = self.overlays.get(client.xid)
                    if overlay is None:
                        overlay = self.overlays[client.xid] = Overlay()
                    xid = overlay.update(client,style,self.registry,1.0 if client.active else self.cfg['inactive_opacity'])
                    keep.add(client.xid)
                    self.tracker.ignored.add(xid)
                    # Flush GTK's map/move requests before the separate Xlib connection restacks.
                    Gdk.Display.get_default().sync()
                    self.tracker.restack(xid,client.frame)
            for xid in set(self.overlays)-keep:
                overlay = self.overlays.pop(xid)
                # Keep destroyed XIDs ignored until the next real client refresh.
                overlay.destroy()
            self.tracker.display.flush()
        except Exception:
            self.failed = True
            log.exception('Unable to update window borders')
            self.stop()
            Gtk.main_quit()
            return False
        return True

    def apply(self, cfg):
        config.save(self.path,cfg,self.registry.ids)
        self.cfg = config.load(self.path,self.registry.ids)
        self.last_config_stamp = self.stamp()
        # Ensure imported/replaced images do not retain stale rendered borders.
        for overlay in self.overlays.values():
            overlay.render_key = None
        self.dirty = True

    def open_settings(self):
        from .settings import Settings
        if self.settings is None:
            self.settings = Settings(self)
            self.settings.connect('destroy',lambda *_: setattr(self,'settings',None))
        self.settings.show_all()
        self.settings.present()

    def popup(self, icon, button, timestamp):
        menu = Gtk.Menu()
        for label, callback in [('Settings',self.open_settings),('Shuffle',self.shuffle),
                                ('Pause / resume',self.toggle),('Quit',Gtk.main_quit)]:
            item = Gtk.MenuItem.new_with_label(label)
            item.connect('activate',lambda _,fn=callback:fn())
            menu.append(item)
        menu.show_all()
        menu.popup(None,None,None,None,button,timestamp)

    def shuffle(self):
        cfg = dict(self.cfg)
        cfg['seed'] = int.from_bytes(os.urandom(7),'big')
        self.apply(cfg)

    def toggle(self):
        self.apply({**self.cfg,'enabled':not self.cfg['enabled']})

    def stop(self):
        for overlay in self.overlays.values():
            overlay.destroy()
        self.overlays.clear()
        self.tray.set_visible(False)
