import { Link } from "react-router-dom";
import { useContext } from "react";
import ProjectContext from "../context/ProjectContext";

function ProjectCard({id, name, status}) {
    const { onDeleteProject} = useContext(ProjectContext);
    return (
        <>
            <p>Name: {name}</p>
            <p>Status: {status}</p>
            <button onClick={() => onDeleteProject(id)}>
                Delete
            </button>
            <p></p>
            <Link to={`/projects/${id}`}>View Details</Link>
            <p>-----</p>
        </>
    );
}

export default ProjectCard;