import argparse
import fcntl
import json
import logging
import os
from pathlib import Path
import signal
import sys
from . import __version__, config
from .textures import Registry


def main():
    parser=argparse.ArgumentParser(description='Knitted window borders for XFCE4/X11')
    parser.add_argument('--version',action='version',version=__version__)
    parser.add_argument('--config',type=Path,default=config.config_path())
    commands=parser.add_subparsers(dest='command')
    commands.add_parser('run',help='Run border daemon with tray icon')
    commands.add_parser('settings',help='Open settings (start daemon if needed)')
    commands.add_parser('list-textures',help='List built-in and user textures')
    commands.add_parser('check-config',help='Validate configuration without a display')
    preview=commands.add_parser('preview',help='Render a border without a display')
    preview.add_argument('output',type=Path)
    preview.add_argument('--texture',default='zigzag')
    preview.add_argument('--color',default='#648e7b')
    args=parser.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(levelname)s: %(message)s')
    registry=Registry(config.texture_dir())
    try:
        if args.command=='list-textures':
            print('\n'.join(registry.ids)); return 0
        if args.command=='check-config':
            print(json.dumps(config.load(args.config,registry.ids),indent=2)); return 0
        if args.command=='preview':
            from .textures import border
            style={'texture':args.texture,'color':args.color,'width':24,'stitch':5}
            config.validate_style(style,registry.ids)
            if style['texture']=='off':
                raise ValueError('Choose a texture to render')
            style=registry.resolve(style,'preview',0)
            border(registry,720,420,style).save(args.output)
            return 0
        if os.environ.get('XDG_SESSION_TYPE')=='wayland':
            raise ValueError('Wayland is unsupported. Log in to an XFCE X11 session.')
        if not os.environ.get('DISPLAY'):
            raise ValueError('No X11 display. Run this command inside your XFCE desktop session.')
        # A per-display lock permits independent VNC/X11 sessions for the same user.
        import hashlib
        suffix=hashlib.sha256(os.environ['DISPLAY'].encode()).hexdigest()[:16]
        runtime=Path(os.environ.get('XDG_RUNTIME_DIR',str(config.config_path().parent)))
        runtime.mkdir(parents=True,exist_ok=True)
        lock=open(runtime/f'xfce4-sweaters-{suffix}.lock','a+')
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            lock.seek(0)
            pid=int(lock.read().strip())
            if args.command=='settings':
                os.kill(pid,signal.SIGUSR1)
            else:
                print('XFCE4 Sweaters is already running.')
            return 0
        # Lock descriptor stays alive until the GTK loop exits.
        lock.seek(0); lock.truncate(); lock.write(str(os.getpid())); lock.flush()
        os.environ['GDK_BACKEND']='x11'
        os.environ['GDK_SCALE']='1'
        from .desktop import Controller, Gtk, GLib
        controller=Controller(args.config)
        def show_settings():
            controller.open_settings(); return True
        def quit_app():
            Gtk.main_quit(); return False
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT,signal.SIGUSR1,show_settings)
        for sig in (signal.SIGINT,signal.SIGTERM):
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT,sig,quit_app)
        if args.command in (None,'settings'):
            controller.open_settings()
        try:
            Gtk.main()
        finally:
            controller.stop(); controller.tracker.close(); lock.close()
        return 1 if controller.failed else 0
    except (ValueError,OSError,RuntimeError,ImportError) as exc:
        print(f'xfce4-sweaters: {exc}',file=sys.stderr)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
