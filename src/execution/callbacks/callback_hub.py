from .callback_handler import CallbackHandler
from .tool_result import ToolResult
from .callback_context import CallbackContext
from .callback_policy import CallbackPolicy
from .policy_resolver import PolicyResolver
from typing import Any

class CallbackHub:
    """
    回调中台，统一调度回调相关组件
    """
    def __init__(self, handler: CallbackHandler, fallback, trace_writer, runtime, policy_resolver: PolicyResolver):
        self.handler = handler
        self.fallback = fallback
        self.trace = trace_writer
        self.runtime = runtime
        self.policy_resolver = policy_resolver

    async def process(self, result: ToolResult, context: CallbackContext) -> Any:
        try:
            policy = self.policy_resolver.resolve(result, vars(context))
            decision = await self.handler.handle_callback_with_policy(result, context, policy)
            self.trace.record(context.trace_id, "CALLBACK_SUCCESS", {"next": policy.trigger_next})
            if policy.trigger_next:
                return await self.runtime.executor.run_next_step(decision.next_action if hasattr(decision, 'next_action') else None)
            return decision
        except Exception as e:
            self.trace.record(context.trace_id, "CALLBACK_FAIL", {"reason": str(e)})
            return await self.fallback.invoke(result) 