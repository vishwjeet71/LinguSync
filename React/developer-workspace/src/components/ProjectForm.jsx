import { useState, useRef, useEffect } from "react";
import Projects from "../pages/Projects";

function ProjectForm({ onAddProject }) {
    const [projectName, setProjectName] = useState("");
    const [projectStatus, setProjectStatus] = useState("");
    const [error, setError] = useState("");
    const projectNameRef = useRef(null);

    useEffect(() => {
        projectNameRef.current.focus();
    }, []);

    function handleSubmit(event) {
        event.preventDefault();

        if (projectName.trim() === "" || projectStatus.trim() === "") {
            setError("Project name and status are required.");
            return;
        }

        const newProject = {
            id: Date.now(),
            name: projectName.trim(),
            status: projectStatus.trim()
        };

        onAddProject(newProject);

        setError("")
        setProjectName("");
        setProjectStatus("");
    }
    return (
        <>
            <form onSubmit={handleSubmit}>
                <input
                    ref={projectNameRef}
                    placeholder="Project Name"
                    value={projectName}
                    maxLength={100}
                    onChange={(event) => setProjectName(event.target.value)}
                />
                <p></p>

                <select value={projectStatus} onChange={(event) => setProjectStatus(event.target.value)}>
                    <option value=''>Select Status</option>
                    <option value="Planning">Planning</option>
                    <option value="In Progress">In Progress</option>
                    <option value="Completed">Completed</option>
                </select>

                <p></p>
                <button type="submit">Add</button>
            </form>

            {error && <p style={{ color: "red" }}>{error}</p>}
        </>
    );
}

export default ProjectForm;