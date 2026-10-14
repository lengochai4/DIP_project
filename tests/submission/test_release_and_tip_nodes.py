"""Reported opening lag and geometry must not invent fingertip vertices."""
from dataclasses import replace
import numpy as np
import pytest
from test_stem_ui import SETTINGS,hand,palm
from test_chemistry import aim
from submission.stem_ui.camera_space import CameraSpace
from submission.stem_ui.chemistry import ChemistryScene
from submission.stem_ui.chemistry_input import ChemistryInput
from submission.stem_ui.geometry import FingerSelection,Tip,live_mesh
from submission.stem_ui.manipulation import GrabController


@pytest.mark.parametrize('edit',(False,True))
def test_raw_opening_freezes_chemistry_even_when_filtered_fingers_still_touch(edit):
    scene=ChemistryScene(SETTINGS); i=scene.add('C',(.6,0,0)); scene.edit=edit
    c=ChemistryInput(scene,SETTINGS); space=CameraSpace(4/3)
    nx,ny=space.project(scene.atoms[i].position)
    closed=aim(nx,ny)
    for t in (1.,1.05): c.update((replace(closed,raw_landmarks=closed.landmarks),),t,space)
    shifted=aim(nx+.06,ny)
    c.update((replace(shifted,raw_landmarks=shifted.landmarks),),1.1,space); c.advance(.016)
    before=scene.atoms[i].position.copy()
    # Motion filter deliberately remains at a closed/shifted pose.
    filtered=aim(nx+.3,ny); raw_open=aim(nx+.3,ny,pinch=False)
    opened=replace(filtered,raw_landmarks=raw_open.landmarks)
    c.update((opened,),1.12,space)
    for _ in range(20): c.advance(1/60)
    np.testing.assert_allclose(scene.atoms[i].position,before)
    c.update((opened,),1.2,space); assert not c.claims
    for _ in range(20): c.advance(1/60)
    np.testing.assert_allclose(scene.atoms[i].position,before)


def test_two_hand_opening_freezes_then_remaining_hand_rebases_without_jump():
    settings={**SETTINGS,'grip_release_s':.065}
    c=GrabController(settings)
    hs=(hand(0,.3),hand(1,.7))
    c.update(hs,1.,4/3); c.update(hs,1.05,4/3)
    c.update((hand(0,.2),hand(1,.8)),1.1,4/3); c.advance(.016)
    before=c.pose.copy()
    opened=replace(hand(1,.95),raw_landmarks=hand(1,.95,pinch=False).landmarks)
    c.update((hand(0,.15),opened),1.12,4/3); c.advance(.1)
    np.testing.assert_allclose(c.pose.position,before.position)
    assert c.pose.scale==before.scale
    c.update((hand(0,.15),opened),1.2,4/3); c.advance(.1)
    assert c.slots==(0,)
    np.testing.assert_allclose(c.pose.position,before.position)
    assert c.pose.scale==before.scale


@pytest.mark.parametrize('count',range(0,11))
def test_geometry_has_exactly_one_vertex_per_observed_fingertip(count):
    points=[(np.cos(i),np.sin(i),.12*np.cos(2*i)) for i in range(count)]
    tips=[Tip(i//5,(4,8,12,16,20)[i%5],p) for i,p in enumerate(points)]
    mesh=live_mesh(tips,.65)
    assert mesh.vertices==tuple(points)
    assert all(index<count for face in mesh.faces for index in face)
    if count<3: assert not mesh.faces


def test_straight_finger_pointing_back_toward_palm_is_not_extended():
    points=list(palm())
    for index,y in ((6,.53),(7,.56),(8,.59)): points[index]=replace(points[index],y=y)
    selection=FingerSelection(SETTINGS); selection.active.add(8)
    assert 8 not in selection.update(tuple(points),4/3)
