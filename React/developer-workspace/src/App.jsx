import { useEffect, useState, useContext, useMemo, useCallback, useRef } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import ProjectContext from "./context/ProjectContext"
import useProjects from "./hooks/useProjects"
import ErrorBoundary from "./components/ErrorBoundary"

// pages
import Dashboard from "./pages/Dashboard";
import Projects from "./pages/Projects";
import ProjectDetails from "./pages/ProjectDetails";

function App() {
  const { projects, addProject, deleteProject} = useProjects();

  return (
    <>
      <BrowserRouter>

        <ProjectContext.Provider value={{
          projects,
          onDeleteProject: deleteProject,
          onAddProject: addProject
        }}>
          <ErrorBoundary>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/projects/:id" element={<ProjectDetails />} />
          </Routes>
          </ErrorBoundary>

        </ProjectContext.Provider>
      </BrowserRouter>
    </>
  )
}
export default App;