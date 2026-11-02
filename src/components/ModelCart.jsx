// project contex
import { useProjectContext } from "../App";

export default function ModelCart({ modelDetails, isDownloading, setIsDownloading }) {
    const { portNumber, setDisplayMessage } = useProjectContext();

    return (
        <div>
            <p>Name: {modelDetails?.name ?? "Not Specified"}</p>

            <h3>Required Files:</h3>

            {Object.entries(modelDetails?.requiredFiles ?? {}).map(
                ([fileName, isDownloaded]) => (
                    <div key={fileName}>
                        <span>{fileName}</span>

                        <button disabled={isDownloading} onClick={() => handleDownload(modelDetails.name, fileName, portNumber, setDisplayMessage, setIsDownloading)} >
                            {isDownloaded ? "Remove" : "Download"}
                        </button>
                    </div>
                )
            )}
        </div>
    );
}

async function handleDownload(modelName, fileName, portNumber, setDisplayMessage, setIsDownloading) {
    setIsDownloading(true);
    setDisplayMessage(`Start Downloading ${modelName} ${fileName}..`);

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

        setDisplayMessage(`${modelName} ${fileName} downloaded successfully`);
    } catch (error) {
        setDisplayMessage(`Failed to download ${modelName} ${fileName}`);
    } finally {
        setIsDownloading(false);
    }
}