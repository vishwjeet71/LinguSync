import httpx, asyncio, os, json, time, uuid
from platformdirs import PlatformDirs
from pathlib import Path

APP_NAME = "com.vishwjeet.lingusync"
dirs = PlatformDirs(appname=APP_NAME, appauthor=False)


def get_file_credentials(file_name: str, model_name: str):
    manifest_file_path = str(dirs.user_data_path) + "/models_manifest.json"

    if not os.path.exists(manifest_file_path):
        raise FileNotFoundError(f"models manifest Not found on {manifest_file_path}")

    url = None
    file_name = file_name
    relative_path = f"models/{model_name}/{file_name}"

    try:
        manifest = json.load(open(manifest_file_path))

        for mld in manifest.values():

            for mtd in mld.values():

                if mtd.get("name") == model_name:
                    download_link = mtd.get("downloadLink")

                    if isinstance(download_link, list):
                        if file_name == "decoder_model.pt":
                            url = mtd.get("downloadLink")[1]

                            return url, file_name, relative_path

                        else:
                            url = f"{download_link[0]}{file_name}"
                            return url, file_name, relative_path

                    url = f"{download_link}{file_name}"
                    return url, file_name, relative_path

    except Exception as e:
        print(f"Unable to extract credentials: {e}")
        return None, None, None


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


class DownloadManager:

    def __init__(self, download_dir: str):
        self.download_dir = Path(download_dir).resolve()
        self.download_dir.mkdir(parents=True, exist_ok=True)

        self.client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(connect=30, read=120, write=30, pool=30),
        )

        self.downloads = {}

    async def download_file(self, url: str, filename: str, relative_path: str = ""):
        download_id = str(uuid.uuid4())

        # Prevent path traversal.
        destination_dir = (self.download_dir / relative_path).resolve()

        if not destination_dir.is_relative_to(self.download_dir):
            raise ValueError("Invalid download path")

        destination_dir.mkdir(parents=True, exist_ok=True)

        destination = destination_dir / Path(filename).name
        temp_file = destination.with_name(destination.name + ".part")

        state = {
            "id": download_id,
            "filename": destination.name,
            "status": "downloading",
            "downloaded": 0,
            "total": None,
            "remaining": None,
            "progress": 0,
            "error": None,
            "task": None,
        }

        self.downloads[download_id] = state

        task = asyncio.create_task(self._download(url, temp_file, destination, state))

        state["task"] = task

        return download_id

    async def _download(self, url, temp_file, destination, state):

        try:
            async with self.client.stream("GET", url) as response:
                response.raise_for_status()

                content_length = response.headers.get("content-length")

                total = int(content_length) if content_length else None
                state["total"] = total

                downloaded = 0

                with open(temp_file, "wb") as file:
                    async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                        file.write(chunk)
                        downloaded += len(chunk)

                        state["downloaded"] = downloaded

                        if total is not None:
                            remaining = max(0, total - downloaded)

                            state["remaining"] = remaining
                            state["progress"] = (
                                downloaded / total * 100 if total > 0 else 100
                            )

                # Ensure data is flushed before finalizing.
                # Rename only after a successful download.
                temp_file.replace(destination)

                state["status"] = "completed"
                state["remaining"] = 0
                state["progress"] = 100

        except asyncio.CancelledError:
            state["status"] = "cancelled"
            raise

        except Exception as e:
            state["status"] = "failed"
            state["error"] = str(e)

        finally:
            if temp_file.exists():
                temp_file.unlink()

    async def cancel_download(self, download_id: str):

        state = self.downloads.get(download_id)

        if not state:
            return False

        if state["status"] != "downloading":
            return False

        task = state["task"]
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        return True

    def get_status(self, download_id: str):

        state = self.downloads.get(download_id)

        if not state:
            return None

        return {key: value for key, value in state.items() if key != "task"}

    async def close(self):
        for state in self.downloads.values():
            if state["status"] == "downloading":
                state["task"].cancel()

        await asyncio.gather(
            *[state["task"] for state in self.downloads.values() if state["task"]],
            return_exceptions=True,
        )

        await self.client.aclose()
