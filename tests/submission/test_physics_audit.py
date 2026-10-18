"""Independent closed-form/conservation references for the mechanics audit.

OpenStax mechanics sources are in physics_labs.yaml. The nonlinear pendulum
reference uses K(k)=pi/(2 AGM(1,sqrt(1-k²))), NIST DLMF 19.8.5.
"""
import json
import csv
import math
import pytest
from submission.stem_ui.physics import PhysicsLab,load_catalog


def evolve(lab,seconds):
    for _ in range(round(seconds/lab.engine['fixed_dt_s'])): lab.step()


@pytest.mark.parametrize('damping',(0.,2.,4.,8.))
def test_spring_phase_matches_under_critical_and_overdamped_closed_forms(damping):
    lab=PhysicsLab('spring'); lab.params.update(mass=1.,stiffness=4.,damping=damping,displacement=.8); lab.reset()
    t=1.25; a=damping/2; w0=2.; x0=.8
    if a<w0:
        w=math.sqrt(w0*w0-a*a)
        x=x0*math.exp(-a*t)*(math.cos(w*t)+a/w*math.sin(w*t))
        v=-x0*math.exp(-a*t)*w0*w0/w*math.sin(w*t)
    elif a==w0:
        x=x0*(1+a*t)*math.exp(-a*t); v=-x0*a*a*t*math.exp(-a*t)
    else:
        root=math.sqrt(a*a-w0*w0); r1,r2=-a+root,-a-root
        c1=-r2*x0/(r1-r2); c2=r1*x0/(r1-r2)
        x=c1*math.exp(r1*t)+c2*math.exp(r2*t)
        v=r1*c1*math.exp(r1*t)+r2*c2*math.exp(r2*t)
    evolve(lab,t)
    assert lab.q[:2]==pytest.approx([x,v],abs=2e-8)
    assert lab.metrics()['balance_j']==pytest.approx(0,abs=2e-8)


@pytest.mark.parametrize('angle',(5.,45.,80.))
def test_nonlinear_pendulum_period_matches_elliptic_integral_reference(angle):
    lab=PhysicsLab('pendulum'); lab.params.update(angle=angle,damping=0.); lab.reset()
    a,b=1.,math.cos(math.radians(angle)/2)
    for _ in range(12): a,b=(a+b)/2,math.sqrt(a*b)
    exact=math.tau*math.sqrt(lab.params['length']/lab.params['gravity'])/a
    evolve(lab,1.6*exact)
    assert lab.period==pytest.approx(exact,rel=2e-6)


def test_damped_pendulum_tension_and_drag_obey_cartesian_newtons_law():
    lab=PhysicsLab('pendulum'); lab.params.update(mass=1.7,length=1.3,gravity=9.81,damping=.4); lab.reset()
    theta,omega=.6,-1.2; lab.q=[theta,omega,0.]
    m=lab.params['mass']; length=lab.params['length']; g=lab.params['gravity']; b=lab.params['damping']
    alpha=-(g/length)*math.sin(theta)-b*omega/(m*length**2)
    ax=length*(alpha*math.cos(theta)-omega**2*math.sin(theta))
    ay=length*(alpha*math.sin(theta)+omega**2*math.cos(theta))
    v=lab.metrics(); tension=v['tension_n']; drag=v['damping_n']
    assert -tension*math.sin(theta)+drag*math.cos(theta)==pytest.approx(m*ax)
    assert tension*math.cos(theta)+drag*math.sin(theta)-m*g==pytest.approx(m*ay)
    assert drag*length*omega==-b*omega**2
    assert v['acceleration_m_s2']==pytest.approx(length*alpha)  # signed tangential, not |a|


def test_pendulum_goal_uses_configured_measured_period_target():
    catalog=load_catalog(); catalog['goals']['pendulum_target_s']=2.4
    lab=PhysicsLab('pendulum',catalog=catalog); lab.challenge=True; lab.period=2.4
    lab._check_goal(); assert lab.achieved


@pytest.mark.parametrize('angle',(0.,30.,90.))
def test_elevated_projectile_matches_ground_intersection_and_energy(angle):
    lab=PhysicsLab('projectile'); lab.params.update(height=1.3,speed=7.,angle=angle,gravity=10.); lab.reset()
    vx=7*math.cos(math.radians(angle)); vy=7*math.sin(math.radians(angle))
    impact=(vy+math.sqrt(vy*vy+26))/10
    evolve(lab,impact+1)
    assert lab.landed and lab.time==pytest.approx(impact,abs=1e-10)
    assert lab.q==pytest.approx([vx*impact,0.,vx,vy-10*impact],abs=1e-10)
    assert lab.metrics()['balance_j']==pytest.approx(0,abs=1e-9)


def test_incline_static_equilibrium_balances_weight_component_without_heat():
    lab=PhysicsLab('incline'); lab.params.update(mass=2.,gravity=10.,angle=30.,force=10.)
    lab.reset(); evolve(lab,1.)
    assert lab.q==pytest.approx([0,0]) and lab.metrics()['thermal_j']==0


def test_collision_loss_matches_reduced_mass_restitution_formula():
    lab=PhysicsLab('collision'); lab.params.update(mass=2.,mass2=3.,velocity1=4.,velocity2=-2.,restitution=.3)
    lab.reset(); evolve(lab,1.)
    assert lab.collided
    assert lab.metrics()['thermal_j']==pytest.approx(.5*(2*3/(2+3))*(1-.3**2)*(4-(-2))**2)


@pytest.mark.parametrize('strands',(1,2,3,4))
def test_all_ideal_pulley_ratios_balance_force_work_and_displacement(strands):
    lab=PhysicsLab('pulley'); lab.params.update(mass=2.,gravity=10.,strands=strands,pull=4.); lab.reset()
    v=lab.metrics()
    assert strands*v['required_n']==20.
    assert strands*v['height_m']==4.
    assert [v['work_j'],v['potential_j']]==pytest.approx([20*4/strands]*2)


@pytest.mark.parametrize('legacy_hash',(
    '8f0a24f1bfce193d05c4d4b9c5f685c5c0658717b2c8be998c4d313a710f9402',
    'f27e940293e274c0131e250b859f36ca9104c01daba6e45789dacb7648957d13'))
def test_old_setup_is_migrated_as_initial_parameters_but_unknown_catalog_is_rejected(tmp_path,legacy_hash):
    lab=PhysicsLab('pendulum'); lab.set_parameter('length',1.4)
    old=lab.configuration(); old['catalog_hash']=legacy_hash
    path=tmp_path/'old.json'; path.write_text(json.dumps(old),encoding='utf8')
    restored=PhysicsLab(); restored.load(path)
    assert restored.params==lab.params and restored.time==0 and not restored.running
    assert restored.snapshot()['model']['revision']==3
    before=restored.configuration(); old['catalog_hash']='0'*64; path.write_text(json.dumps(old),encoding='utf8')
    with pytest.raises(ValueError): restored.load(path)
    assert restored.configuration()==before


@pytest.mark.parametrize('seconds',(0.,.05))
def test_csv_final_matches_json_after_live_force_edit_at_existing_sample_time(tmp_path,seconds):
    lab=PhysicsLab(); evolve(lab,seconds)
    assert lab.samples[-1]['time_s']==lab.time
    lab.set_parameter('force',17.)
    folder=lab.export(tmp_path/'export')
    final=json.loads((folder/'experiment.json').read_text(encoding='utf8'))['final']
    assert lab.snapshot()['samples'][-1]==final
    with (folder/'measurements.csv').open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    assert float(rows[-1]['applied_n'])==final['applied_n']
    assert float(rows[-1]['acceleration_m_s2'])==final['acceleration_m_s2']


def test_force_challenge_rejects_transient_turnaround_as_a_stationary_stop():
    lab=PhysicsLab(); lab.params.update(mass=1.,gravity=10.,mu_s=.4,mu_k=.2,force=10.)
    lab.reset(); lab.challenge=True
    evolve(lab,.6); lab.set_parameter('force',-10.); evolve(lab,.5)
    assert not lab.achieved  # The object turns around in the target zone; it never sticks.


def test_force_challenge_accepts_a_genuine_static_stop_in_target_zone():
    lab=PhysicsLab(); lab.params.update(mass=1.,gravity=10.,mu_s=.4,mu_k=.2,force=10.)
    lab.reset(); lab.challenge=True
    evolve(lab,.5); lab.set_parameter('force',-2.); evolve(lab,1.2)
    assert lab.achieved and lab.q==pytest.approx([3.,0.],abs=1e-10)


def test_force_edit_updates_existing_event_sample_and_snapshot_does_not_mutate_history():
    lab=PhysicsLab(); lab.set_parameter('force',17.); evolve(lab,.05)
    assert lab.samples[0]['applied_n']==17.
    history=[row.copy() for row in lab.samples]
    evolve(lab,.01); before=[row.copy() for row in lab.samples]
    snapshot=lab.snapshot()
    assert snapshot['samples'][-1]==snapshot['final']
    assert list(lab.samples)==before
    snapshot['samples'][0]['applied_n']=-99.
    assert list(lab.samples)==before and before[0]==history[0]


def test_force_challenge_rejects_short_travel_from_a_nearby_initial_position():
    lab=PhysicsLab(); lab.params.update(position0=1.5,mass=1.,gravity=10.,mu_s=.4,mu_k=.2,force=10.)
    lab.reset(); lab.challenge=True
    evolve(lab,.25); lab.set_parameter('force',-2.); evolve(lab,.8)
    assert lab.q==pytest.approx([2.25,0.],abs=1e-10)
    assert not lab.achieved  # Only .75 m forward, despite a real stop in the zone.


def test_force_challenge_accepts_two_meter_travel_starting_at_zone_boundary():
    lab=PhysicsLab(); lab.params.update(position0=2.,mass=1.,gravity=10.,mu_s=.2,mu_k=.2,force=4.)
    lab.reset(); lab.challenge=True
    evolve(lab,1.); lab.set_parameter('force',0.); evolve(lab,1.1)
    assert lab.q==pytest.approx([4.,0.],abs=1e-10)
    assert lab.achieved
