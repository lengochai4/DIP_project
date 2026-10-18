"""Observed contact break must discard the display tail before wide release."""
from dataclasses import replace
import numpy as np
import pytest
from test_stem_ui import SETTINGS
from test_chemistry import aim,with_ratio
from submission.stem_ui.camera_space import CameraSpace
from submission.stem_ui.chemistry import ChemistryScene
from submission.stem_ui.chemistry_input import ChemistryInput


def setup(edit=False):
    scene=ChemistryScene(SETTINGS); scene.add_template('H2O'); scene.edit=edit
    c=ChemistryInput(scene,SETTINGS); space=CameraSpace(4/3)
    nx,ny=space.project(scene.atoms[scene.selected].position)
    for t in (1.,1.05): c.update([with_ratio(aim(nx,ny),.1)],t,space)
    c.update([with_ratio(aim(nx+.02,ny),.1)],1.1,space); c.advance(.01)
    assert 0 in c.claims
    return c,space,nx,ny


def state(c):
    return {i:(a.position.copy(),a.scale) for i,a in c.scene.atoms.items()}


def unchanged(c,expected):
    for i,(position,scale) in expected.items():
        np.testing.assert_allclose(c.scene.atoms[i].position,position,atol=1e-12)
        assert c.scene.atoms[i].scale==pytest.approx(scale)


@pytest.mark.parametrize('edit',(False,True))
def test_partial_raw_opening_freezes_then_releases_without_follow_tail(edit):
    c,space,nx,ny=setup(edit); frozen=state(c)
    filtered=with_ratio(aim(nx+.12,ny),.1)
    raw=with_ratio(aim(nx+.12,ny),.38)
    opened=replace(filtered,raw_landmarks=raw.landmarks)
    c.update([opened],1.15,space); c.advance(.1)
    assert c.claims[0].paused
    unchanged(c,frozen)
    c.update([opened],1.20,space); c.advance(.1)
    assert not c.claims
    unchanged(c,frozen)
    for t in (1.25,1.30,1.35):
        c.update([opened],t,space); c.advance(.1)
    assert not c.claims
    unchanged(c,frozen)


@pytest.mark.parametrize('edit',(False,True))
def test_one_noisy_break_freezes_but_tight_reclose_rebases_without_jump(edit):
    c,space,nx,ny=setup(edit); frozen=state(c)
    c.update([with_ratio(aim(nx+.1,ny),.38)],1.15,space); c.advance(.1)
    unchanged(c,frozen)
    # Dropping back into the wide hysteresis band is still opening.
    c.update([with_ratio(aim(nx+.12,ny),.31)],1.17,space); c.advance(.1)
    unchanged(c,frozen)
    closed=with_ratio(aim(nx+.12,ny),.1)
    c.update([closed],1.18,space); c.advance(.1)
    assert 0 in c.claims and not c.claims[0].paused
    unchanged(c,frozen)
    c.update([with_ratio(aim(nx+.14,ny),.1)],1.22,space); c.advance(.1)
    assert np.linalg.norm(c.scene.atoms[c.scene.selected].position-frozen[c.scene.selected][0])>0


@pytest.mark.parametrize('edit',(False,True))
def test_missing_input_does_not_complete_opening_or_link_atoms(edit,monkeypatch):
    c,space,nx,ny=setup(edit); links=[]
    monkeypatch.setattr(c.scene,'link_nearby',lambda *a:links.append(1))
    c.update([with_ratio(aim(nx+.1,ny),.38)],1.15,space)
    frozen=state(c)
    c.update([],1.18,space); c.advance(.1)
    c.update([with_ratio(aim(nx+.2,ny),.38)],1.22,space); c.advance(.1)
    assert 0 in c.claims and not links
    unchanged(c,frozen)
    c.release(); assert not links


def test_two_hand_release_freezes_scale_and_remaining_hand_rebases():
    c,space,nx,ny=setup()
    one=with_ratio(aim(nx+.02,ny),.1); two=with_ratio(aim(.88,.55,slot=1),.1)
    for t in (1.12,1.16): c.update([one,two],t,space); c.advance(.02)
    assert len(c.claims)==2
    frozen=state(c)
    opening=with_ratio(aim(.96,.65,slot=1),.38)
    c.update([with_ratio(aim(nx+.04,ny),.1),opening],1.20,space); c.advance(.2)
    unchanged(c,frozen)
    c.update([with_ratio(aim(nx+.06,ny),.1),opening],1.25,space); c.advance(.2)
    assert set(c.claims)=={0}
    unchanged(c,frozen)
    c.update([with_ratio(aim(nx+.08,ny),.1),opening],1.30,space); c.advance(.05)
    assert set(c.claims)=={0}
    assert np.linalg.norm(c.scene.atoms[c.scene.selected].position-frozen[c.scene.selected][0])>0
