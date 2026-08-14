import { createContext } from "react";
import useProjects from "../hooks/useProjects"

const ProjectContext = createContext();

export default ProjectContext;

export function ProjectProvider({children}) {
    const {
        projects,
        addProject,
        deleteProject
    } = useProjects();

    return (
        <ProjectContext.Provider value={{ projects, addProject, deleteProject}}>
            {children}
        </ProjectContext.Provider>
    );
}


export function useProjectContext() {
    return useContext(ProjectContext);
}