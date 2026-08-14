import { useEffect, useState } from "react";

function useProjects() {
    const [projects, setProjects] = useState(() => {
        const savedProjects =
            localStorage.getItem("projects");

        return savedProjects ? JSON.parse(savedProjects) : [];
    });

    useEffect(() => {
        localStorage.setItem(
            "projects",
            JSON.stringify(projects)
        );
    }, [projects])

    function addProject(newProject) {
        setProjects(previousProjects => [
            ...previousProjects,
            newProject
        ]);
    }

    function deleteProject(id) {
        setProjects(previousProjects =>
            previousProjects.filter(
                project => project.id !== Number(id)
            )
        );
    }

    return {
        projects,
        addProject,
        deleteProject
    };
}

export default useProjects;