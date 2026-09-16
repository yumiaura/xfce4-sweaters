#!/usr/bin/env python3
"""Offline, per-user installer. Run with Ubuntu's /usr/bin/python3."""
import argparse
import importlib
import os
from pathlib import Path
import shlex
import shutil
import sys


def desktop_quote(path):
    # Desktop Entry string parsing followed by Exec argument parsing.
    text=str(path).replace('\\','\\\\\\\\').replace('"','\\\\"').replace('`','\\\\`').replace('$','\\\\$').replace('%','%%')
    return '"'+text+'"'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--autostart',action='store_true')
    args=parser.parse_args()
    missing=[]
    for module in ('gi','cairo','PIL','Xlib'):
        try: importlib.import_module(module)
        except ImportError: missing.append(module)
    if missing:
        print('Missing desktop dependencies: '+', '.join(missing),file=sys.stderr)
        print('sudo apt install python3-gi python3-gi-cairo python3-cairo python3-pil python3-xlib gir1.2-gtk-3.0',file=sys.stderr)
        print('Then run /usr/bin/python3 scripts/install.py',file=sys.stderr)
        return 1
    root=Path(__file__).resolve().parents[1]
    data=Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))
    configs=Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))
    app=data/'xfce4-sweaters/app'
    app.mkdir(parents=True,exist_ok=True)
    shutil.copytree(root/'xfce4_sweaters',app/'xfce4_sweaters',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copy2(root/'LICENSE',app/'LICENSE')
    launcher=Path.home()/'.local/bin/xfce4-sweaters'
    launcher.parent.mkdir(parents=True,exist_ok=True)
    bootstrap=app/'launch.py'
    bootstrap.write_text('from xfce4_sweaters.__main__ import main\nraise SystemExit(main())\n')
    launcher.write_text('#!/bin/sh\n# Installed by xfce4-sweaters\nexec '+shlex.quote(sys.executable)+' '+shlex.quote(str(bootstrap))+' "$@"\n')
    launcher.chmod(0o755)
    entry='[Desktop Entry]\nType=Application\nName=XFCE4 Sweaters\nComment=Knitted window borders\nExec='+desktop_quote(launcher)+' settings\nIcon=preferences-desktop-theme\nTerminal=false\nCategories=Settings;DesktopSettings;\n'
    applications=data/'applications'; applications.mkdir(parents=True,exist_ok=True)
    (applications/'xfce4-sweaters.desktop').write_text(entry)
    if args.autostart:
        autostart=configs/'autostart'; autostart.mkdir(parents=True,exist_ok=True)
        (autostart/'xfce4-sweaters.desktop').write_text(entry.replace(' settings\n',' run\n')+'OnlyShowIn=XFCE;\n')
    print(f'Installed. Open XFCE4 Sweaters in the application menu, or run {launcher} settings')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
