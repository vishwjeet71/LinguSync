import httpx, asyncio, os, json, time
from platformdirs import PlatformDirs

from fastapi import Response, status

APP_NAME = "com.vishwjeet.lingusync"
dirs = PlatformDirs(appname=APP_NAME, appauthor=False)


def handleRequest(modelName: str, fileName: str, response: Response):
    manifest_file_path = str(dirs.user_data_path) + "/models_manifest.json"
    isRemoval = None

    if not os.path.exists(manifest_file_path):
        response.status_code = status.HTTP_404_NOT_FOUND
        return {
            "CM": "Model manifest file not found.",
            "UM": "Model information file is missing.",
        }

    isRemoval = inverse_file_status(modelName, fileName)
    if isRemoval:

        try:

            # File removing logic
            inverse_file_status(modelName, fileName, inverse=True)
            return {"status": "ok"}

        except Exception as E:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return {
                "CM": f"Failed to remove file '{fileName}'. Error: {e}",
                "UM": f"Unable to remove '{fileName}' from {modelName}.",
            }

    try:
        # Downloading logic
        time.sleep(2)
        inverse_file_status(modelName, fileName, inverse=True)
        return {"status": "ok"}

    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "CM": f"Failed to download '{fileName}'. Error: {e}",
            "UM": f"Unable to download '{fileName}'. Please try again.",
        }


def inverse_file_status(modelName: str, fileName: str, inverse: bool = False):

    manifest_file_path = str(dirs.user_data_path) + "/models_manifest.json"

    with open(manifest_file_path, "r") as f:
        manifest = json.load(f)

    for mld in manifest.values():

        for mtd in mld.values():

            if mtd.get("name") == modelName:
                req_files = mtd.get("requiredFiles", {})

                if fileName in req_files:
                    if inverse:
                        req_files[fileName] = not req_files[fileName]

                        with open(manifest_file_path, "w") as f:
                            json.dump(manifest, f, indent=4)

                    return req_files[fileName]
