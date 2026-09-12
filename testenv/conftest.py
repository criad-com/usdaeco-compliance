"""Tests run from source; no installed package or setuptools is needed."""
import os
from pathlib import Path
import sys
from pxr import Plug
ROOT = Path(__file__).resolve().parents[1]
CORE = Path(os.environ.get('CORE_DIR', ROOT.parent/'usdaeco-core'))
CORE_PLUGIN = Path(os.environ.get('CORE_PLUGIN_DIR', CORE/'out/plugins/usdAeco/resources'))
sys.path.insert(0, str(ROOT/'tools'))
sys.path.insert(0, str(ROOT))
Plug.Registry().RegisterPlugins(str(CORE_PLUGIN))
Plug.Registry().RegisterPlugins(str(ROOT/'usdAecoCompliance'))
Plug.Registry().RegisterPlugins(str(ROOT/'usdAecoComplianceValidators'))
