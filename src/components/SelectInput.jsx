import { open } from "@tauri-apps/plugin-dialog";

export default function SelectInput({ portNumber, project_id, Input_file, setDisplayMessage }) {

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

                await makeUpdateRequest({ portNumber, project_id, filePath, setDisplayMessage });
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

const makeUpdateRequest = async ({ portNumber, project_id, filePath, setDisplayMessage }) => {

    try {

        const response = await fetch(`http://localhost:${portNumber}/project/update`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                "project_id": project_id,
                "input_video": filePath
            })
        });

        const response_data = await response.json();

        if (response.ok) {

            console.log(response_data.CM);
            setDisplayMessage(response_data.UM);
            window.location.reload();

        } else {

            console.warn(response_data.CM);
            setDisplayMessage(response_data.UM);
        }

    } catch (err) {

        console.error(`Failed to update: ${err}`);
        setDisplayMessage("Something went wrong while updating. Please try again later.")

    }

}