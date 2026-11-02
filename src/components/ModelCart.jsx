// project contex
import { useProjectContext } from "../App";

export default function ModelCart({ modelDetails, isDownloading, setIsDownloading, setNeedToRefresh, setRequestFile }) {
    const { portNumber, setDisplayMessage } = useProjectContext();

    return (
        <div>
            <p>Name: {modelDetails?.name ?? "Not Specified"}</p>

            <h3>Required Files:</h3>

            {Object.entries(modelDetails?.requiredFiles ?? {}).map(
                ([fileName, isDownloaded]) => (
                    <div key={fileName}>
                        <span>{fileName}</span>

                        <button disabled={isDownloading} onClick={() => handleDownload(
                            modelDetails.name, fileName, portNumber, setDisplayMessage, setIsDownloading, setNeedToRefresh, isDownloaded, setRequestFile
                        )} >
                            {isDownloaded ? "Remove" : "Download"}
                        </button>
                    </div>
                )
            )}
        </div>
    );
}

async function handleDownload(
    modelName, fileName, portNumber, setDisplayMessage, setIsDownloading, setNeedToRefresh, isDownloaded, setRequestFile
) {

    if (isDownloaded) {
        const confirmed = await new Promise((resolve) => {
            setRequestFile({
                fileName,
                resolve
            });
        });

        if (!confirmed) return;
    }

    setIsDownloading(true);
    setDisplayMessage(`${isDownloaded ? 'Removing' : 'Downloading'} ${modelName} ${fileName}`);

    try {
        const response = await fetch(
            `http://localhost:${portNumber}/download_resources`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    "model_name": modelName, "file_name": fileName
                })
            });

        if (!response.ok) throw new Error("Download failed");

        setDisplayMessage(`${modelName} ${fileName} ${isDownloaded ? 'removed' : 'downloaded'} successfully.`);

    } catch (error) {
        setDisplayMessage(`Failed to ${isDownloaded ? 'remove' : 'download'} ${modelName} ${fileName}.`);
    } finally {
        setIsDownloading(false);
        setNeedToRefresh((c) => c + 1);
    }
}