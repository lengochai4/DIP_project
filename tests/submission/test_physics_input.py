"""Exclusive target claims, selection latches and interruption handling."""
from types import SimpleNamespace
import numpy as np
import pytest
from test_stem_ui import SETTINGS
from test_point_pinch import sample
from submission.stem_ui.physics_input import PhysicsInput


class Host:
    page_key='forces/adjust'
    def __init__(self): self.action='run'; self.commands=[]; self.moves=[]; self.pauses=0
    def hit(self,point): return self.action
    def capture(self,action): return {'value':1}
    def pause_edit(self): self.pauses+=1
    def command(self,action): self.commands.append(action)
    def drag(self,*args): self.moves.append(args)


def select(control,start=1):
    for delta,ratio in ((0,1),(.06,1),(.12,1),(.17,.4),(.22,.1),(.27,.1)):
        control.update([sample(ratio)],start+delta,4/3)


def test_pinch_selects_once_and_never_turns_into_grab_behind_changed_menu():
    host=Host(); control=PhysicsInput(SETTINGS,host); select(control)
    assert host.commands==['run']
    host.page_key='other'; host.action='drag:body'
    for t in np.arange(1.3,1.9,.04): control.update([sample(.1)],float(t),4/3)
    assert not control.claims and not host.moves


def test_dwell_stays_one_shot_until_deliberate_departure_even_with_open_hand():
    host=Host(); control=PhysicsInput(SETTINGS,host)
    for t in np.arange(1,5,.04): control.update([sample(1)],float(t),4/3)
    assert host.commands==['run']


def test_deliberate_release_and_fresh_pinch_can_select_same_button_again():
    host=Host(); control=PhysicsInput(SETTINGS,host); select(control)
    for t in (1.4,1.5,1.64): control.update([sample(1)],t,4/3)
    for t in (1.7,1.75): control.update([sample(.1)],t,4/3)
    assert host.commands==['run','run']


def test_two_hands_cannot_own_same_handle_but_can_use_distinct_handles():
    host=Host(); host.action='drag:body'; control=PhysicsInput(SETTINGS,host)
    for t in (1,1.05): control.update([sample(.1),sample(.1,slot=1)],t,4/3)
    assert len(control.claims)==1
    host.action='drag:force'
    control.update([sample(.1),sample(.1,slot=1)],1.1,4/3)
    assert len(control.claims)==2 and {c.target for c in control.claims.values()}=={'drag:body','drag:force'}


def test_pending_open_freezes_immediately_and_brief_loss_rebases_return():
    host=Host(); host.action='drag:body'; control=PhysicsInput(SETTINGS,host)
    for t in (1,1.05,1.1): control.update([sample(.1)],t,4/3)
    count=len(host.moves); assert count
    control.update([sample(.8,nx=.4)],1.13,4/3)
    assert len(host.moves)==count and control.claims[0].paused
    control.update([],1.16,4/3)
    control.update([sample(.1,nx=.5)],1.2,4/3)
    last=host.moves[-1]; assert last[1]==last[2]  # resumed origin equals current point


@pytest.mark.parametrize('cause',('generation','long_loss','timestamp'))
def test_discontinuities_drop_previous_claim_without_throw_or_command(cause):
    host=Host(); host.action='drag:body'; control=PhysicsInput(SETTINGS,host)
    for t in (1,1.05): control.update([sample(.1)],t,4/3)
    if cause=='generation': control.update([sample(1,generation=2)],1.1,4/3)
    elif cause=='long_loss': control.update([],1.4,4/3)
    else: control.update([],float('nan'),4/3)
    assert not control.claims and not host.commands


def test_menu_is_blocked_while_another_hand_is_editing():
    host=Host(); host.action='drag:body'; control=PhysicsInput(SETTINGS,host)
    for t in (1,1.05): control.update([sample(.1)],t,4/3)
    host.action='run'
    for t in np.arange(1.1,2.6,.05): control.update([sample(.1),sample(1,slot=1)],float(t),4/3)
    assert not host.commands
