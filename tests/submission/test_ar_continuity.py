"""AR hot paths must preserve input semantics without repainting unchanged UI."""
from types import SimpleNamespace
from dataclasses import replace
import pygame
from test_stem_ui import SETTINGS,hand
from test_chemistry import with_ratio
from submission.stem_ui.chemistry import ChemistryScene
from submission.stem_ui.chemistry_input import ChemistryInput
from submission.stem_ui.chemistry_view import CameraChemistryView
from submission.stem_ui.manipulation import GrabController,PinchGate


def test_panel_does_not_rebuild_for_atom_or_button_hover_motion_or_bond_graph(monkeypatch):
    import submission.stem_ui.chemistry_view as module
    view=CameraChemistryView(SETTINGS,SimpleNamespace(help_visible=True))
    c=view.input; view.scene.add_template('H2O')
    surface=pygame.Surface((2,2),pygame.SRCALPHA); calls=[]; clock=[10.]
    monkeypatch.setattr(module.time,'monotonic',lambda:clock[0])
    monkeypatch.setattr(view,'_panel',lambda:(SimpleNamespace(full=False),surface))
    monkeypatch.setattr(view,'_upload',lambda *args,**kwargs:calls.append(c.page))
    view.panel_texture=1
    view._ensure_panel(); assert len(calls)==1
    for i in range(30):
        clock[0]+=.1; c.hover={0:'atom:'+str(i%3+1),1:None}
        view.scene.move_atom(2,(3+i*.01,0,0)); view._ensure_panel()
    assert len(calls)==1
    c.hover={0:'elements'}; view._ensure_panel(); assert len(calls)==1
    clock[0]+=.1; c.hover={0:'elements',1:'elements'}; view._ensure_panel()
    assert len(calls)==1


def test_panel_semantic_changes_refresh_immediately_inside_hover_rate_limit(monkeypatch):
    import submission.stem_ui.chemistry_view as module
    view=CameraChemistryView(SETTINGS,SimpleNamespace(help_visible=True))
    view.scene.add_template('H2O'); view.input.page='elements'
    surface=pygame.Surface((2,2),pygame.SRCALPHA); symbols=[]
    def panel():
        symbols.append(view.scene.atoms[view.scene.selected].symbol)
        return SimpleNamespace(full=False),surface
    monkeypatch.setattr(module.time,'monotonic',lambda:10.)
    monkeypatch.setattr(view,'_panel',panel)
    monkeypatch.setattr(view,'_upload',lambda *args,**kwargs:None)
    view.panel_texture=1
    view._ensure_panel(); view.scene.selected=2; view._ensure_panel()
    assert symbols==['O','H']
    view.scene.selected=3; view._ensure_panel(); assert symbols==['O','H']


def test_light_gate_preserves_raw_pinch_confirmation_opening_loss_and_generation():
    settings=ChemistryInput(ChemistryScene(SETTINGS),SETTINGS).grab_settings
    full=GrabController(settings); gate=PinchGate(settings)
    closed=with_ratio(hand(),.1); opened=with_ratio(hand(),.9)
    samples=[(1.,[closed]),(1.05,[closed]),(1.1,[closed]),(1.12,[opened]),
        (1.14,[closed]),(1.2,[opened]),(1.3,[opened]),
        (1.4,[replace(closed,generation=1)]),(1.45,[replace(closed,generation=1)]),
        (1.5,[]),(1.8,[]),(1.7,[closed])]
    for t,hands in samples:
        full.update(hands,t,4/3); gate.update(hands,t,4/3)
        assert (gate.slots,gate.suspended)==(full.slots,full.suspended)
        assert {s:(g.held,g.pending_since) for s,g in gate.grips.items()}=={
            s:(g.held,g.pending_since) for s,g in full.grips.items()}


def test_gate_does_not_calculate_unused_object_orientation(monkeypatch):
    import submission.stem_ui.manipulation as module
    settings=ChemistryInput(ChemistryScene(SETTINGS),SETTINGS).grab_settings
    gate=PinchGate(settings)
    def unnecessary(*args,**kwargs): raise AssertionError('gate must not compute object pose')
    monkeypatch.setattr(module,'hand_anchor',unnecessary)
    monkeypatch.setattr(module,'quaternion',unnecessary)
    closed=with_ratio(hand(),.1)
    gate.update([closed],1.,4/3); gate.update([closed],1.05,4/3)
    assert gate.slots==(0,) and not gate.suspended
