
import { useState, useEffect, useRef, useCallback } from "react";
import ModelCart from "./ModelCart";
import { useProjectContext } from "../App";

export default function ListModels({ modelsManifest, setNeedToRefresh }) {
    const { portNumber, setDisplayMessage } = useProjectContext();

    // { downloadId: downloadStatus }
    const [downloads, setDownloads] = useState({});
    const sockets = useRef({});


    const startTracking = useCallback((downloadId, filename, modelName) => {

        // Prevent duplicate WebSocket connections.
        if (sockets.current[downloadId]) return;

        setDownloads(prev => ({
            ...prev,
            [downloadId]: {
                id: downloadId,
                filename,
                modelName,
                status: "connecting",
                downloaded: 0,
                total: null,
                remaining: null,
                progress: 0
            }
        }));

        const socket = new WebSocket(
            `ws://localhost:${portNumber}/downloads/${downloadId}/progress`
        );

        sockets.current[downloadId] = socket;

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.error) {
                setDownloads(prev => ({
                    ...prev,
                    [downloadId]: {
                        ...prev[downloadId],
                        status: "failed",
                        error: data.error
                    }
                }));

                socket.close();
                return;
            }

            setDownloads(prev => ({
                ...prev,
                [downloadId]: {
                    ...prev[downloadId],
                    ...data
                }
            }));

            if (["completed", "failed", "cancelled"].includes(data.status)) {
                socket.close();
                delete sockets.current[downloadId];

                setNeedToRefresh(c => c + 1);

                setDisplayMessage(
                    data.status === "completed"
                        ? `${filename} downloaded successfully.`
                        : `${filename}: ${data.status}`
                );
            }
        };

        socket.onerror = () => {
            setDownloads(prev => ({
                ...prev,
                [downloadId]: {
                    ...prev[downloadId],
                    connectionError: true
                }
            }));
        };

        socket.onclose = () => {
            if (sockets.current[downloadId] === socket) {
                delete sockets.current[downloadId];
            }
        };

    }, [portNumber, setNeedToRefresh, setDisplayMessage]);

    useEffect(() => {
        let isMounted = true;

        async function restoreDownloads() {
            try {
                const response = await fetch(
                    `http://localhost:${portNumber}/downloads`
                );

                if (!response.ok) {
                    throw new Error("Unable to restore active downloads.");
                }

                const data = await response.json();

                if (!isMounted) return;

                data.downloads.forEach(download => {
                    startTracking(
                        download.id,
                        download.filename,
                        download.model_name
                    );
                });

            } catch (error) {
                if (isMounted) {
                    console.error("Failed to restore downloads:", error);
                }
            }
        }

        restoreDownloads();

        return () => {
            isMounted = false;
        };

    }, [portNumber, startTracking]);


    async function cancelDownload(downloadId) {
        const previous = downloads[downloadId];

        if (!previous || previous.status !== "downloading") return;

        setDownloads(prev => ({
            ...prev,
            [downloadId]: {
                ...prev[downloadId],
                status: "cancelling"
            }
        }));

        try {
            const response = await fetch(
                `http://localhost:${portNumber}/downloads/${downloadId}`,
                { method: "DELETE" }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.UM || "Unable to cancel download");
            }

            // Backend confirms cancellation.
            // Close the WebSocket.
            const socket = sockets.current[downloadId];

            if (socket) {
                socket.close();
                delete sockets.current[downloadId];
            }

            // Immediately remove the download from frontend state.
            setDownloads(prev => {
                const updated = { ...prev };
                delete updated[downloadId];
                return updated;
            });

            setDisplayMessage(`${previous.filename} cancelled successfully.`);

        } catch (error) {
            setDownloads(prev => ({
                ...prev,
                [downloadId]: {
                    ...prev[downloadId],
                    status: "downloading"
                }
            }));

            setDisplayMessage(error.message);
        }
    }


    const downloadProps = {
        portNumber,
        startTracking,
        setNeedToRefresh,
        setDisplayMessage
    };

    const em = modelsManifest.efficient;
    const pm = modelsManifest.performance;

    return (
        <div>
            {em && Object.keys(em).length > 0 && (
                <>
                    <h2>Efficient Models</h2>
                    <ModelBlock blockDetail={em} {...downloadProps} />
                </>
            )}

            {pm && Object.keys(pm).length > 0 && (
                <>
                    <h2>Performance Models</h2>
                    <ModelBlock blockDetail={pm} {...downloadProps} />
                </>
            )}

            <DownloadingBar
                downloads={downloads}
                onCancel={cancelDownload}
            />
        </div>
    );
}

function ModelBlock({ blockDetail, ...downloadProps }) {
    const [requestFile, setRequestFile] = useState(null);

    const { stt, mt, tts } = blockDetail;

    return (
        <>
            {requestFile && (
                <FileRemovingWarning
                    requestFile={requestFile.fileName}
                    onConfirm={() => {
                        requestFile.resolve(true);
                        setRequestFile(null);
                    }}
                    onCancel={() => {
                        requestFile.resolve(false);
                        setRequestFile(null);
                    }}
                />
            )}

            <h3>Speech To Text model</h3>
            {stt ? (
                <ModelCart
                    modelDetails={stt}
                    setRequestFile={setRequestFile}
                    {...downloadProps}
                />
            ) : <p>Not implemented yet.</p>}

            <h3>Machine Translation</h3>
            {mt ? (
                <ModelCart
                    modelDetails={mt}
                    setRequestFile={setRequestFile}
                    {...downloadProps}
                />
            ) : <p>Not implemented yet.</p>}

            <h3>Text To Speech</h3>
            {tts ? (
                <ModelCart
                    modelDetails={tts}
                    setRequestFile={setRequestFile}
                    {...downloadProps}
                />
            ) : <p>Not implemented yet.</p>}
        </>
    );
}


function DownloadingBar({ downloads, onCancel }) {

    const activeDownloads = Object.values(downloads).filter(
        download =>
            ["connecting", "downloading", "cancelling"].includes(download.status)
    );

    if (activeDownloads.length === 0) return null;

    return (
        <section>
            <h3>Downloads</h3>

            {activeDownloads.map(download => (
                <div key={download.id}>
                    <p>
                        <strong>{download.filename}</strong>
                        {" "}({download.modelName})
                    </p>

                    <p>Status: {download.status}</p>

                    {download.total != null ? (
                        <progress
                            value={download.progress ?? 0}
                            max="100"
                        />
                    ) : (
                        <progress />
                    )}

                    <p>
                        {download.total != null
                            ? `${download.progress.toFixed(1)}%`
                            : "Calculating progress..."}
                        {" | "}
                        {formatBytes(download.downloaded)}
                        {" / "}
                        {formatBytes(download.total)}
                    </p>

                    {download.status === "downloading" && (
                        <button onClick={() => onCancel(download.id)}>
                            Cancel
                        </button>
                    )}

                    {download.status === "cancelling" && (
                        <p>Cancelling download...</p>
                    )}
                </div>
            ))}
        </section>
    );
}


function formatBytes(bytes) {
    if (bytes == null) return "Unknown";

    if (bytes < 1024) return `${bytes} B`;

    const units = ["KB", "MB", "GB", "TB"];
    let size = bytes / 1024;
    let index = 0;

    while (size >= 1024 && index < units.length - 1) {
        size /= 1024;
        index++;
    }

    return `${size.toFixed(2)} ${units[index]}`;
}

function FileRemovingWarning({ requestFile, onConfirm, onCancel }) {
    return (
        <div>
            <p>Are you sure you want to remove "{requestFile}"?</p>
            <button onClick={onConfirm}>Yes</button>
            <button onClick={onCancel}>Cancel</button>
        </div>
    );
}
