"""
Models list endpoint
"""

from starlette.requests import Request
from starlette.responses import JSONResponse

from .bootstrap import env
from .core import check, parse_routing_rule
from .config import ModelListingMode, Group


async def models(request: Request) -> JSONResponse:
    """
    Lists available models based on routing rules and group permissions.
    """
    group_name, api_key = await check(request)
    group: Group = env.config.groups[group_name]
    models = list()
    for model_pattern, route in env.config.routing.items():
        connection_name, _ = parse_routing_rule(route, env.config)
        if group.allows_connecting_to(connection_name):
            is_model_name = not ("*" in model_pattern or "?" in model_pattern)
            if not is_model_name:
                if env.config.model_listing_mode != ModelListingMode.AS_IS:
                    if (
                        env.config.model_listing_mode
                        == ModelListingMode.IGNORE_WILDCARDS
                    ):
                        continue
                    else:
                        raise NotImplementedError(
                            f"'{env.config.model_listing_mode}' model listing mode "
                            f"is not implemented yet"
                        )
            models.append(
                dict(
                    id=model_pattern,
                    object="model",
                    created=0,
                    owned_by=connection_name,
                )
            )

    return JSONResponse(
        {
            "object": "list",
            "data": models,
        }
    )
