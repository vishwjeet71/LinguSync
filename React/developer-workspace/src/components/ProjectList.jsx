import ProjectCard from "./ProjectCard";
import { useContext } from "react";
import ProjectContext from "../context/ProjectContext";

function ProjectList() {
    const { projects} = useContext(ProjectContext);

    if (projects.length === 0) {
        return <p>No projects yet.</p>;
    }

    return (
        <section>
            {projects.map((project) => (
                <ProjectCard
                    key={project.id}
                    id = {project.id}
                    name={project.name}
                    status={project.status}
                />
            ))}
        </section>
    );
}

export default ProjectList;