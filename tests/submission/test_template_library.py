"""Neutral textbook connectivity, atom identity, pagination and display geometry."""
from collections import Counter
from dataclasses import replace
from types import SimpleNamespace
import copy
import numpy as np
import pytest
from test_stem_ui import SETTINGS,palm
from submission.stem_ui.chemistry import ChemistryScene
from submission.stem_ui.chemistry_input import ChemistryInput
from submission.stem_ui.geometry import FingerSelection

EXPECTED={
    'H2O':'H2O','CO2':'CO2','CH4':'CH4','NH3':'H3N','H2':'H2','O2':'O2','N2':'N2','HCl':'ClH',
    'F2':'F2','Cl2':'Cl2','Br2':'Br2','I2':'I2','HF':'FH','HBr':'BrH','HI':'HI',
    'H2S':'H2S','H2O2':'H2O2','PH3':'H3P','C2H6':'C2H6','C2H4':'C2H4','C2H2':'C2H2',
    'C3H8':'C3H8','CH3OH':'CH4O','C2H5OH':'C2H6O','CH3OCH3':'C2H6O','CH2O':'CH2O',
    'CH3CHO':'C2H4O','CH3COCH3':'C3H6O','HCOOH':'CH2O2','CH3COOH':'C2H4O2','HCN':'CHN','CS2':'CS2',
}


@pytest.mark.parametrize('key',tuple(EXPECTED))
def test_preset_formula_exact_neutral_valence_and_renumbered_graph(key):
    s=ChemistryScene(SETTINGS); s.add_template(key)
    ids=s.component(s.selected)
    assert s.formula(ids)==EXPECTED[key]
    for i in ids: assert s.valence(i)==SETTINGS['chemistry_covalent_limits'][s.atoms[i].symbol]
    state=s.state(); perm=np.random.default_rng(17).permutation(len(ids))+101
    mapping=dict(zip(ids,map(int,perm)))
    for atom in state['atoms']: atom['id']=mapping[atom['id']]
    for bond in state['bonds']: bond['a']=mapping[bond['a']]; bond['b']=mapping[bond['b']]
    s.restore(state)
    assert s.describe(s.component(min(s.atoms)))==SETTINGS['chemistry_templates'][key]['label']


def test_same_formula_ethanol_and_dimethyl_ether_have_distinct_names_after_cache_restore():
    s=ChemistryScene(SETTINGS); s.add_template('C2H5OH')
    ethanol=s.state(); ethanol_name=s.describe(s.component(s.selected))
    assert 'Etanol' in ethanol_name
    other=ChemistryScene(SETTINGS); other.add_template('CH3OCH3')
    ether=other.state()
    assert Counter(a['symbol'] for a in ethanol['atoms'])==Counter(a['symbol'] for a in ether['atoms'])
    s.restore(ether); assert 'Đimetyl ete' in s.describe(s.component(min(s.atoms)))
    s.restore(ethanol); assert s.describe(s.component(min(s.atoms)))==ethanol_name
    hydrogen=next(i for i,a in s.atoms.items() if a.symbol=='H')
    s.move_atom(hydrogen,(7.,7.,0))
    assert 'đang xây dựng' in s.describe(s.component(1))


def test_preset_pages_cover_all_32_without_overflow():
    s=ChemistryScene(SETTINGS); c=ChemistryInput(s,SETTINGS); seen=[]
    keys=list(SETTINGS['chemistry_templates'])
    assert len(keys)==32
    for page in range(4):
        assert c.template_page==page
        seen.extend(keys[c.template_page*8:(c.template_page+1)*8]); c.command('templates_next')
    assert seen==keys and c.template_page==3
    for _ in range(10): c.command('templates_prev')
    assert c.template_page==0


@pytest.mark.parametrize('key',('C2H2','HCN','CO2','CS2'))
def test_linear_presets_are_collinear(key):
    t=SETTINGS['chemistry_templates'][key]; p=np.array(t['positions'],dtype=float)
    assert np.linalg.matrix_rank(p-p.mean(axis=0),tol=1e-4)==1


@pytest.mark.parametrize('key',('CH4','NH3','PH3','C3H8'))
def test_volume_presets_do_not_collapse_into_a_plane(key):
    p=np.array(SETTINGS['chemistry_templates'][key]['positions'],dtype=float)
    assert np.linalg.matrix_rank(p-p.mean(axis=0),tol=1e-4)==3


def test_invalid_preset_is_rejected_before_scene_changes():
    bad=copy.deepcopy(SETTINGS); bad['chemistry_templates']['H2O']['bonds'][0][2]=3
    with pytest.raises(ValueError): ChemistryScene(bad)


@pytest.mark.parametrize('kind',('nan','duplicate_index','invalid_aspect'))
def test_invalid_finger_observation_clears_active_vertices(kind):
    p=list(palm()); c=FingerSelection(SETTINGS); assert c.update(p,4/3)
    aspect=4/3
    if kind=='nan': p[8]=SimpleNamespace(index=8,x=float('nan'),y=.2,z=0.)
    if kind=='duplicate_index': p[8]=replace(p[8],index=9)
    if kind=='invalid_aspect': aspect=0
    assert c.update(p,aspect)==() and not c.active
