import "./App.css";
import { useState } from "react";

// components
import useDisplayMessage from "./components/DisplayMessages";

// context
import ProjectContext from "./context/ProjectContext";
import { useContext } from "react";

// pages
import MainLandingPage from "./pages/MainLandingPage";
import BackendLandingPage from "./pages/BackendLandingPage";

function App() {

  const [portNumber, setPortNumber] = useState(8000);
  const [backendStatus, setBackendStatus] = useState(false);

  return (
    <>
    <ProjectContext.Provider value={portNumber}>
      {backendStatus ? (
        <MainLandingPage />
      ) : (
        <BackendLandingPage />
      )}
      </ProjectContext.Provider>
    </>
  );
}

export default App;

export const useProjectContext = () => {
  return useContext(ProjectContext);
}