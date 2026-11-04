
export default function ModelCart({
    modelDetails,
    portNumber,
    startTracking,
    setNeedToRefresh,
    setRequestFile,
    setDisplayMessage
}) {
    return (
        <div>
            <p>Name: {modelDetails?.name ?? "Not Specified"}</p>

            <h3>Required Files:</h3>

            {Object.entries(modelDetails?.requiredFiles ?? {}).map(
                ([fileName, isDownloaded]) => (
                    <div key={fileName}>
                        <span>{fileName}</span>

                        <button
                            onClick={() => handleDownload(
                                modelDetails.name,
                                fileName,
                                isDownloaded,
                                portNumber,
                                startTracking,
                                setNeedToRefresh,
                                setRequestFile,
                                setDisplayMessage
                            )}
                        >
                            {isDownloaded ? "Remove" : "Download"}
                        </button>
                    </div>
                )
            )}
        </div>
    );
}

async function handleDownload(
    modelName,
    fileName,
    isDownloaded,
    portNumber,
    startTracking,
    setNeedToRefresh,
    setRequestFile,
    setDisplayMessage
) {
    if (isDownloaded) {
        const confirmed = await new Promise(resolve => {
            setRequestFile({ fileName, resolve });
        });

        if (!confirmed) return;
    }

    setDisplayMessage(
        `${isDownloaded ? "Removing" : "Starting download:"} ${fileName}`
    );

    try {
        const response = await fetch(
            `http://localhost:${portNumber}/downloads`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    model_name: modelName,
                    file_name: fileName
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.UM || data.CM || "Request failed");
        }

        if (isDownloaded) {
            setDisplayMessage(data.UM || `${fileName} removed.`);
            setNeedToRefresh(c => c + 1);
            return;
        }

        const downloadId = data.CM;

        if (!downloadId) {
            throw new Error("Backend did not return a download ID.");
        }

        startTracking(downloadId, fileName, modelName);

        setDisplayMessage(`${fileName} download started.`);

    } catch (error) {
        console.error("Download request failed:", error);
        setDisplayMessage(error.message);
    }
}
