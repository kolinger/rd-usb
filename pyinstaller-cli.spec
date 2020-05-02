# -*- mode: python -*-

from runpy import run_path
version_script = os.path.realpath(workpath + "/../../utils/version.py")
run_path(version_script, run_name="write")

from PyInstaller.utils.hooks import collect_dynamic_libs

block_cipher = None

a = Analysis(['web.py'],
             binaries=collect_dynamic_libs('bleak'),
             datas=[
                ('webapp/templates', 'webapp/templates'),
                ('static', 'static'),
             ],
             hiddenimports=['engineio.async_drivers.threading'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='rd-usb',
          icon='static/img/icon.ico',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          runtime_tmpdir=None,
          console=True )

run_path(version_script, run_name="clean")
