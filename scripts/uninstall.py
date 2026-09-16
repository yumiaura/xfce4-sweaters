#!/usr/bin/env python3
"""Remove installed program files; preserve settings and imported textures."""
import os
from pathlib import Path
import shutil

data=Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))
configs=Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))
for path in [Path.home()/'.local/bin/xfce4-sweaters',data/'applications/xfce4-sweaters.desktop',configs/'autostart/xfce4-sweaters.desktop']:
    path.unlink(missing_ok=True)
app=data/'xfce4-sweaters/app'
if app.exists():
    shutil.rmtree(app)
print('Program removed. Saved settings and custom textures were kept. Quit any running instance from its tray menu.')
