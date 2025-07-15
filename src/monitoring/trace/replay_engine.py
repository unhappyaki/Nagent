import time

class ReplayEngine:
    def __init__(self, step_delay=0.5):
        self.step_delay = step_delay

    def replay(self, snapshot, trace_events, step_by_step=False, verbose=True):
        print(f"[Replay] Session: {snapshot.get('session_id')}, Trace: {snapshot.get('trace_id')}")
        for i, event in enumerate(trace_events):
            if verbose:
                print(f"Step {i+1}: [{event['event_type']}] @ {event['timestamp']}")
                print(f"  Payload: {event['payload']}")
            if step_by_step:
                input("Press Enter for next step...")
            else:
                time.sleep(self.step_delay)
        print("[Replay End]")

    def replay_prompt(self, snapshot):
        prompt = snapshot.get("prompt")
        print("[Prompt Replay]")
        print(prompt)
        return prompt 