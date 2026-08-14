import { useParams, Link } from "react-router-dom";
import { useContext } from "react";

// Contex
import ProjectContext from "../context/ProjectContext";

function ProjectDetails() {
  const { id } = useParams();
  const { projects } = useContext(ProjectContext);

  const project = projects.find(
    project => project.id === Number(id)
  );
  if (!project) {
    return <h1 style={{ color: "red" }}>Project not found</h1>;

  }
  return (
    <>
      <h1>Project Details</h1>
      <h2>Name: {project.name}</h2>
      <h2>Status: {project.status}</h2>
      <h2>Project ID: {id}</h2>
      <div>
        <Link to="/projects">
          <button type="button">Go Back</button>
        </Link>
      </div>
    </>
  );
}

export default ProjectDetails;