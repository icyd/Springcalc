# -*- mode: python -*-

block_cipher = None

resource_files = [
    ('wires.db', '.'),
    ('spring.ico', '.')
    ]

a = Analysis(['springcalc.py'],
             pathex=['C:\\Users\\beto.AD.000\\Desktop\\SpringCalc'],
             binaries=None,
             datas=resource_files,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='springcalc',
          debug=False,
          strip=False,
          upx=True,
          console=False , icon='spring.ico')
