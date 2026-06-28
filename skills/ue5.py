import json
import httpx
from skills.base import NedsterSkill

class UE5ImportFBX(NedsterSkill):
    name = "ue5_import_fbx"
    description = "Import an FBX file (e.g. built from Blender) into an open UE5 project via Remote Control."
    parameters = {
        "type": "object",
        "properties": {
            "source_fbx_path": {"type": "string"},
            "destination_game_path": {"type": "string", "default": "/Game/VFXStudio/Imports"},
        },
        "required": ["source_fbx_path"],
    }

    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        self.base_url = f"http://{host}:{port}/remote/object"

    async def run(self, source_fbx_path: str, destination_game_path: str = "/Game/VFXStudio/Imports") -> dict:
        payload = {
            "objectPath": "/Script/UnrealEd.Default__AutomatedAssetImportData",
            "functionName": "InitializeImportData",
            "parameters": {"Filenames": [source_fbx_path], "DestinationPath": destination_game_path},
            "generateTransaction": True,
        }
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.put(self.base_url, json=payload)
            if resp.status_code == 200:
                return {"status": "success", "data": resp.json()}
            return {"status": "error", "code": resp.status_code, "msg": resp.text}
        except httpx.ConnectError:
            return {"status": "offline", "msg": "UE5 Remote Control plugin not reachable on port 8080."}
