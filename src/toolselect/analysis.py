"""解析ツールの実行口。選択の評価グラフからは呼ばない。"""


class AnalysisNotApproved(PermissionError):
    pass


def execute_analysis(tool_ids: list[str], approved: bool) -> dict:
    if not approved:
        raise AnalysisNotApproved("ユーザーの承認前に解析ツールは実行できない")
    return {
        "executed": False,
        "planned_tool_ids": list(tool_ids),
        "reason": "この評価システムは解析ツールを起動しない。承認後も実行計画を返すだけである。",
    }
