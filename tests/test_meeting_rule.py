import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from models.item import PanelPart
from core.panel_rules import apply_meeting_rule, role_of


def _p(comp, t, ptype="LND-PLY-E0-12", faces=0):
    return PanelPart("p", comp, ptype, 100, 100, t, 1, faces)


def test_roles():
    assert role_of("Drawer box side") == "ply" and role_of("Drawer bottom") == "ply"
    assert role_of("Back panel") == "ply" and role_of("Internal dividers") == "divider"
    assert role_of("Door MDF veneer 18") == "door" and role_of("Drawer face") == "face"
    assert role_of("Side panel") == "side" and role_of("Top panel") is None


def test_side_panel_is_mdf_one_face():
    p = apply_meeting_rule(_p("Side panel", 12, "LND-PLY-E0-12-MSF", 1))
    assert (p.panel_type, p.exposed_faces) == ("LND-MDF-E0-12-MSF", 1)


def test_door_is_mdf_two_faces():
    p = apply_meeting_rule(_p("Door", 18, "LND-PLY-E0-18-MDF", 2))
    assert (p.panel_type, p.exposed_faces) == ("LND-MDF-E0-18-MDF", 2)


def test_drawer_face_is_mdf_one_face():
    p = apply_meeting_rule(_p("Drawer front", 18, "LND-MDF-E0-18-MDF", 2))
    assert (p.panel_type, p.exposed_faces) == ("LND-MDF-E0-18-MSF", 1)


def test_drawer_box_stays_raw_plywood():
    p = apply_meeting_rule(_p("Drawer box front/back", 12, "LND-MDF-E0-12", 0))
    assert (p.panel_type, p.exposed_faces) == ("LND-PLY-E0-12", 0)


def test_back_panel_plywood_keeps_faces():
    p = apply_meeting_rule(_p("Back panel", 9, "LND-MDF-E0-9", 1))
    assert (p.panel_type, p.exposed_faces) == ("LND-PLY-E0-9-MSF", 1)


def test_top_untouched_and_idempotent():
    p = apply_meeting_rule(_p("Top panel", 18, "LND-MDF-E0-18-MSF", 1))
    assert p.panel_type == "LND-MDF-E0-18-MSF" and "[MEETING]" not in p.note
    q = apply_meeting_rule(_p("Door", 18, "LND-PLY-E0-18-MDF", 2)); n = q.note
    apply_meeting_rule(q)
    assert q.note == n


def test_odd_thickness_left_alone_and_flagged():
    p = apply_meeting_rule(_p("Side panel", 20, "LND-MDF-E0-18-MSF", 1))
    assert p.panel_type == "LND-MDF-E0-18-MSF" and "tidak ada di tabel" in p.note


def test_label_warning_silenced_when_meeting_rule_applied():
    from core.panel_rules import check_panel
    # drawing label B-12-1X says plywood, but the meeting rule makes a side panel MDF veneer
    p = PanelPart("/ B-12-1X", "SIDE PANEL", "LND-MDF-E0-12-MSF", 100, 100, 12, 1, 1)
    assert any("implies" in m for m in check_panel(p))          # before the rule: conflict is reported
    apply_meeting_rule(p)
    assert p.panel_type == "LND-MDF-E0-12-MSF"
    assert not any("implies" in m for m in check_panel(p))      # after: the meeting rule wins, no warning


def test_divider_veneer_only_on_visible_faces():
    for faces, suffix in ((0, ""), (1, "-MSF"), (2, "-MDF")):
        p = PanelPart("/ X", "Internal dividers", "LND-MDF-E0-18-MSF", 100, 100, 18, 1, faces)
        apply_meeting_rule(p)
        assert p.panel_type == "LND-PLY-E0-18" + suffix, (faces, p.panel_type)
        assert p.exposed_faces == faces


def test_drawer_divider_post_not_treated_as_divider_panel():
    from core.panel_rules import role_of
    assert role_of("Drawer divider post") != "divider"
