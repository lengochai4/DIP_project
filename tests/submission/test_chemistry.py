"""Sourced atom data and explicit, limited molecular editor behavior."""
from dataclasses import replace
import copy
from pathlib import Path
import numpy as np
import pytest
from test_stem_ui import SETTINGS,hand
from submission.stem_ui.chemistry import ChemistryScene,load_elements
from submission.stem_ui.chemistry_input import ChemistryInput
from submission.stem_ui.camera_space import CameraSpace,SpatialPanel,letterbox
from submission.stem_ui.geometry import bone_transforms


def aim(nx,ny,slot=0,pinch=True,generation=0):
    return replace(hand(slot,x=1.12-nx,y=ny+.225,pinch=pinch),generation=generation)


def test_primary_data_contains_all_118_symbols_and_electrons_without_invented_neutrons():
    elements=load_elements()
    assert {e.number for e in elements.values()}==set(range(1,119))
    assert all(sum(e.shells)==e.number for e in elements.values())
    assert elements['C'].shells==(2,4) and elements['Fe'].shells==(2,8,14,2)
    assert elements['Og'].number==118 and len(elements)==118


@pytest.mark.parametrize('aspect',(4/3,16/9,9/16))
def test_camera_projection_round_trip_matches_mirrored_display_coordinates(aspect):
    space=CameraSpace(aspect)
    for nx,ny,z in ((.2,.3,0.),(.8,.6,.8),(.5,.5,-.3)):
        assert space.project(space.point(nx,ny,z))==pytest.approx((nx,ny))
    x,y,w,h=letterbox((20,100,1000,600),aspect)
    assert w/h==pytest.approx(aspect,rel=.005) and x>=20 and y>=100


@pytest.mark.parametrize('aspect',(4/3,16/9,9/16))
@pytest.mark.parametrize('full',(False,True))
def test_spatial_panel_hits_the_visible_projected_button_and_fits_camera(aspect,full):
    space=CameraSpace(aspect); panel=SpatialPanel(full,space)
    panel.targets=[((200,200,100,100),'element:H')]
    nx,ny=space.project(panel.world(250,250))
    assert panel.intersect(*space.ray(nx,ny))[1]=='element:H'
    assert panel.intersect(*space.ray(1.5,1.5)) is None
    for x,y in ((0,0),(panel.pixels[0],0),(panel.pixels[0],panel.pixels[1]),(0,panel.pixels[1])):
        nx,ny=space.project(panel.world(x,y))
        assert 0<=nx<=1 and 0<=ny<=1


def test_supported_bonds_enforce_explicit_neutral_valence_and_do_not_guess_metals():
    scene=ChemistryScene(SETTINGS)
    h=scene.add('H',(0,0,0)); o=scene.add('O',(.5,0,0)); h2=scene.add('H',(1,0,0))
    assert scene.bond(h,o) and scene.bond(o,h2)
    assert not scene.bond(h,h2) and not scene.bond(h,h)
    na=scene.add('Na',(0,1,0)); cl=scene.add('Cl',(.5,1,0))
    assert not scene.bond(na,cl)
    assert len(scene.bonds)==2


def test_formula_does_not_label_carbon_dioxide_without_matching_double_bonds():
    s=ChemistryScene(SETTINGS)
    c=s.add('C',(0,0,0)); a=s.add('O',(-.5,0,0)); b=s.add('O',(.5,0,0))
    s.bond(c,a); s.bond(c,b)
    assert 'đang xây dựng' in s.describe(s.component(c))
    s.bond(c,a,2); s.bond(c,b,2)
    assert s.describe(s.component(c)).startswith('CO₂')


@pytest.mark.parametrize('key',tuple(SETTINGS['chemistry_templates']))
def test_templates_have_supported_topology_and_match_label(key):
    s=ChemistryScene(SETTINGS); s.add_template(key)
    component=s.component(s.selected)
    assert len(component)==len(SETTINGS['chemistry_templates'][key]['symbols'])
    assert s.describe(component)==SETTINGS['chemistry_templates'][key]['label']
    for i in component: assert s.valence(i)<=SETTINGS['chemistry_covalent_limits'][s.atoms[i].symbol]
    s.restore(s.state())


def test_edit_breaks_links_only_when_deliberately_moved_and_undo_restores_whole_edit():
    s=ChemistryScene(SETTINGS); s.add_template('H2O'); original=s.state()
    h=next(i for i,a in s.atoms.items() if a.symbol=='H')
    s.begin_edit(); s.move_atom(h,(2.3,0,0)); s.advance(.2); s.finish_edit()
    assert len(s.bonds)==1
    s.undo(); assert s.state()==original
    s.undo(redo=True); assert len(s.bonds)==1


def test_invalid_import_is_atomic_and_preserves_existing_workspace(tmp_path):
    s=ChemistryScene(SETTINGS); s.add_template('CH4'); before=s.state()
    invalid=copy.deepcopy(before); invalid['atoms'][0]['position'][0]=float('nan')
    with pytest.raises(ValueError): s.restore(invalid)
    assert s.state()==before
    invalid=copy.deepcopy(before); invalid['bonds'].append(invalid['bonds'][0])
    with pytest.raises(ValueError,match='trùng'): s.restore(invalid)
    assert s.state()==before
    invalid=copy.deepcopy(before); invalid['bonds'][0]['order']=1.0
    with pytest.raises(ValueError): s.restore(invalid)
    assert s.state()==before
    p=tmp_path/'workspace.json'; s.save(p); s.delete_selected(); assert not s.atoms
    s.load(p); assert s.state()==before


def test_confirmed_palette_pinch_spawns_once_even_when_hold_continues():
    s=ChemistryScene(SETTINGS); c=ChemistryInput(s,SETTINGS); space=CameraSpace(4/3)
    panel=SpatialPanel(False,space); panel.targets=[((0,0,720,1000),'element:H')]; c.panel=panel
    nx,ny=space.project(panel.world(360,400))
    for t in (1.,1.05,1.1,1.15,1.2): c.update((aim(nx,ny),),t,space)
    assert len(s.atoms)==1 and c.claims[0].kind=='panel'
    c.update((aim(nx,ny,pinch=False),),1.25,space)
    c.update((aim(nx,ny,pinch=False),),1.36,space)
    c.update((aim(nx,ny),),1.4,space); c.update((aim(nx,ny),),1.45,space)
    assert len(s.atoms)==2


def test_hover_without_pinch_never_creates_atom():
    s=ChemistryScene(SETTINGS); c=ChemistryInput(s,SETTINGS); space=CameraSpace(4/3)
    panel=SpatialPanel(False,space); panel.targets=[((0,0,720,1000),'element:O')]; c.panel=panel
    nx,ny=space.project(panel.world(360,400))
    for t in (1,1.05,1.1): c.update((aim(nx,ny,pinch=False),),t,space)
    assert not s.atoms


def test_confirmed_mode_button_is_latched_instead_of_repeatedly_toggling():
    s=ChemistryScene(SETTINGS); c=ChemistryInput(s,SETTINGS); space=CameraSpace(4/3)
    panel=SpatialPanel(False,space); panel.targets=[((0,0,720,1000),'edit')]; c.panel=panel
    nx,ny=space.project(panel.world(360,400))
    for t in (1,1.05,1.1,1.15,1.2): c.update((aim(nx,ny),),t,space)
    assert s.edit is True


def test_tracking_loss_cancels_atom_claim_without_accidental_join():
    s=ChemistryScene(SETTINGS); s.edit=True
    h=s.add('H',(.5,0,0)); o=s.add('O',(.95,0,0))
    c=ChemistryInput(s,SETTINGS); space=CameraSpace(4/3)
    nx,ny=space.project(s.atoms[h].position)
    c.update((aim(nx,ny),),1,space); c.update((aim(nx,ny),),1.05,space)
    assert c.claims[0].target==h
    c.update((),1.1,space); c.advance(.05)
    c.update((),1.4,space)
    assert not c.claims and not s.bonds


def test_short_atom_tracking_loss_rebases_without_recovery_jump():
    s=ChemistryScene(SETTINGS); s.edit=True; i=s.add('C',(.6,0,0))
    c=ChemistryInput(s,SETTINGS); space=CameraSpace(4/3)
    nx,ny=space.project(s.atoms[i].position)
    c.update((aim(nx,ny),),1.,space); c.update((aim(nx,ny),),1.05,space)
    c.update((),1.1,space); before=s.atoms[i].position.copy()
    c.update((aim(nx+.15,ny),),1.15,space); c.advance(.05)
    np.testing.assert_allclose(s.atoms[i].position,before)
    assert c.claims[0].kind=='atom'


def test_visible_confirmed_atom_release_joins_but_pending_open_does_not():
    s=ChemistryScene(SETTINGS); s.edit=True
    h=s.add('H',(.5,0,0)); s.add('O',(1.,0,0))
    c=ChemistryInput(s,SETTINGS); space=CameraSpace(4/3)
    nx,ny=space.project(s.atoms[h].position)
    c.update((aim(nx,ny),),1.,space); c.update((aim(nx,ny),),1.05,space)
    c.update((aim(nx,ny,pinch=False),),1.1,space)
    assert not s.bonds
    c.update((aim(nx,ny,pinch=False),),1.21,space)
    assert len(s.bonds)==1


def test_return_to_camera_workspace_preserves_graph_and_can_be_undone():
    s=ChemistryScene(SETTINGS); s.add_template('NH3')
    for atom in s.atoms.values(): atom.position+=np.array((5.,2.,0.)); atom.target=atom.position.copy()
    before=s.state(); c=ChemistryInput(s,SETTINGS)
    c.command('frame'); s.advance(.5)
    assert max(a.position[0] for a in s.atoms.values())<2
    assert len(s.bonds)==3
    s.undo(); assert s.state()==before


def test_two_hands_can_grab_distinct_atoms_without_claim_transfer():
    s=ChemistryScene(SETTINGS); s.edit=True
    a=s.add('H',(-.5,0,0)); b=s.add('O',(.7,0,0))
    c=ChemistryInput(s,SETTINGS); space=CameraSpace(4/3)
    pa,pb=space.project(s.atoms[a].position),space.project(s.atoms[b].position)
    hs=(aim(*pa,0),aim(*pb,1))
    c.update(hs,1,space); c.update(hs,1.05,space)
    assert {claim.target for claim in c.claims.values()}=={a,b}
    replacement=(aim(*pa,0,generation=1),aim(*pb,1))
    c.update(replacement,1.1,space)
    assert 0 not in c.claims and c.claims[1].target==b


def test_whole_molecule_moves_with_one_hand_and_scales_with_second_without_first_frame_jump():
    s=ChemistryScene(SETTINGS); s.add_template('H2O'); before={i:a.position.copy() for i,a in s.atoms.items()}
    c=ChemistryInput(s,SETTINGS); space=CameraSpace(4/3)
    ids=list(s.atoms); point=space.project(s.atoms[ids[0]].position)
    c.update((aim(*point),),1,space); c.update((aim(*point),),1.05,space)
    c.advance(.016)
    for i,p in before.items(): np.testing.assert_allclose(s.atoms[i].position,p,atol=1e-10)
    c.update((aim(point[0]+.1,point[1]),),1.1,space); c.advance(.1)
    assert s.atoms[ids[0]].position[0]>before[ids[0]][0]
    p0=space.project(s.atoms[ids[0]].position); p1=space.project(s.atoms[ids[1]].position)
    c.update((aim(*p0,0),aim(*p1,1)),1.15,space)
    c.update((aim(*p0,0),aim(*p1,1)),1.2,space)
    span=np.linalg.norm(s.atoms[ids[0]].position-s.atoms[ids[1]].position)
    c.update((aim(p0[0]+.1,p0[1],0),aim(p1[0]-.1,p1[1],1)),1.25,space); c.advance(.1)
    assert np.linalg.norm(s.atoms[ids[0]].position-s.atoms[ids[1]].position)>span
    assert all(a.scale>1 for a in s.atoms.values())
    s.restore(s.state())


def test_batch_bone_frames_preserve_endpoints_and_skip_collapsed_bones():
    p=np.array(((0,0,0),(1,0,0),(0,1,0),(0,0,1),(0,0,0)),dtype=float)
    edges=np.array(((0,1),(0,2),(0,3),(0,4)))
    matrices,lengths=bone_transforms(p,edges)
    assert len(matrices)==3
    for matrix,length,end in zip(matrices,lengths,p[1:4]):
        np.testing.assert_allclose(matrix[:3,3]+length*matrix[:3,2],end)
        np.testing.assert_allclose(matrix[:3,:3].T@matrix[:3,:3],np.eye(3))


def test_fast_fingertip_display_following_is_bounded_and_does_not_overshoot():
    from submission.stem_ui.renderer import SubmissionRenderer
    r=SubmissionRenderer(SETTINGS); start=np.zeros(3); target=np.array((1.,.5,.1))
    followed=r._follow_point(start,target,1/60)
    old=(1-np.exp(-2*np.pi*SETTINGS['live_response_hz']/60))*target
    assert np.linalg.norm(followed)>np.linalg.norm(old)
    assert np.linalg.norm(followed)<np.linalg.norm(target)
    np.testing.assert_allclose(r._follow_point(start,start,1/60),start)
