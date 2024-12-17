# pylint: disable=protected-access
import logging

from opentelemetry.trace import Tracer

from monocle_apptrace.instrumentation.common.span_handler import SpanHandler
from monocle_apptrace.instrumentation.common.utils import (
    get_fully_qualified_class_name,
    with_tracer_wrapper,
)

logger = logging.getLogger(__name__)


@with_tracer_wrapper
def task_wrapper(tracer: Tracer, handler: SpanHandler,to_wrap, wrapped, instance, args, kwargs):

    # Some Langchain objects are wrapped elsewhere, so we ignore them here
    if instance.__class__.__name__ in ("AgentExecutor"):
        return wrapped(*args, **kwargs)

    if hasattr(instance, "name") and instance.name:
        name = f"{to_wrap.get('span_name')}.{instance.name.lower()}"
    elif to_wrap.get("span_name"):
        name = to_wrap.get("span_name")
    else:
        name = get_fully_qualified_class_name(instance)

    handler.validate(to_wrap, wrapped, instance, args, kwargs)
    handler.set_context_properties(to_wrap, wrapped, instance, args, kwargs)
    with tracer.start_as_current_span(name) as span:
        handler.pre_task_processing(to_wrap, wrapped, instance, args, span)
        return_value = wrapped(*args, **kwargs)
        handler.hydrate_span(to_wrap, wrapped, instance, args, kwargs, return_value, span)
        handler.post_task_processing(to_wrap, wrapped, instance, args, kwargs, return_value, span)

    return return_value


@with_tracer_wrapper
async def atask_wrapper(tracer: Tracer, handler: SpanHandler, to_wrap, wrapped, instance, args, kwargs):
    """Instruments and calls every function defined in TO_WRAP."""

    # Some Langchain objects are wrapped elsewhere, so we ignore them here
    if instance.__class__.__name__ in ("AgentExecutor"):
        return wrapped(*args, **kwargs)

    if hasattr(instance, "name") and instance.name:
        name = f"{to_wrap.get('span_name')}.{instance.name.lower()}"
    elif to_wrap.get("span_name"):
        name = to_wrap.get("span_name")
    else:
        name = get_fully_qualified_class_name(instance)

    handler.validate(to_wrap, wrapped, instance, args, kwargs)
    handler.set_context_properties(to_wrap, wrapped, instance, args, kwargs)
    with tracer.start_as_current_span(name) as span:
        handler.pre_task_processing(to_wrap, wrapped, instance, args, span)
        return_value = wrapped(*args, **kwargs)
        handler.hydrate_span(to_wrap, wrapped, instance, args, kwargs, return_value, span)
        handler.post_task_processing(to_wrap, wrapped, instance, args, kwargs, return_value, span)

    return return_value