"""Exercise installation paths and launchers without changing the real user profile."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('sweaters_installer',ROOT/'scripts/install.py')
installer=importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

class InstallTests(unittest.TestCase):
    def test_install_launch_and_remove_preserves_user_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            home=Path(temp)/'user with spaces and $cash'
            data=home/'share'; configs=home/'config'
            env={'XDG_DATA_HOME':str(data),'XDG_CONFIG_HOME':str(configs)}
            # Only dependency detection is mocked; file copying and the launcher are real.
            with patch.object(Path,'home',return_value=home),patch.dict(os.environ,env),patch.object(sys,'argv',['install.py','--autostart']),patch.object(installer.importlib,'import_module'),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(installer.main(),0)
            launcher=home/'.local/bin/xfce4-sweaters'
            result=subprocess.run([str(launcher),'--version'],capture_output=True,text=True,env={**os.environ,**env},check=True)
            self.assertEqual(result.stdout.strip(),'0.0.0')
            desktop=(data/'applications/xfce4-sweaters.desktop').read_text()
            self.assertIn(' settings\n',desktop)
            self.assertIn(' run\n',(configs/'autostart/xfce4-sweaters.desktop').read_text())
            textures=data/'xfce4-sweaters/textures'; textures.mkdir()
            custom=textures/'custom.png'; custom.write_bytes(b'preserve user data')
            cfg=configs/'xfce4-sweaters/config.json'; cfg.parent.mkdir(); cfg.write_text('{}')
            with patch.object(Path,'home',return_value=home),patch.dict(os.environ,env),contextlib.redirect_stdout(io.StringIO()):
                runpy.run_path(str(ROOT/'scripts/uninstall.py'),run_name='__main__')
            self.assertFalse(launcher.exists())
            self.assertFalse((data/'xfce4-sweaters/app').exists())
            self.assertTrue(custom.exists())
            self.assertTrue(cfg.exists())

    def test_missing_dependencies_do_not_install_partial_files(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(Path,'home',return_value=Path(temp)),patch.object(sys,'argv',['install.py']),patch.object(installer.importlib,'import_module',side_effect=ImportError),contextlib.redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(installer.main(),1)
            self.assertEqual(list(Path(temp).iterdir()),[])
            self.assertIn('Missing desktop dependencies',errors.getvalue())

if __name__=='__main__': unittest.main()
