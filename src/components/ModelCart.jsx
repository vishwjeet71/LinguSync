export default function ModelCart({ modelDetails }) {
    return (
        <div>
            <p>Name: {modelDetails?.name ?? "Not Specified"}</p>

            <h3>Required Files:</h3>

            {Object.entries(modelDetails?.requiredFiles ?? {}).map(
                ([fileName, isDownloaded]) => (
                    <div key={fileName}>
                        <span>{fileName}</span>

                        <button>
                            {isDownloaded ? "Remove" : "Download"}
                        </button>
                    </div>
                )
            )}
        </div>
    );
}