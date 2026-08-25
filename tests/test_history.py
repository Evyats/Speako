from speako.history import MAX_HISTORY, load_recent_recordings, save_recording


def test_most_recent_recording_is_listed_first(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    save_recording({"status": "completed", "final_output": "first"})
    save_recording({"status": "completed", "final_output": "second"})
    assert load_recent_recordings() == [
        {"status": "completed", "final_output": "second"},
        {"status": "completed", "final_output": "first"},
    ]


def test_history_is_capped_at_max_history(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    for i in range(MAX_HISTORY + 2):
        save_recording({"status": "completed", "final_output": str(i)})
    records = load_recent_recordings()
    assert len(records) == MAX_HISTORY
    assert [r["final_output"] for r in records] == ["4", "3", "2"]
