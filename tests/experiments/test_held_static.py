from experiments.round2.held_static import manifest_payload


def test_supported_hand_manifest_preserves_frozen_comparison(tmp_path):
    plan = manifest_payload(tmp_path)
    assert plan["profiles"] == ["f0", "f1", "f2"]
    assert plan["primary_metric"] == "radial_rms_jitter"
    assert plan["analysis_window"] == {"start_s": 2.0, "end_s": 10.0}
    assert len(plan["trials"]) == 3
    assert all(trial["source"].startswith(str(tmp_path)) for trial in plan["trials"])
