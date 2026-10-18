"""Analytic and conservation checks for bounded SI teaching models."""
import json
import math
import pytest
import yaml
from submission.stem_ui import physics
from submission.stem_ui.physics import PhysicsLab,load_catalog


def simulate(model,seconds):
    for _ in range(round(seconds/model.engine['fixed_dt_s'])): model.step()


def test_catalog_has_eight_bounded_experiments_and_primary_sources():
    data=load_catalog()
    assert len(data['labs'])==8 and len(data['sources'])>=6
    assert all(l['assumptions'] and l['formula'] and l['challenge'] for l in data['labs'].values())


def test_static_friction_holds_and_exceeding_static_limit_starts_motion():
    lab=PhysicsLab(); lab.params.update(mass=2,gravity=10,mu_s=.4,mu_k=.2,force=8); lab.reset()
    simulate(lab,1); assert lab.q==[0,0]
    lab.set_parameter('force',10); simulate(lab,1)
    assert lab.q==pytest.approx([1.5,3])
    assert lab.metrics()['balance_j']==pytest.approx(0,abs=1e-10)


def test_friction_stops_without_oscillating_or_reversing_at_zero():
    lab=PhysicsLab(); lab.params.update(force=0,mass=1,gravity=10,mu_s=.4,mu_k=.2); lab.reset(); lab.q=[0,1]
    lab.initial_energy=.5; simulate(lab,2)
    assert lab.q==pytest.approx([.25,0],abs=1e-10)
    assert lab.metrics()['thermal_j']==pytest.approx(.5)
    assert lab.metrics()['balance_j']==pytest.approx(0,abs=1e-10)


def test_opposing_force_can_stop_then_reverse_with_correct_work():
    lab=PhysicsLab(); lab.params.update(force=-10,mass=1,gravity=10,mu_s=.4,mu_k=.2); lab.reset(); lab.q=[0,1]
    lab.initial_energy=.5; simulate(lab,1)
    assert lab.q[1]<0 and lab.metrics()['thermal_j']>=0
    assert lab.metrics()['balance_j']==pytest.approx(0,abs=1e-9)


def test_incline_without_friction_matches_newtons_law_and_energy_work():
    lab=PhysicsLab('incline'); lab.params.update(force=0,angle=30,gravity=10,mu_s=0,mu_k=0); lab.reset()
    simulate(lab,1)
    assert lab.q==pytest.approx([-2.5,-5])
    assert lab.metrics()['balance_j']==pytest.approx(0,abs=1e-9)


@pytest.mark.parametrize('mass',(.1,1,5))
def test_projectile_lands_at_analytic_time_range_and_energy(mass):
    lab=PhysicsLab('projectile'); lab.params.update(mass=mass,height=0,speed=10,angle=30,gravity=10); lab.reset()
    simulate(lab,2)
    assert lab.finished and lab.time==pytest.approx(1,abs=1e-10)
    assert lab.q[0]==pytest.approx(5*math.sqrt(3),abs=1e-10)
    assert lab.q[1]==0 and lab.metrics()['balance_j']==pytest.approx(0,abs=1e-9)


def test_zero_speed_is_free_fall_not_a_required_throw_gesture():
    lab=PhysicsLab('projectile'); lab.params.update(speed=0,height=5,gravity=10); lab.reset(); simulate(lab,2)
    assert lab.time==pytest.approx(1) and lab.q[:2]==pytest.approx([0,0])


@pytest.mark.parametrize('elasticity',(0,.3,1))
@pytest.mark.parametrize('mass1,mass2',((1,1),(2,5)))
def test_collision_conserves_momentum_and_accounts_for_energy_loss(elasticity,mass1,mass2):
    lab=PhysicsLab('collision'); lab.params.update(mass=mass1,mass2=mass2,velocity1=2,velocity2=-1,restitution=elasticity); lab.reset()
    before=lab.metrics(); simulate(lab,2); after=lab.metrics()
    assert lab.collided and lab.q[1]-lab.q[0]>=.4-1e-9
    assert after['momentum_kg_m_s']==pytest.approx(before['momentum_kg_m_s'])
    assert lab.q[3]-lab.q[2]==pytest.approx(elasticity*3)
    assert after['balance_j']==pytest.approx(0,abs=1e-10)
    assert after['thermal_j']>=-1e-12


@pytest.mark.parametrize('damping',(0,1,10))
def test_spring_energy_and_dissipation_are_integrated_consistently(damping):
    lab=PhysicsLab('spring'); lab.params['damping']=damping; lab.reset(); simulate(lab,5)
    assert lab.metrics()['balance_j']==pytest.approx(0,abs=1e-5)
    assert lab.q[2]>=0
    if damping: assert abs(lab.q[0])<abs(lab.params['displacement'])


def test_small_pendulum_period_is_measured_not_assumed_from_formula():
    lab=PhysicsLab('pendulum'); lab.params.update(angle=5,damping=0); lab.reset(); simulate(lab,6)
    assert lab.period is not None
    assert lab.period==pytest.approx(lab.metrics()['period_small_s'],rel=.001)
    assert lab.metrics()['balance_j']==pytest.approx(0,abs=1e-7)


def test_large_pendulum_angle_uses_nonlinear_equation():
    lab=PhysicsLab('pendulum'); lab.params['angle']=80; lab.reset(); simulate(lab,8)
    assert lab.period>lab.metrics()['period_small_s']*1.1
    assert lab.metrics()['balance_j']==pytest.approx(0,abs=1e-6)


def test_lever_equilibrium_and_pulley_work_relationship():
    lever=PhysicsLab('lever'); assert lever.metrics()['torque_net_nm']==pytest.approx(0)
    lever.set_parameter('arm2',2); assert lever.metrics()['torque_net_nm']<0
    pulley=PhysicsLab('pulley'); pulley.set_parameter('strands',3); pulley.set_parameter('pull',6)
    m=pulley.metrics(); assert m['height_m']==2
    assert m['required_n']==pytest.approx(pulley.params['mass']*pulley.params['gravity']/3)
    assert m['work_j']==pytest.approx(m['potential_j'])
    assert m['balance_j']==pytest.approx(0)


def test_fixed_steps_do_not_depend_on_render_partition_or_pause_debt():
    a,b=PhysicsLab('spring'),PhysicsLab('spring'); a.running=b.running=True
    for _ in range(120): a.advance(1/60)
    for _ in range(40): b.advance(.05)
    assert a.time==pytest.approx(b.time) and a.q==pytest.approx(b.q)
    a.running=False; state=a.q.copy(); a.advance(100); assert a.q==state
    a.running=True; a.advance(10); assert a.discarded_wall_s==pytest.approx(9.9)


def test_comparison_keeps_independent_initial_conditions_inputs_and_rows():
    lab=PhysicsLab(); simulate(lab,1); lab.keep_reference()
    a=lab.reference; lab.set_parameter('mass',3); simulate(lab,1)
    assert a['configuration']['params']['mass']==2 and a['final']['time_s']==pytest.approx(1)
    assert lab.comparison()['changed']==['Khối lượng']
    assert lab.comparison()['same_duration']


@pytest.mark.parametrize('invalid',(float('nan'),float('inf'),True))
def test_invalid_values_rejected_without_mutation(invalid):
    lab=PhysicsLab(); before=lab.configuration()
    with pytest.raises(ValueError): lab.set_parameter('mass',invalid)
    assert lab.configuration()==before


def test_save_load_export_and_invalid_load_are_transactional(tmp_path):
    lab=PhysicsLab('spring'); lab.set_parameter('mass',2); lab.challenge=True
    setup=tmp_path/'setup.json'; lab.save(setup); other=PhysicsLab(); other.load(setup)
    assert other.configuration()==lab.configuration()
    simulate(lab,1); folder=lab.export(tmp_path/'output')
    assert len((folder/'measurements.csv').read_text(encoding='utf-8-sig').splitlines())>2
    assert json.loads((folder/'experiment.json').read_text(encoding='utf-8'))['initial_params']['mass']==2
    data=other.configuration(); data['params']['mass']=float('nan'); setup.write_text(json.dumps(data))
    before=other.configuration()
    with pytest.raises(ValueError): other.load(setup)
    assert other.configuration()==before


@pytest.mark.parametrize('name',tuple(load_catalog()['labs']))
@pytest.mark.parametrize('boundary',(2,3))
def test_allowed_extreme_parameters_remain_finite_and_bounded_in_history(name,boundary):
    lab=PhysicsLab(name)
    for key,spec in lab.spec['params'].items(): lab.set_parameter(key,spec[boundary])
    simulate(lab,2)
    assert all(math.isfinite(v) for v in lab.q)
    assert all(value is None or math.isfinite(value) for value in lab.metrics().values())
    assert len(lab.samples)<=lab.engine['max_samples']


def test_projectile_timeout_does_not_report_ground_impact_or_a_hit():
    lab=PhysicsLab('projectile'); lab.params.update(speed=15,angle=90,height=5,gravity=1); lab.reset()
    simulate(lab,31)
    assert lab.finished and not lab.landed and lab.q[1]>0 and lab.metrics()['target_error_m'] is None


def test_live_force_changes_are_preserved_and_distinguished_in_comparison():
    lab=PhysicsLab(); simulate(lab,.5); lab.set_parameter('force',12); simulate(lab,.5); lab.keep_reference()
    lab.reset(); simulate(lab,1)
    assert lab.comparison()['live_inputs_differ']
    assert lab.reference['inputs'][0]['time_s']==pytest.approx(.5)


@pytest.mark.parametrize('bad_step',(0,-1,1e-12,float('nan')))
def test_catalog_rejects_invalid_or_unbounded_integrator_before_opening_ui(tmp_path,monkeypatch,bad_step):
    data=load_catalog(); data['engine']['fixed_dt_s']=bad_step
    path=tmp_path/'physics.yaml'; path.write_text(yaml.safe_dump(data),encoding='utf8')
    monkeypatch.setattr(physics,'CATALOG_PATH',path)
    with pytest.raises(ValueError): load_catalog()
