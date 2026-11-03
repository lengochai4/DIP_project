import pytest
from submission.stem_ui.dwell import DwellSelector


def observed(selector, start, end, target='a', generation=0, point=(.2,.3)):
    triggered=[]
    for i in range(round((end-start)*20)+1):
        result=selector.update(0,generation,target,start+i/20,point)
        if result is not None: triggered.append(result)
    return triggered


def test_continuous_dwell_is_one_shot_and_page_change_does_not_repeat():
    d=DwellSelector(3.,.25,.035)
    assert not observed(d,0,2.95)
    assert d.update(0,0,'a',3.,(.2,.3))=='a'
    assert not observed(d,3.05,7.,target='new_page_button')
    assert not observed(d,7.05,7.1,target='new_page_button',point=(.26,.3))
    assert observed(d,7.15,10.15,target='new_page_button',point=(.26,.3))==['new_page_button']


@pytest.mark.parametrize('interruption',('missing','gap','generation','backward','invalid','target','outside'))
def test_interrupted_dwell_cannot_spend_time_from_previous_target(interruption):
    d=DwellSelector(3.,.25,.035); observed(d,0,2.5)
    start=2.6; generation=0; target='a'
    if interruption=='missing': d.retain(())
    elif interruption=='gap': start=3.
    elif interruption=='generation': generation=1
    elif interruption=='backward': d.update(0,0,'a',2.,(.2,.3))
    elif interruption=='invalid': d.update(0,0,'a',float('nan'),(.2,.3))
    elif interruption=='target': target='b'
    else: d.update(0,0,None,2.55,(.9,.9),outside=True)
    assert not observed(d,start,start+2.95,target,generation)
    assert d.update(0,generation,target,start+3.,(.2,.3))==target


def test_two_hands_accumulate_independently_and_reset_clears_progress():
    d=DwellSelector(3.,.25,.035)
    for i in range(61):
        t=i/20
        a=d.update(0,0,'a',t,(.2,.3))
        b=d.update(1,2,'b',t,(.7,.3))
    assert (a,b)==('a','b')
    d.reset(); assert not d.states
