import { useParams, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";

// Project Context
import { useProjectContext } from "../App";

export default function Project() {

    const { id } = useParams();
    const { portNumber, setDisplayMessage } = useProjectContext();
    const [projectData, setProjectData] = useState("");
    const navigate = useNavigate();

    useEffect(() => {
        const make_project_request = async () => {

            try {
                const response = await fetch(`http://localhost:${portNumber}/get/project`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ "project_id": id })
                });

                const response_data = await response.json();

                if (response.ok) {

                    console.log(response_data.CM);
                    setProjectData(response_data.UM);
                    setDisplayMessage("Project Load successfully!");

                } else {

                    console.warn(response_data.CM);
                    setDisplayMessage(response_data.UM);
                    setProjectData(false);

                }
            } catch (err) {

                setProjectData(false);
                console.error(`Failed to Load data: ${err}`);
                setDisplayMessage("Unable to load Project Details!");

            }
        }

        make_project_request();
    }, []);

    if (projectData === "") {
        return (
            <div>
                <h3>Loading your project details...</h3>
            </div>
        );
    }

    if (projectData === false) {
        return (
            <div>
                <h3>Something went wrong</h3>
                <p>We couldn't load your data. Please try again.</p>

            </div>
        );
    }

    return (
        <div>
            <div>
                <button onClick={() => navigate("/")}>Back To Projects</button>
                <h2>Project Name: {projectData.project_name || "unnamed project"} </h2>
                <h3>Created: {projectData.created_at || ""}</h3>
            </div>

            <div>
            </div>
        </div>
    );
}