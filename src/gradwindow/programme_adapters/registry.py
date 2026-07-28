from __future__ import annotations

from collections.abc import Callable

from .adelaide import AdelaideAdapter
from .anu import ANUAdapter
from .auckland import AucklandAdapter
from .base import ProgrammeAdapter
from .berkeley import BerkeleyAdapter
from .birmingham import BirminghamAdapter
from .bristol import BristolAdapter
from .brown import BrownAdapter
from .caltech import CaltechAdapter
from .cambridge import CambridgeAdapter
from .cityu import CityUAdapter
from .columbia import ColumbiaAdapter
from .cornell import CornellAdapter
from .cuhk import CUHKAdapter
from .duke import DukeAdapter
from .edinburgh import EdinburghAdapter
from .epfl import EPFLAdapter
from .eth import ETHAdapter
from .fudan import FudanAdapter
from .glasgow import GlasgowAdapter
from .harvard import HarvardAdapter
from .heidelberg import HeidelbergAdapter
from .hku import HKUAdapter
from .hkust import HKUSTAdapter
from .imperial import ImperialAdapter
from .ip_paris import IPParisAdapter
from .jhu import JHUAdapter
from .kaist import KAISTAdapter
from .kcl import KCLAdapter
from .kfupm import KFUPMAdapter
from .korea import KoreaAdapter
from .kth import KTHAdapter
from .ku_leuven import KULeuvenAdapter
from .kyoto import KyotoAdapter
from .leeds import LeedsAdapter
from .lmu import LMUAdapter
from .lund import LundAdapter
from .manchester import ManchesterAdapter
from .mcgill import McGillAdapter
from .melbourne import MelbourneAdapter
from .mit import MITAdapter
from .monash import MonashAdapter
from .northwestern import NorthwesternAdapter
from .nottingham import NottinghamAdapter
from .ntu import NTUAdapter
from .ntu_taiwan import NTUTaiwanAdapter
from .nus import NUSAdapter
from .oxford import OxfordAdapter
from .paris_saclay import ParisSaclayAdapter
from .peking import PekingAdapter
from .penn_state import PennStateAdapter
from .polimi import PolimiAdapter
from .polyu import PolyUAdapter
from .princeton import PrincetonAdapter
from .psl import PSLAdapter
from .sheffield import SheffieldAdapter
from .sjtu import SJTUAdapter
from .snu import SNUAdapter
from .sorbonne import SorbonneAdapter
from .southampton import SouthamptonAdapter
from .stanford import StanfordAdapter
from .sydney import SydneyAdapter
from .toronto import TorontoAdapter
from .tsinghua import TsinghuaAdapter
from .tudelft import TUDelftAdapter
from .tum import TUMAdapter
from .ubc import UBCAdapter
from .uchicago import UChicagoAdapter
from .ucl import UCLAdapter
from .ucla import UCLAAdapter
from .ucsd import UCSDAdapter
from .uiuc import UIUCAdapter
from .um import UMAdapter
from .unsw import UNSWAdapter
from .upenn import UpennAdapter
from .uq import UQAdapter
from .ut_austin import UTAustinAdapter
from .utokyo import UTokyoAdapter
from .uts import UTSAdapter
from .uva import UvAAdapter
from .uwa import UWAAdapter
from .warwick import WarwickAdapter
from .yale import YaleAdapter
from .yonsei import YonseiAdapter
from .zju import ZJUAdapter

AdapterFactory = Callable[[], ProgrammeAdapter]

PROGRAMME_ADAPTERS: dict[str, AdapterFactory] = {
    "adelaide": AdelaideAdapter,
    "anu": ANUAdapter,
    "auckland": AucklandAdapter,
    "berkeley": BerkeleyAdapter,
    "birmingham": BirminghamAdapter,
    "bristol": BristolAdapter,
    "brown": BrownAdapter,
    "caltech": CaltechAdapter,
    "cambridge": CambridgeAdapter,
    "columbia": ColumbiaAdapter,
    "cornell": CornellAdapter,
    "cuhk": CUHKAdapter,
    "cityu": CityUAdapter,
    "duke": DukeAdapter,
    "edinburgh": EdinburghAdapter,
    "epfl": EPFLAdapter,
    "eth": ETHAdapter,
    "fudan": FudanAdapter,
    "glasgow": GlasgowAdapter,
    "harvard": HarvardAdapter,
    "heidelberg": HeidelbergAdapter,
    "hku": HKUAdapter,
    "hkust": HKUSTAdapter,
    "imperial": ImperialAdapter,
    "ip-paris": IPParisAdapter,
    "jhu": JHUAdapter,
    "kaist": KAISTAdapter,
    "kcl": KCLAdapter,
    "kfupm": KFUPMAdapter,
    "kth": KTHAdapter,
    "korea": KoreaAdapter,
    "ku-leuven": KULeuvenAdapter,
    "kyoto": KyotoAdapter,
    "leeds": LeedsAdapter,
    "lmu": LMUAdapter,
    "lund": LundAdapter,
    "mcgill": McGillAdapter,
    "melbourne": MelbourneAdapter,
    "manchester": ManchesterAdapter,
    "mit": MITAdapter,
    "monash": MonashAdapter,
    "nottingham": NottinghamAdapter,
    "northwestern": NorthwesternAdapter,
    "ntu": NTUAdapter,
    "ntu-taiwan": NTUTaiwanAdapter,
    "nus": NUSAdapter,
    "oxford": OxfordAdapter,
    "peking": PekingAdapter,
    "paris-saclay": ParisSaclayAdapter,
    "penn-state": PennStateAdapter,
    "polimi": PolimiAdapter,
    "polyu": PolyUAdapter,
    "princeton": PrincetonAdapter,
    "psl": PSLAdapter,
    "sjtu": SJTUAdapter,
    "sheffield": SheffieldAdapter,
    "snu": SNUAdapter,
    "southampton": SouthamptonAdapter,
    "sorbonne": SorbonneAdapter,
    "stanford": StanfordAdapter,
    "sydney": SydneyAdapter,
    "toronto": TorontoAdapter,
    "tsinghua": TsinghuaAdapter,
    "tudelft": TUDelftAdapter,
    "tum": TUMAdapter,
    "ubc": UBCAdapter,
    "uchicago": UChicagoAdapter,
    "ucl": UCLAdapter,
    "ucla": UCLAAdapter,
    "ucsd": UCSDAdapter,
    "uiuc": UIUCAdapter,
    "unsw": UNSWAdapter,
    "uq": UQAdapter,
    "ut-austin": UTAustinAdapter,
    "um": UMAdapter,
    "upenn": UpennAdapter,
    "utokyo": UTokyoAdapter,
    "uts": UTSAdapter,
    "uva": UvAAdapter,
    "uwa": UWAAdapter,
    "warwick": WarwickAdapter,
    "yale": YaleAdapter,
    "yonsei": YonseiAdapter,
    "zju": ZJUAdapter,
}
