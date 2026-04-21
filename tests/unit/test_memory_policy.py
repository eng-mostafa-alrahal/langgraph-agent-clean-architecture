from app.modules.agent_orchestration.domain.memory_policy import (
    should_summarize_messages,
    summary_cut_index,
)


def test_should_summarize_messages_respects_threshold_and_keep_window() -> None:
    assert not should_summarize_messages(
        20,
        trigger_threshold=40,
        keep_recent_messages=12,
    )
    assert should_summarize_messages(
        41,
        trigger_threshold=40,
        keep_recent_messages=12,
    )


def test_should_summarize_messages_rejects_invalid_policy() -> None:
    assert not should_summarize_messages(100, trigger_threshold=0, keep_recent_messages=12)
    assert not should_summarize_messages(100, trigger_threshold=40, keep_recent_messages=0)


def test_summary_cut_index_keeps_recent_window() -> None:
    assert summary_cut_index(45, keep_recent_messages=12) == 33
    assert summary_cut_index(8, keep_recent_messages=12) == 0
