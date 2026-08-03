from __future__ import annotations

from collections.abc import Callable

from .aalto import AaltoAdapter
from .aarhus import AarhusAdapter
from .adelaide import AdelaideAdapter
from .anu import ANUAdapter
from .auckland import AucklandAdapter
from .base import ProgrammeAdapter
from .basel import BaselAdapter
from .bath import BathAdapter
from .berkeley import BerkeleyAdapter
from .birmingham import BirminghamAdapter
from .boston import BostonAdapter
from .bristol import BristolAdapter
from .brown import BrownAdapter
from .caltech import CaltechAdapter
from .cambridge import CambridgeAdapter
from .cityu import CityUAdapter
from .columbia import ColumbiaAdapter
from .cornell import CornellAdapter
from .cuhk import CUHKAdapter
from .dtu import DTUAdapter
from .duke import DukeAdapter
from .edinburgh import EdinburghAdapter
from .epfl import EPFLAdapter
from .eth import ETHAdapter
from .exeter import ExeterAdapter
from .fu_berlin import FUBerlinAdapter
from .fudan import FudanAdapter
from .glasgow import GlasgowAdapter
from .groningen import GroningenAdapter
from .harvard import HarvardAdapter
from .heidelberg import HeidelbergAdapter
from .helsinki import HelsinkiAdapter
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
from .lancaster import LancasterAdapter
from .leeds import LeedsAdapter
from .leiden import LeidenAdapter
from .liverpool import LiverpoolAdapter
from .lmu import LMUAdapter
from .lse import LSEAdapter
from .lund import LundAdapter
from .manchester import ManchesterAdapter
from .mcgill import McGillAdapter
from .melbourne import MelbourneAdapter
from .mit import MITAdapter
from .monash import MonashAdapter
from .newcastle import NewcastleAdapter
from .northwestern import NorthwesternAdapter
from .nottingham import NottinghamAdapter
from .ntu import NTUAdapter
from .ntu_taiwan import NTUTaiwanAdapter
from .nus import NUSAdapter
from .oslo import OsloAdapter
from .oxford import OxfordAdapter
from .paris_saclay import ParisSaclayAdapter
from .peking import PekingAdapter
from .penn_state import PennStateAdapter
from .polimi import PolimiAdapter
from .polyu import PolyUAdapter
from .princeton import PrincetonAdapter
from .psl import PSLAdapter
from .rice import RiceAdapter
from .rmit import RMITAdapter
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
from .uzh import UZHAdapter
from .vienna import ViennaAdapter
from .wageningen import WageningenAdapter
from .warwick import WarwickAdapter
from .washington import WashingtonAdapter
from .waterloo import WaterlooAdapter
from .wisconsin import WisconsinAdapter
from .yale import YaleAdapter
from .yonsei import YonseiAdapter
from .york import YorkAdapter
from .zju import ZJUAdapter

AdapterFactory = Callable[[], ProgrammeAdapter]

PROGRAMME_ADAPTERS: dict[str, AdapterFactory] = {
    "adelaide": AdelaideAdapter,
    "aalto": AaltoAdapter,
    "aarhus": AarhusAdapter,
    "anu": ANUAdapter,
    "auckland": AucklandAdapter,
    "basel": BaselAdapter,
    "bath": BathAdapter,
    "berkeley": BerkeleyAdapter,
    "birmingham": BirminghamAdapter,
    "boston": BostonAdapter,
    "bristol": BristolAdapter,
    "brown": BrownAdapter,
    "caltech": CaltechAdapter,
    "cambridge": CambridgeAdapter,
    "columbia": ColumbiaAdapter,
    "cornell": CornellAdapter,
    "cuhk": CUHKAdapter,
    "cityu": CityUAdapter,
    "duke": DukeAdapter,
    "dtu": DTUAdapter,
    "edinburgh": EdinburghAdapter,
    "epfl": EPFLAdapter,
    "eth": ETHAdapter,
    "exeter": ExeterAdapter,
    "fudan": FudanAdapter,
    "fu-berlin": FUBerlinAdapter,
    "glasgow": GlasgowAdapter,
    "groningen": GroningenAdapter,
    "harvard": HarvardAdapter,
    "heidelberg": HeidelbergAdapter,
    "helsinki": HelsinkiAdapter,
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
    "lancaster": LancasterAdapter,
    "leeds": LeedsAdapter,
    "leiden": LeidenAdapter,
    "lmu": LMUAdapter,
    "lund": LundAdapter,
    "lse": LSEAdapter,
    "liverpool": LiverpoolAdapter,
    "mcgill": McGillAdapter,
    "melbourne": MelbourneAdapter,
    "manchester": ManchesterAdapter,
    "mit": MITAdapter,
    "monash": MonashAdapter,
    "nottingham": NottinghamAdapter,
    "newcastle": NewcastleAdapter,
    "northwestern": NorthwesternAdapter,
    "ntu": NTUAdapter,
    "ntu-taiwan": NTUTaiwanAdapter,
    "nus": NUSAdapter,
    "oxford": OxfordAdapter,
    "oslo": OsloAdapter,
    "peking": PekingAdapter,
    "paris-saclay": ParisSaclayAdapter,
    "penn-state": PennStateAdapter,
    "polimi": PolimiAdapter,
    "polyu": PolyUAdapter,
    "princeton": PrincetonAdapter,
    "psl": PSLAdapter,
    "rice": RiceAdapter,
    "rmit": RMITAdapter,
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
    "uzh": UZHAdapter,
    "uwa": UWAAdapter,
    "warwick": WarwickAdapter,
    "washington": WashingtonAdapter,
    "wageningen": WageningenAdapter,
    "waterloo": WaterlooAdapter,
    "wisconsin": WisconsinAdapter,
    "yale": YaleAdapter,
    "york": YorkAdapter,
    "yonsei": YonseiAdapter,
    "zju": ZJUAdapter,
    "vienna": ViennaAdapter,
}
