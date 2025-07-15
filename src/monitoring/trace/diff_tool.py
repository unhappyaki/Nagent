import difflib
import json

class DiffTool:
    @staticmethod
    def diff_snapshots(snap_a, snap_b):
        # 对比两个快照（dict），输出结构化差异
        a_str = json.dumps(snap_a, sort_keys=True, indent=2, ensure_ascii=False)
        b_str = json.dumps(snap_b, sort_keys=True, indent=2, ensure_ascii=False)
        diff = list(difflib.unified_diff(a_str.splitlines(), b_str.splitlines(), lineterm=""))
        return diff

    @staticmethod
    def diff_traces(trace_a, trace_b):
        # trace为list[dict]
        a_str = json.dumps(trace_a, sort_keys=True, indent=2, ensure_ascii=False)
        b_str = json.dumps(trace_b, sort_keys=True, indent=2, ensure_ascii=False)
        diff = list(difflib.unified_diff(a_str.splitlines(), b_str.splitlines(), lineterm=""))
        return diff

    @staticmethod
    def diff_memory(mem_a, mem_b):
        # memory为list[dict]
        a_str = json.dumps(mem_a, sort_keys=True, indent=2, ensure_ascii=False)
        b_str = json.dumps(mem_b, sort_keys=True, indent=2, ensure_ascii=False)
        diff = list(difflib.unified_diff(a_str.splitlines(), b_str.splitlines(), lineterm=""))
        return diff 