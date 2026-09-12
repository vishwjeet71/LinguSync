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

  // messages
  const { currentMessage, setDisplayMessage } = useDisplayMessage();

  return (
    <>
      <ProjectContext.Provider value={
        { portNumber, setDisplayMessage }
      }>
        {backendStatus ? (<MainLandingPage />) : (
          <BackendLandingPage
            setBackendStatus={setBackendStatus}
            setPortNumber={setPortNumber}
          />
        )}
      </ProjectContext.Provider>
      <div>
        {currentMessage}
      </div>
    </>
  );
}

export default App;

export const useProjectContext = () => {
  return useContext(ProjectContext);
}