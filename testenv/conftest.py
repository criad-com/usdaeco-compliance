"""Tests run from source; no installed package or setuptools is needed."""
import os
from pathlib import Path
import sys
from pxr import Plug
ROOT = Path(__file__).resolve().parents[1]
CORE = Path(os.environ.get('CORE_DIR', ROOT.parent/'usdaeco-core'))
sys.path.insert(0, str(ROOT/'tools'))
sys.path.insert(0, str(ROOT))
Plug.Registry().RegisterPlugins(str(CORE/'out/plugins/usdAeco/resources'))
Plug.Registry().RegisterPlugins(str(ROOT/'usdAecoCompliance'))
Plug.Registry().RegisterPlugins(str(ROOT/'usdAecoComplianceValidators'))
