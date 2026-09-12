import { useEffect, useState } from "react";
import { useProjectContext } from "../App";

// Cart
import ProjectCart from "./ProjectCart";

export default function Projects() {

    const { portNumber, setDisplayMessage } = useProjectContext(); // project context

    const [projectsData, setProjectsData] = useState("");
    const [projectName, setProjectName] = useState('');

    const [isFailed, setIsFailed] = useState(false);
    const [isOpen, setIsOpen] = useState(false);

    useEffect(() => {

        const fetchData = async () => {

            const response = await fetch(`http://localhost:${portNumber}/load_data`)
            const responseData = await response.json();

            if (response.ok) {

                console.log(responseData.CM);
                setProjectsData(responseData.UM.projects);

            } else {

                console.error(responseData.CM);
                setDisplayMessage(responseData.UM);
                setIsFailed(true);

            }
        }

        fetchData();

    }, []);

    if (projectsData === "") {
        return (
            <>
                <h3>Loading your projects...</h3>
            </>
        )
    }

    if (isFailed) {
        return (
            <>
                <h3>Unable to Bring your Data!</h3>
            </>
        );
    }

    if (projectsData && projectsData.length !== 0) {
        return (
            <div>
                <div>

                    <button onClick={() => setIsOpen(true)}>
                        + Add Project
                    </button>

                    <ProjectAddingWindow
                        isOpen={isOpen}
                        setIsOpen={setIsOpen}
                        projectName={projectName}
                        setProjectName={setProjectName}
                        portNumber={portNumber}
                        setDisplayMessage={setDisplayMessage}
                    />
                </div>

                {projectsData.map((p) => (
                    <ProjectCart
                        key={p.project_id}
                        projectName={p.project_name}
                        created_at={p.created_at}
                    />
                ))}
            </div>
        );
    }

    if (projectsData && projectsData.length === 0) {

        return (
            <>
                <h3>You have no Projects!</h3>
                <p>Create A project</p>

                <button onClick={() => setIsOpen(true)}>
                    + Add Project
                </button>

                <ProjectAddingWindow // should pop up a box for entring project name and save it
                    isOpen={isOpen}
                    setIsOpen={setIsOpen}
                    projectName={projectName}
                    setProjectName={setProjectName}
                    portNumber={portNumber}
                    setDisplayMessage={setDisplayMessage}
                />
            </>
        );

    }
}


const ProjectAddingWindow = ({
    isOpen,
    setIsOpen,
    projectName,
    setProjectName,
    portNumber,
    setDisplayMessage
}) => {

    const handleSave = async (e) => {
        e.preventDefault();

        const response = await fetch(
            `http://localhost:${portNumber}/save_project`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    project_name: projectName
                })
            }
        );

        const responseData = await response.json();

        if (response.ok) {

            console.log(responseData.CM);
            setDisplayMessage(responseData.UM);
            setIsOpen(false);
            setProjectName("");

        } else {

            console.error(responseData.CM);
            setDisplayMessage(responseData.UM);

        }
    };

    if (!isOpen) return null;

    return (
        <div className="popup-overlay">
            <div className="popup-box">

                <h3>Create New Project</h3>

                <form onSubmit={handleSave}>
                    <input
                        type="text"
                        placeholder="Enter project name"
                        value={projectName}
                        onChange={(e) => setProjectName(e.target.value)}
                        autoFocus
                        required
                    />

                    <div>
                        <button
                            type="button"
                            onClick={() => setIsOpen(false)}
                        >
                            Cancel
                        </button>

                        <button type="submit">
                            Save
                        </button>
                    </div>
                </form>

            </div>
        </div>
    );
}