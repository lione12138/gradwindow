from __future__ import annotations

from collections.abc import Callable

from .aalto import AaltoAdapter
from .aarhus import AarhusAdapter
from .adelaide import AdelaideAdapter
from .anu import ANUAdapter
from .asu import ASUAdapter
from .auckland import AucklandAdapter
from .base import ProgrammeAdapter
from .basel import BaselAdapter
from .bath import BathAdapter
from .berkeley import BerkeleyAdapter
from .bern import BernAdapter
from .birmingham import BirminghamAdapter
from .bologna import BolognaAdapter
from .boston import BostonAdapter
from .bristol import BristolAdapter
from .brown import BrownAdapter
from .caltech import CaltechAdapter
from .cambridge import CambridgeAdapter
from .chalmers import ChalmersAdapter
from .cityu import CityUAdapter
from .columbia import ColumbiaAdapter
from .copenhagen import CopenhagenAdapter
from .cornell import CornellAdapter
from .cuhk import CUHKAdapter
from .dtu import DTUAdapter
from .duke import DukeAdapter
from .edinburgh import EdinburghAdapter
from .epfl import EPFLAdapter
from .erasmus import ErasmusAdapter
from .eth import ETHAdapter
from .exeter import ExeterAdapter
from .fu_berlin import FUBerlinAdapter
from .fudan import FudanAdapter
from .geneva import GenevaAdapter
from .georgia_tech import GeorgiaTechAdapter
from .ghent import GhentAdapter
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
from .kit import KITAdapter
from .korea import KoreaAdapter
from .kth import KTHAdapter
from .ku_leuven import KULeuvenAdapter
from .kyoto import KyotoAdapter
from .kyushu import KyushuAdapter
from .lancaster import LancasterAdapter
from .leeds import LeedsAdapter
from .leiden import LeidenAdapter
from .liverpool import LiverpoolAdapter
from .lmu import LMUAdapter
from .lse import LSEAdapter
from .lund import LundAdapter
from .manchester import ManchesterAdapter
from .mcgill import McGillAdapter
from .mcmaster import McMasterAdapter
from .melbourne import MelbourneAdapter
from .mit import MITAdapter
from .monash import MonashAdapter
from .nagoya import NagoyaAdapter
from .newcastle import NewcastleAdapter
from .northwestern import NorthwesternAdapter
from .nottingham import NottinghamAdapter
from .nthu import NTHUAdapter
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
from .purdue import PurdueAdapter
from .queens_ontario import QueensOntarioAdapter
from .rice import RiceAdapter
from .rmit import RMITAdapter
from .science_tokyo import ScienceTokyoAdapter
from .sheffield import SheffieldAdapter
from .sjtu import SJTUAdapter
from .snu import SNUAdapter
from .sorbonne import SorbonneAdapter
from .southampton import SouthamptonAdapter
from .st_andrews import StAndrewsAdapter
from .stanford import StanfordAdapter
from .stockholm import StockholmAdapter
from .sydney import SydneyAdapter
from .toronto import TorontoAdapter
from .tsinghua import TsinghuaAdapter
from .tu_berlin import TUBerlinAdapter
from .tu_wien import TUWienAdapter
from .tudelft import TUDelftAdapter
from .tum import TUMAdapter
from .ubc import UBCAdapter
from .ucd import UCDAdapter
from .uchicago import UChicagoAdapter
from .ucl import UCLAdapter
from .ucla import UCLAAdapter
from .ucsd import UCSDAdapter
from .uiuc import UIUCAdapter
from .um import UMAdapter
from .unsw import UNSWAdapter
from .upenn import UpennAdapter
from .uppsala import UppsalaAdapter
from .uq import UQAdapter
from .ut_austin import UTAustinAdapter
from .utokyo import UTokyoAdapter
from .uts import UTSAdapter
from .uva import UvAAdapter
from .uwa import UWAAdapter
from .uzh import UZHAdapter
from .vienna import ViennaAdapter
from .vu_amsterdam import VUAmsterdamAdapter
from .wageningen import WageningenAdapter
from .warwick import WarwickAdapter
from .washington import WashingtonAdapter
from .waterloo import WaterlooAdapter
from .western import WesternAdapter
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
    "asu": ASUAdapter,
    "basel": BaselAdapter,
    "bath": BathAdapter,
    "berkeley": BerkeleyAdapter,
    "bern": BernAdapter,
    "birmingham": BirminghamAdapter,
    "boston": BostonAdapter,
    "bologna": BolognaAdapter,
    "bristol": BristolAdapter,
    "brown": BrownAdapter,
    "caltech": CaltechAdapter,
    "cambridge": CambridgeAdapter,
    "chalmers": ChalmersAdapter,
    "columbia": ColumbiaAdapter,
    "copenhagen": CopenhagenAdapter,
    "cornell": CornellAdapter,
    "cuhk": CUHKAdapter,
    "cityu": CityUAdapter,
    "duke": DukeAdapter,
    "dtu": DTUAdapter,
    "edinburgh": EdinburghAdapter,
    "epfl": EPFLAdapter,
    "erasmus": ErasmusAdapter,
    "eth": ETHAdapter,
    "exeter": ExeterAdapter,
    "fudan": FudanAdapter,
    "fu-berlin": FUBerlinAdapter,
    "glasgow": GlasgowAdapter,
    "ghent": GhentAdapter,
    "georgia-tech": GeorgiaTechAdapter,
    "geneva": GenevaAdapter,
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
    "kit": KITAdapter,
    "kcl": KCLAdapter,
    "kfupm": KFUPMAdapter,
    "kth": KTHAdapter,
    "korea": KoreaAdapter,
    "ku-leuven": KULeuvenAdapter,
    "kyoto": KyotoAdapter,
    "kyushu": KyushuAdapter,
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
    "mcmaster": McMasterAdapter,
    "mit": MITAdapter,
    "monash": MonashAdapter,
    "nagoya": NagoyaAdapter,
    "nottingham": NottinghamAdapter,
    "newcastle": NewcastleAdapter,
    "northwestern": NorthwesternAdapter,
    "ntu": NTUAdapter,
    "ntu-taiwan": NTUTaiwanAdapter,
    "nthu": NTHUAdapter,
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
    "purdue": PurdueAdapter,
    "queens-ontario": QueensOntarioAdapter,
    "rice": RiceAdapter,
    "rmit": RMITAdapter,
    "science-tokyo": ScienceTokyoAdapter,
    "sjtu": SJTUAdapter,
    "sheffield": SheffieldAdapter,
    "snu": SNUAdapter,
    "southampton": SouthamptonAdapter,
    "st-andrews": StAndrewsAdapter,
    "sorbonne": SorbonneAdapter,
    "stanford": StanfordAdapter,
    "stockholm": StockholmAdapter,
    "sydney": SydneyAdapter,
    "toronto": TorontoAdapter,
    "tsinghua": TsinghuaAdapter,
    "tudelft": TUDelftAdapter,
    "tum": TUMAdapter,
    "tu-wien": TUWienAdapter,
    "tu-berlin": TUBerlinAdapter,
    "ubc": UBCAdapter,
    "uchicago": UChicagoAdapter,
    "ucl": UCLAdapter,
    "ucla": UCLAAdapter,
    "ucsd": UCSDAdapter,
    "ucd": UCDAdapter,
    "uiuc": UIUCAdapter,
    "unsw": UNSWAdapter,
    "uq": UQAdapter,
    "ut-austin": UTAustinAdapter,
    "um": UMAdapter,
    "upenn": UpennAdapter,
    "uppsala": UppsalaAdapter,
    "utokyo": UTokyoAdapter,
    "uts": UTSAdapter,
    "uva": UvAAdapter,
    "uzh": UZHAdapter,
    "uwa": UWAAdapter,
    "warwick": WarwickAdapter,
    "washington": WashingtonAdapter,
    "wageningen": WageningenAdapter,
    "waterloo": WaterlooAdapter,
    "western": WesternAdapter,
    "wisconsin": WisconsinAdapter,
    "yale": YaleAdapter,
    "york": YorkAdapter,
    "yonsei": YonseiAdapter,
    "zju": ZJUAdapter,
    "vienna": ViennaAdapter,
    "vu-amsterdam": VUAmsterdamAdapter,
}
