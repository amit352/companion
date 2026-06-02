from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/")
async def list_plugins(request: Request):
    engine = request.app.state.engine
    return {"plugins": engine.plugin_manager.list_plugins()}


@router.get("/types")
async def list_plugin_types():
    from feature_graph.sdk.base.plugin_base import PluginType
    return {"types": [t.value for t in PluginType]}
