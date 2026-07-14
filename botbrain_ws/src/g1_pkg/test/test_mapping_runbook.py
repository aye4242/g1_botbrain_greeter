from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
RUNBOOK_PATH = PROJECT_ROOT / "机器人项目run.md"


def _runbook():
    return RUNBOOK_PATH.read_text(encoding="utf-8")


def test_mapping_runbook_uses_current_install_and_launch_paths():
    source = _runbook()

    assert "/botbrain_ws/tools/mapping/shift_pcd_z.py" not in source
    assert "/botbrain_ws/install/g1_pkg/lib/g1_pkg/shift_pcd_z.py" in source
    assert "/botbrain_ws/start_localization.sh" not in source
    assert "grid_map_file:=" in source


def test_mapping_runbook_documents_safe_save_and_editor_semantics():
    source = _runbook()

    assert "docker compose stop -t 120 fast_lio" in source
    assert "左键**画黑" in source
    assert "右键**画白" in source
    assert "当前不会影响 Nav2" in source
    assert "mode: trinary" in source


def test_mapping_runbook_has_balanced_markdown_fences():
    assert sum(line.startswith("```") for line in _runbook().splitlines()) % 2 == 0
