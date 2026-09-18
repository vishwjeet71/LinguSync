import { open } from "@tauri-apps/plugin-dialog";
import { useEffect, useState } from "react";

export default function SelectInput({ portNumber, project_id, Input_file, setDisplayMessage, setRefTrigger, setIsUpdate }) {

    const [updateProcessMenager, setUpdateProcessMenager] = useState("default");
    const [warrMessage, setWarrMessage] = useState(false);
    const [userResponse, setUserResponse] = useState(false);


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

                await makeUpdateRequest({ portNumber, project_id, filePath, setDisplayMessage, setRefTrigger });
            }

        } catch (err) {
            console.error("Error selecting file:", err);
        }
    }

    useEffect(() => {

        if (updateProcessMenager === "default") {
            return;
        }

        if (updateProcessMenager === "wantUpdate" && Input_file) {

            setWarrMessage(true);

        } else {

            handleSelectFile();
            setUpdateProcessMenager("default");
        }

    }, [updateProcessMenager])

    return (
        <div>
            {warrMessage && (
                <div>
                    <h3>Changing the input file will restart the project.</h3>
                    <p>Create a new project if you want to keep this project unchanged.</p>

                    <div>
                        <button onClick={() => {
                            setWarrMessage(false);
                            setUpdateProcessMenager("default");
                        }}>Cancle</button>

                        <button onClick={() => {
                            setWarrMessage(false);
                            handleSelectFile();
                            setUpdateProcessMenager("default");
                        }}>Update</button>
                    </div>

                </div>
            )}

            <p>Input Video: {Input_file || "Not selected"}</p>
            <button onClick={() => setUpdateProcessMenager("wantUpdate")}>
                {Input_file ? "Update File" : "Select File"}
            </button>
        </div>
    );
}

const makeUpdateRequest = async ({ portNumber, project_id, filePath, setDisplayMessage, setRefTrigger }) => {

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
            setRefTrigger(p => p + 1);

        } else {

            console.warn(response_data.CM);
            setDisplayMessage(response_data.UM);
        }

    } catch (err) {

        console.error(`Failed to update: ${err}`);
        setDisplayMessage("Something went wrong while updating. Please try again later.")

    }

}