import { useContext, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import ProjectContext from "../context/ProjectContext";
import ProjectForm from "../components/ProjectForm";
import ProjectList from "../components/ProjectList";

function Projects() {
  const { projects, onAddProject } = useContext(ProjectContext);

  const completedProjects = useMemo(() => {
    return projects.filter(
      project => project.status === "Completed"
    );
  }, [projects]);

  const inProgressProjects = useMemo(() => {
    return projects.filter(
      project => project.status === "In Progress"
    );
  }, [projects]);

  const planningProjects = useMemo(() => {
    return projects.filter(
      project => project.status === "Planning"
    );
  }, [projects]);

  return (
    <>
      <h1>Projects</h1>
      <h2>Total Projects: {projects.length}</h2>
      <p>Completed: {completedProjects.length}</p>
      <p>In Progress: {inProgressProjects.length}</p>
      <p>Planning: {planningProjects.length}</p>
      <p></p>

      <ProjectForm onAddProject={onAddProject} />
      <ProjectList />

      <div>
        <Link to="/">
          <button type="button">Back To Dashboard</button>
        </Link>
      </div>
    </>
  );
}

export default Projects;