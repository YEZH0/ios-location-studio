"""Build from macos/: uv run python scripts/build.py (unsigned, local arch)."""
from pathlib import Path
import subprocess
import sys
root=Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--windowed',
    '--name','iOS Location Studio','--osx-bundle-identifier','xyz.yezhihong.locationstudio.mac',
    '--paths',str(root/'src'), '--collect-all','accessory_location',
    '--collect-data','location_studio_mac','--collect-all','pymobiledevice3','--hidden-import','location_studio_mac.worker',
    '--add-data',f'{root / "vendor/accessory-location"}:upstream',
    '--add-data',f'{root / "LICENSE"}:notices',
    '--add-data',f'{root / "THIRD_PARTY_NOTICES.md"}:notices',
    str(root/'scripts/launch.py')],cwd=root,check=True)
# Source accompanies local binary; release publishers must distribute both together.
subprocess.run(['git','archive','--format=zip','--output',str(root/'dist/macOS-source.zip'),
                'HEAD','macos','.github/workflows/macos.yml'],cwd=root.parent,check=True)
print('Unsigned app built. Source zip reflects HEAD: commit all intended source before distribution.')
