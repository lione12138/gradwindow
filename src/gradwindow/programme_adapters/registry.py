from __future__ import annotations

from collections.abc import Callable

from .aalto import AaltoAdapter
from .aarhus import AarhusAdapter
from .adelaide import AdelaideAdapter
from .alberta import AlbertaAdapter
from .antwerp import AntwerpAdapter
from .anu import ANUAdapter
from .asu import ASUAdapter
from .auckland import AucklandAdapter
from .barcelona import BarcelonaAdapter
from .base import ProgrammeAdapter
from .basel import BaselAdapter
from .bath import BathAdapter
from .baylor import BaylorAdapter
from .berkeley import BerkeleyAdapter
from .bern import BernAdapter
from .birmingham import BirminghamAdapter
from .bologna import BolognaAdapter
from .bonn import BonnAdapter
from .boston import BostonAdapter
from .bristol import BristolAdapter
from .brown import BrownAdapter
from .calgary import CalgaryAdapter
from .caltech import CaltechAdapter
from .cambridge import CambridgeAdapter
from .cape_town import CapeTownAdapter
from .cardiff import CardiffAdapter
from .case_western import CaseWesternAdapter
from .chalmers import ChalmersAdapter
from .charite import ChariteAdapter
from .cityu import CityUAdapter
from .cmu import CMUAdapter
from .cologne import CologneAdapter
from .colorado_boulder import ColoradoBoulderAdapter
from .columbia import ColumbiaAdapter
from .complutense import ComplutenseAdapter
from .copenhagen import CopenhagenAdapter
from .cornell import CornellAdapter
from .cu_anschutz import CUAnschutzAdapter
from .cuhk import CUHKAdapter
from .curtin import CurtinAdapter
from .dartmouth import DartmouthAdapter
from .deakin import DeakinAdapter
from .dtu import DTUAdapter
from .duke import DukeAdapter
from .durham import DurhamAdapter
from .edinburgh import EdinburghAdapter
from .emory import EmoryAdapter
from .epfl import EPFLAdapter
from .erasmus import ErasmusAdapter
from .eth import ETHAdapter
from .exeter import ExeterAdapter
from .farabi import FarabiAdapter
from .florida import FloridaAdapter
from .freiburg import FreiburgAdapter
from .fu_berlin import FUBerlinAdapter
from .fudan import FudanAdapter
from .geneva import GenevaAdapter
from .georgia_tech import GeorgiaTechAdapter
from .ghent import GhentAdapter
from .glasgow import GlasgowAdapter
from .gothenburg import GothenburgAdapter
from .gottingen import GottingenAdapter
from .groningen import GroningenAdapter
from .hamburg import HamburgAdapter
from .hanyang import HanyangAdapter
from .harvard import HarvardAdapter
from .hebrew import HebrewAdapter
from .heidelberg import HeidelbergAdapter
from .helsinki import HelsinkiAdapter
from .hit import HITAdapter
from .hku import HKUAdapter
from .hkust import HKUSTAdapter
from .hokkaido import HokkaidoAdapter
from .humboldt import HumboldtAdapter
from .hust import HUSTAdapter
from .icahn import IcahnAdapter
from .iit_bombay import IITBombayAdapter
from .iit_delhi import IITDelhiAdapter
from .iit_madras import IITMadrasAdapter
from .imperial import ImperialAdapter
from .ip_paris import IPParisAdapter
from .jhu import JHUAdapter
from .kaist import KAISTAdapter
from .karolinska import KarolinskaAdapter
from .kau import KAUAdapter
from .kaust import KAUSTAdapter
from .kcl import KCLAdapter
from .kfupm import KFUPMAdapter
from .khalifa import KhalifaAdapter
from .kit import KITAdapter
from .korea import KoreaAdapter
from .ksu import KSUAdapter
from .kth import KTHAdapter
from .ku_leuven import KULeuvenAdapter
from .kyoto import KyotoAdapter
from .kyushu import KyushuAdapter
from .lancaster import LancasterAdapter
from .lausanne import LausanneAdapter
from .leeds import LeedsAdapter
from .leicester import LeicesterAdapter
from .leiden import LeidenAdapter
from .liverpool import LiverpoolAdapter
from .lmu import LMUAdapter
from .lse import LSEAdapter
from .lund import LundAdapter
from .maastricht import MaastrichtAdapter
from .macau import MacauAdapter
from .macquarie import MacquarieAdapter
from .manchester import ManchesterAdapter
from .mcgill import McGillAdapter
from .mcmaster import McMasterAdapter
from .md_anderson import MDAndersonAdapter
from .meduni_vienna import MedUniViennaAdapter
from .melbourne import MelbourneAdapter
from .michigan import MichiganAdapter
from .michigan_state import MichiganStateAdapter
from .minnesota import MinnesotaAdapter
from .mit import MITAdapter
from .monash import MonashAdapter
from .montreal import MontrealAdapter
from .msu import MSUAdapter
from .munster import MunsterAdapter
from .nagoya import NagoyaAdapter
from .nanjing import NanjingAdapter
from .ncku import NCKUAdapter
from .newcastle import NewcastleAdapter
from .northwestern import NorthwesternAdapter
from .notre_dame import NotreDameAdapter
from .nottingham import NottinghamAdapter
from .nthu import NTHUAdapter
from .ntnu import NTNUAdapter
from .ntu import NTUAdapter
from .ntu_taiwan import NTUTaiwanAdapter
from .nus import NUSAdapter
from .nycu import NYCUAdapter
from .nyu import NYUAdapter
from .ohio_state import OhioStateAdapter
from .osaka import OsakaAdapter
from .oslo import OsloAdapter
from .otago import OtagoAdapter
from .ottawa import OttawaAdapter
from .oxford import OxfordAdapter
from .paris_cite import ParisCiteAdapter
from .paris_saclay import ParisSaclayAdapter
from .peking import PekingAdapter
from .penn_state import PennStateAdapter
from .pittsburgh import PittsburghAdapter
from .polimi import PolimiAdapter
from .polyu import PolyUAdapter
from .postech import POSTECHAdapter
from .princeton import PrincetonAdapter
from .psl import PSLAdapter
from .puc_chile import PUCChileAdapter
from .purdue import PurdueAdapter
from .qatar import QatarAdapter
from .qmul import QMULAdapter
from .qub import QUBAdapter
from .queens_ontario import QueensOntarioAdapter
from .radboud import RadboudAdapter
from .reading import ReadingAdapter
from .rice import RiceAdapter
from .rmit import RMITAdapter
from .rochester import RochesterAdapter
from .rockefeller import RockefellerAdapter
from .rwth import RWTHAdapter
from .sapienza import SapienzaAdapter
from .science_tokyo import ScienceTokyoAdapter
from .sheffield import SheffieldAdapter
from .shenzhen import ShenzhenAdapter
from .sichuan import SichuanAdapter
from .sjtu import SJTUAdapter
from .skku import SKKUAdapter
from .snu import SNUAdapter
from .sorbonne import SorbonneAdapter
from .southampton import SouthamptonAdapter
from .st_andrews import StAndrewsAdapter
from .stanford import StanfordAdapter
from .stockholm import StockholmAdapter
from .strasbourg import StrasbourgAdapter
from .sun_yat_sen import SunYatSenAdapter
from .sustech import SUSTechAdapter
from .swinburne import SwinburneAdapter
from .sydney import SydneyAdapter
from .tamu import TAMUAdapter
from .tec_monterrey import TecMonterreyAdapter
from .tel_aviv import TelAvivAdapter
from .tohoku import TohokuAdapter
from .tongji import TongjiAdapter
from .toronto import TorontoAdapter
from .trinity import TrinityAdapter
from .tsinghua import TsinghuaAdapter
from .tu_berlin import TUBerlinAdapter
from .tu_dresden import TUDresdenAdapter
from .tu_wien import TUWienAdapter
from .tubingen import TubingenAdapter
from .tudelft import TUDelftAdapter
from .tue import TUEAdapter
from .tufts import TuftsAdapter
from .tum import TUMAdapter
from .twente import TwenteAdapter
from .uab import UABAdapter
from .uba import UBAAdapter
from .ubc import UBCAdapter
from .uc_davis import UCDavisAdapter
from .ucas import UCASAdapter
from .ucd import UCDAdapter
from .uchicago import UChicagoAdapter
from .uchile import UChileAdapter
from .uci import UCIAdapter
from .ucl import UCLAdapter
from .ucla import UCLAAdapter
from .uclouvain import UCLouvainAdapter
from .ucsb import UCSBAdapter
from .ucsc import UCSCAdapter
from .ucsd import UCSDAdapter
from .ucsf import UCSFAdapter
from .uiuc import UIUCAdapter
from .ukm import UKMAdapter
from .um import UMAdapter
from .umd import UMDAdapter
from .unam import UNAMAdapter
from .unc import UNCAdapter
from .universitas_indonesia import UniversitasIndonesiaAdapter
from .unsw import UNSWAdapter
from .uow import UOWAdapter
from .upenn import UpennAdapter
from .upm import UPMAdapter
from .uppsala import UppsalaAdapter
from .uq import UQAdapter
from .usc import USCAdapter
from .usm import USMAdapter
from .usp import USPAdapter
from .ustc import USTCAdapter
from .ut_austin import UTAustinAdapter
from .utah import UtahAdapter
from .utm import UTMAdapter
from .utokyo import UTokyoAdapter
from .utrecht import UtrechtAdapter
from .uts import UTSAdapter
from .utsw import UTSWAdapter
from .uva import UvAAdapter
from .uwa import UWAAdapter
from .uzh import UZHAdapter
from .vanderbilt import VanderbiltAdapter
from .vienna import ViennaAdapter
from .vu_amsterdam import VUAmsterdamAdapter
from .wageningen import WageningenAdapter
from .warwick import WarwickAdapter
from .washington import WashingtonAdapter
from .washu import WashUAdapter
from .waterloo import WaterlooAdapter
from .weizmann import WeizmannAdapter
from .western import WesternAdapter
from .wisconsin import WisconsinAdapter
from .wuhan import WuhanAdapter
from .wurzburg import WurzburgAdapter
from .xjtu import XJTUAdapter
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
    "antwerp": AntwerpAdapter,
    "auckland": AucklandAdapter,
    "asu": ASUAdapter,
    "basel": BaselAdapter,
    "bath": BathAdapter,
    "baylor-medicine": BaylorAdapter,
    "cape-town": CapeTownAdapter,
    "cardiff": CardiffAdapter,
    "berkeley": BerkeleyAdapter,
    "bern": BernAdapter,
    "birmingham": BirminghamAdapter,
    "boston": BostonAdapter,
    "barcelona": BarcelonaAdapter,
    "bologna": BolognaAdapter,
    "bonn": BonnAdapter,
    "bristol": BristolAdapter,
    "brown": BrownAdapter,
    "caltech": CaltechAdapter,
    "calgary": CalgaryAdapter,
    "cambridge": CambridgeAdapter,
    "case-western": CaseWesternAdapter,
    "charite": ChariteAdapter,
    "chalmers": ChalmersAdapter,
    "cologne": CologneAdapter,
    "columbia": ColumbiaAdapter,
    "complutense": ComplutenseAdapter,
    "colorado-boulder": ColoradoBoulderAdapter,
    "copenhagen": CopenhagenAdapter,
    "cornell": CornellAdapter,
    "cu-anschutz": CUAnschutzAdapter,
    "cuhk": CUHKAdapter,
    "curtin": CurtinAdapter,
    "dartmouth": DartmouthAdapter,
    "deakin": DeakinAdapter,
    "cityu": CityUAdapter,
    "cmu": CMUAdapter,
    "duke": DukeAdapter,
    "dtu": DTUAdapter,
    "durham": DurhamAdapter,
    "edinburgh": EdinburghAdapter,
    "emory": EmoryAdapter,
    "epfl": EPFLAdapter,
    "erasmus": ErasmusAdapter,
    "eth": ETHAdapter,
    "exeter": ExeterAdapter,
    "farabi": FarabiAdapter,
    "fudan": FudanAdapter,
    "florida": FloridaAdapter,
    "freiburg": FreiburgAdapter,
    "fu-berlin": FUBerlinAdapter,
    "glasgow": GlasgowAdapter,
    "gottingen": GottingenAdapter,
    "gothenburg": GothenburgAdapter,
    "ghent": GhentAdapter,
    "georgia-tech": GeorgiaTechAdapter,
    "geneva": GenevaAdapter,
    "groningen": GroningenAdapter,
    "harvard": HarvardAdapter,
    "hebrew": HebrewAdapter,
    "hamburg": HamburgAdapter,
    "hanyang": HanyangAdapter,
    "heidelberg": HeidelbergAdapter,
    "helsinki": HelsinkiAdapter,
    "hit": HITAdapter,
    "hust": HUSTAdapter,
    "hokkaido": HokkaidoAdapter,
    "humboldt": HumboldtAdapter,
    "icahn": IcahnAdapter,
    "iit-bombay": IITBombayAdapter,
    "iit-delhi": IITDelhiAdapter,
    "iit-madras": IITMadrasAdapter,
    "hku": HKUAdapter,
    "hkust": HKUSTAdapter,
    "imperial": ImperialAdapter,
    "ip-paris": IPParisAdapter,
    "jhu": JHUAdapter,
    "kaist": KAISTAdapter,
    "kaust": KAUSTAdapter,
    "karolinska": KarolinskaAdapter,
    "kau": KAUAdapter,
    "khalifa": KhalifaAdapter,
    "kit": KITAdapter,
    "kcl": KCLAdapter,
    "kfupm": KFUPMAdapter,
    "kth": KTHAdapter,
    "korea": KoreaAdapter,
    "ku-leuven": KULeuvenAdapter,
    "kyoto": KyotoAdapter,
    "kyushu": KyushuAdapter,
    "lancaster": LancasterAdapter,
    "lausanne": LausanneAdapter,
    "leeds": LeedsAdapter,
    "leiden": LeidenAdapter,
    "leicester": LeicesterAdapter,
    "lmu": LMUAdapter,
    "msu": MSUAdapter,
    "lund": LundAdapter,
    "lse": LSEAdapter,
    "liverpool": LiverpoolAdapter,
    "mcgill": McGillAdapter,
    "melbourne": MelbourneAdapter,
    "manchester": ManchesterAdapter,
    "macquarie": MacquarieAdapter,
    "maastricht": MaastrichtAdapter,
    "macau": MacauAdapter,
    "meduni-vienna": MedUniViennaAdapter,
    "mcmaster": McMasterAdapter,
    "md-anderson": MDAndersonAdapter,
    "michigan": MichiganAdapter,
    "michigan-state": MichiganStateAdapter,
    "minnesota": MinnesotaAdapter,
    "mit": MITAdapter,
    "montreal": MontrealAdapter,
    "munster": MunsterAdapter,
    "monash": MonashAdapter,
    "nagoya": NagoyaAdapter,
    "nanjing": NanjingAdapter,
    "ncku": NCKUAdapter,
    "nottingham": NottinghamAdapter,
    "notre-dame": NotreDameAdapter,
    "newcastle": NewcastleAdapter,
    "northwestern": NorthwesternAdapter,
    "ntu": NTUAdapter,
    "ntu-taiwan": NTUTaiwanAdapter,
    "nthu": NTHUAdapter,
    "ntnu": NTNUAdapter,
    "nus": NUSAdapter,
    "nyu": NYUAdapter,
    "nycu": NYCUAdapter,
    "ohio-state": OhioStateAdapter,
    "oxford": OxfordAdapter,
    "oslo": OsloAdapter,
    "osaka": OsakaAdapter,
    "otago": OtagoAdapter,
    "ottawa": OttawaAdapter,
    "peking": PekingAdapter,
    "paris-saclay": ParisSaclayAdapter,
    "penn-state": PennStateAdapter,
    "pittsburgh": PittsburghAdapter,
    "paris-cite": ParisCiteAdapter,
    "polimi": PolimiAdapter,
    "polyu": PolyUAdapter,
    "puc-chile": PUCChileAdapter,
    "postech": POSTECHAdapter,
    "princeton": PrincetonAdapter,
    "psl": PSLAdapter,
    "purdue": PurdueAdapter,
    "qatar": QatarAdapter,
    "qmul": QMULAdapter,
    "qub": QUBAdapter,
    "queens-ontario": QueensOntarioAdapter,
    "radboud": RadboudAdapter,
    "reading": ReadingAdapter,
    "rice": RiceAdapter,
    "rmit": RMITAdapter,
    "rockefeller": RockefellerAdapter,
    "rochester": RochesterAdapter,
    "rwth": RWTHAdapter,
    "sapienza": SapienzaAdapter,
    "science-tokyo": ScienceTokyoAdapter,
    "sjtu": SJTUAdapter,
    "skku": SKKUAdapter,
    "sheffield": SheffieldAdapter,
    "sichuan": SichuanAdapter,
    "shenzhen": ShenzhenAdapter,
    "snu": SNUAdapter,
    "southampton": SouthamptonAdapter,
    "st-andrews": StAndrewsAdapter,
    "sorbonne": SorbonneAdapter,
    "stanford": StanfordAdapter,
    "stockholm": StockholmAdapter,
    "strasbourg": StrasbourgAdapter,
    "sun-yat-sen": SunYatSenAdapter,
    "sustech": SUSTechAdapter,
    "swinburne": SwinburneAdapter,
    "sydney": SydneyAdapter,
    "tamu": TAMUAdapter,
    "tec-monterrey": TecMonterreyAdapter,
    "tel-aviv": TelAvivAdapter,
    "toronto": TorontoAdapter,
    "tohoku": TohokuAdapter,
    "tongji": TongjiAdapter,
    "trinity": TrinityAdapter,
    "tsinghua": TsinghuaAdapter,
    "tudelft": TUDelftAdapter,
    "tue": TUEAdapter,
    "tum": TUMAdapter,
    "tubingen": TubingenAdapter,
    "tufts": TuftsAdapter,
    "twente": TwenteAdapter,
    "uab": UABAdapter,
    "tu-wien": TUWienAdapter,
    "tu-berlin": TUBerlinAdapter,
    "tu-dresden": TUDresdenAdapter,
    "ubc": UBCAdapter,
    "uba": UBAAdapter,
    "uchicago": UChicagoAdapter,
    "ucl": UCLAdapter,
    "uclouvain": UCLouvainAdapter,
    "ucla": UCLAAdapter,
    "uc-davis": UCDavisAdapter,
    "ucsd": UCSDAdapter,
    "ucsb": UCSBAdapter,
    "ucsf": UCSFAdapter,
    "uci": UCIAdapter,
    "ucsc": UCSCAdapter,
    "ucas": UCASAdapter,
    "ucd": UCDAdapter,
    "uchile": UChileAdapter,
    "uiuc": UIUCAdapter,
    "ukm": UKMAdapter,
    "unsw": UNSWAdapter,
    "uq": UQAdapter,
    "utrecht": UtrechtAdapter,
    "utah": UtahAdapter,
    "utm": UTMAdapter,
    "upm": UPMAdapter,
    "ut-austin": UTAustinAdapter,
    "umd": UMDAdapter,
    "um": UMAdapter,
    "unam": UNAMAdapter,
    "unc": UNCAdapter,
    "universitas-indonesia": UniversitasIndonesiaAdapter,
    "upenn": UpennAdapter,
    "uppsala": UppsalaAdapter,
    "utokyo": UTokyoAdapter,
    "uts": UTSAdapter,
    "utsw": UTSWAdapter,
    "usm": USMAdapter,
    "usc": USCAdapter,
    "usp": USPAdapter,
    "ustc": USTCAdapter,
    "uva": UvAAdapter,
    "vanderbilt": VanderbiltAdapter,
    "uow": UOWAdapter,
    "uzh": UZHAdapter,
    "uwa": UWAAdapter,
    "warwick": WarwickAdapter,
    "washington": WashingtonAdapter,
    "washu": WashUAdapter,
    "wageningen": WageningenAdapter,
    "weizmann": WeizmannAdapter,
    "waterloo": WaterlooAdapter,
    "western": WesternAdapter,
    "wisconsin": WisconsinAdapter,
    "wuhan": WuhanAdapter,
    "wurzburg": WurzburgAdapter,
    "xjtu": XJTUAdapter,
    "yale": YaleAdapter,
    "york": YorkAdapter,
    "yonsei": YonseiAdapter,
    "zju": ZJUAdapter,
    "alberta": AlbertaAdapter,
    "ksu": KSUAdapter,
    "vienna": ViennaAdapter,
    "vu-amsterdam": VUAmsterdamAdapter,
}
