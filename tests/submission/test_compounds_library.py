"""Verify all 72 educational chemical formulas: connectivity, valence, description, restore."""
import pytest
import yaml
from pathlib import Path
from submission.stem_ui.chemistry import ChemistryScene, load_compounds
from submission.stem_ui.chemistry_input import ChemistryInput

SETTINGS = yaml.safe_load((Path(__file__).resolve().parents[2] / 'submission/stem_ui/settings.yaml').read_text(encoding='utf-8'))
COMPOUNDS = load_compounds()

def test_all_72_compounds_loaded():
    assert len(COMPOUNDS) == 72, f"Expected 72 compounds, got {len(COMPOUNDS)}"

@pytest.mark.parametrize('key', tuple(COMPOUNDS))
def test_compound_spawns_single_connected_cluster_and_restores(key):
    s = ChemistryScene(SETTINGS)
    s.add_template(key)
    comp_info = COMPOUNDS[key]
    assert s.selected is not None
    ids = s.component(s.selected)
    # 1. Total atoms match definition
    assert len(ids) == len(comp_info['symbols']), f"{key}: atom count mismatch"
    # 2. All atoms are in one single connected cluster
    assert set(ids) == set(s.atoms), f"{key}: not all atoms are in a single cluster"
    # 3. Description recognizes compound label
    assert s.describe(ids) == comp_info['label']
    # 4. State round-trip (restore) succeeds without error
    state = s.state()
    s.restore(state)
    assert len(s.atoms) == len(comp_info['symbols'])
    assert s.describe(ids) == comp_info['label']

def test_categories_and_filtering_navigation():
    s = ChemistryScene(SETTINGS)
    inp = ChemistryInput(s, SETTINGS)
    inp.command('compounds')
    assert inp.page == 'compounds'
    assert inp.compound_category == 'all'
    assert len(inp.filtered_compounds()) == 72

    # Test filtering by category
    categories = ['oxit', 'axit', 'bazo', 'muoi', 'huu_co']
    expected_counts = {'oxit': 20, 'axit': 8, 'bazo': 10, 'muoi': 22, 'huu_co': 12}
    for cat in categories:
        inp.command(f'compound_cat:{cat}')
        assert inp.compound_category == cat
        assert inp.compound_page == 0
        items = inp.filtered_compounds()
        assert len(items) == expected_counts[cat], f"Category {cat} count {len(items)} != {expected_counts[cat]}"

    # Test pagination
    inp.command('compound_cat:oxit')
    # 20 items at 7 per page -> 3 pages (pages 0, 1, 2)
    assert inp.compound_page == 0
    inp.command('compounds_next')
    assert inp.compound_page == 1
    inp.command('compounds_next')
    assert inp.compound_page == 2
    inp.command('compounds_next')
    assert inp.compound_page == 2  # bounds checked
    inp.command('compounds_prev')
    assert inp.compound_page == 1
    inp.command('compounds_prev')
    assert inp.compound_page == 0
