import { open } from "@tauri-apps/plugin-dialog";
import { useEffect, useState } from "react";

// navigation
import { useNavigate } from "react-router-dom";

export default function SelectInput({ portNumber, project_id, Input_file, setDisplayMessage, setRefTrigger, setIsUpdate }) {

    const [updateProcessMenager, setUpdateProcessMenager] = useState("default");
    const [warrMessage, setWarrMessage] = useState(false);
    const [projectRemovingWarr, setProjectRemovingWarr] = useState(false);

    // navigation
    const navigate = useNavigate();

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

            {projectRemovingWarr && (
                <div>
                    <h3>Are you sure you want to delete this project?</h3>
                    <button onClick={() => {
                        setProjectRemovingWarr(false);
                        handleProjectDeletion({ portNumber, navigate, project_id, setDisplayMessage })
                    }}>Delete</button>
                    <button onClick={() => setProjectRemovingWarr(false)}>Cancel</button>
                </div>
            )}

            <p>Input Video: {Input_file || "Not selected"}</p>
            <button onClick={() => setUpdateProcessMenager("wantUpdate")}>
                {Input_file ? "Update File" : "Select File"}
            </button>

            <button onClick={() => setProjectRemovingWarr(true)}>Delete project</button>
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

const handleProjectDeletion = async ({
    portNumber,
    navigate,
    project_id,
    setDisplayMessage
}) => {
    try {
        const response = await fetch(
            `http://localhost:${portNumber}/remove/${project_id}`,
            {
                method: "DELETE",
                headers: {
                    "accept": "*/*"
                }
            }
        );

        const response_data = await response.json();

        const consoleMessage = response_data.CM;
        const userMessage = response_data.UM;

        if (!response.ok) {
            console.error(consoleMessage);
            setDisplayMessage(userMessage);
            return;
        }

        console.log(consoleMessage);
        navigate("/");

    } catch (error) {
        console.error("Project deletion failed:", error);
        setDisplayMessage("Something went wrong. Please try again.");
    }
};