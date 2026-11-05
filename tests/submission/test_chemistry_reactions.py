"""Tests for the 10 interactive chemical reactions."""
from pathlib import Path
import json
import numpy as np
import pytest
import pygame
import yaml

from submission.stem_ui.chemistry import ChemistryScene, load_reactions
from submission.stem_ui.chemistry_input import ChemistryInput
from test_stem_ui import SETTINGS


def test_all_10_reactions_data_valid():
    reactions = load_reactions()
    assert len(reactions) == 10
    required_fields = ['id', 'name', 'equation', 'equation_display', 'type',
                       'description', 'phenomenon', 'reactants_label',
                       'products_label', 'scene_layout']
    for rid, r in reactions.items():
        for field in required_fields:
            assert field in r, f"Reaction {rid} missing {field}"
        assert 'reactants' in r['scene_layout']
        assert 'products' in r['scene_layout']
        assert len(r['scene_layout']['reactants']) > 0
        assert len(r['scene_layout']['products']) > 0


def test_scene_load_and_trigger_all_10_reactions():
    scene = ChemistryScene(SETTINGS)
    reactions = scene.reactions
    assert len(reactions) == 10

    for rid in reactions:
        # 1. Load reactants
        loaded = scene.load_reaction(rid)
        assert loaded is True
        assert scene.current_reaction == rid
        assert scene.reaction_state == 'reactants'
        assert len(scene.atoms) > 0
        assert len(scene.bonds) > 0
        reactant_atom_count = len(scene.atoms)

        # 2. Trigger reaction -> products
        triggered = scene.trigger_reaction()
        assert triggered is True
        assert scene.reaction_state == 'products'
        assert len(scene.atoms) > 0
        assert reactions[rid]['phenomenon'] in scene.message

        # 3. Reset reaction -> back to reactants
        reset = scene.reset_reaction()
        assert reset is True
        assert scene.reaction_state == 'reactants'
        assert len(scene.atoms) == reactant_atom_count


def test_chemistry_input_reactions_commands():
    scene = ChemistryScene(SETTINGS)
    inp = ChemistryInput(scene, SETTINGS)

    # Navigate to reactions page
    inp.command('reactions')
    assert inp.page == 'reactions'
    assert inp.reaction_page == 0

    # Test pagination
    inp.command('reactions_next')
    assert inp.reaction_page == 1
    inp.command('reactions_next')
    assert inp.reaction_page == 1  # Clamped to max pages
    inp.command('reactions_prev')
    assert inp.reaction_page == 0

    # Test selecting a reaction
    inp.command('reaction:r01_h2_o2')
    assert scene.current_reaction == 'r01_h2_o2'
    assert scene.reaction_state == 'reactants'

    # Test triggering reaction
    inp.command('trigger_reaction')
    assert scene.reaction_state == 'products'

    # Test reset reaction
    inp.command('reset_reaction')
    assert scene.reaction_state == 'reactants'


def test_reactions_page_rendering():
    pygame.font.init()
    from submission.stem_ui.chemistry_view import CameraChemistryView
    from types import SimpleNamespace

    renderer_mock = SimpleNamespace(size=(1360, 860), help_visible=True, fonts={},
                                    unit_sphere=1, unit_bone=2)
    view = CameraChemistryView(SETTINGS, renderer_mock)
    # Load reaction and render panel
    view.scene.load_reaction('r01_h2_o2')
    view.input.command('reactions')
    panel, surface = view._panel()
    assert panel is not None
    assert surface is not None
    assert surface.get_width() > 0
    # Check action targets exist on panel
    actions = [act for rect, act in panel.targets]
    assert 'reaction:r01_h2_o2' in actions
    assert 'trigger_reaction' in actions
    assert 'reset_reaction' in actions
    assert 'reactions_prev' in actions
    assert 'reactions_next' in actions
