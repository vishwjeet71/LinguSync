import { open } from "@tauri-apps/plugin-dialog";

export default function SelectInput({ Input_file }) {

    const handleSelectFile = async () => {

        try {

            const filePath = await open({
                multiple: false,
                directory: false,
                filters: [
                    {
                        name: "Videos",
                        extensions: ["mp4", "mkv"],
                    }
                ],
            });

            if (filePath === null) {
                console.log("User cancelled the file selection");
            } else {
                // makeUpdateRequest
            }

        } catch (err) {
            console.error("Error selecting file:", err);
        }
    }


    return (
        <div>

            <p>Input Video: {Input_file || "Not selected"}</p>
            <button onClick={handleSelectFile}>
                {Input_file ? "Update File" : "Select File"}
            </button>
        </div>
    );
}

const makeUpdateRequest = async ({ filePath }) => {
}