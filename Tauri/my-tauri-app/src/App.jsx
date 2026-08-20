import { getName } from "@tauri-apps/api/app";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import { mkdir, writeTextFile, readTextFile, BaseDirectory } from "@tauri-apps/plugin-fs";
import { appDataDir, appConfigDir, appCacheDir, appLogDir, tempDir } from "@tauri-apps/api/path";
import { listen } from "@tauri-apps/api/event";
import { Command } from "@tauri-apps/plugin-shell";

import "./App.css"
import { useState, useEffect } from "react";
import ProcessManager from "./ProcessManager";
import TauriStateTest from "./TauriStateTest";
import FastApiBackend from "./Backend";

function App() {
  const [appName, setAppName] = useState("");
  const [message, setMessage] = useState("");
  const [userName, setUserName] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [settingsData, setSettingsData] = useState(null);
  const [appDirs, setAppDirs] = useState({});
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState("Idle");
  const [pid, setPid] = useState('—');
  const [childProcess, setChildProcess] = useState(null);

  useEffect(() => {
    async function loadAppName() {
      const name = await getName();

      setAppName(name);
    }

    loadAppName();
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();

    try {
      setMessage(await invoke("greet", {
        name: userName,
      }));

    } catch (error) {
      setMessage(error)
    }

  }

  async function selectFile() {
    const file = await open({
      multiple: false,
      directory: false,
      filters: [
        {
          name: "video",
          extensions: ["mp4", "mkv", "mov",]
        }
      ]
    });

    if (file === null) {
      return;
    }

    setSelectedFile(file)
  }

  async function saveSettings() {
    try {
      // create app name folder into the .config
      await mkdir("", {
        baseDir: BaseDirectory.AppConfig,
        recursive: true
      });


      await writeTextFile(
        "settings.json",
        JSON.stringify({
          name: userName || "Unknown",
          theme: "dark",
          language: "English",
        }), {
        baseDir: BaseDirectory.AppConfig,
      }
      );

      console.log("Saved!");
    } catch (error) {
      console.error("Failed to save settings:", error);
    }
  }

  async function loadSettings() {
    try {
      const contents = await readTextFile("settings.json", {
        baseDir: BaseDirectory.AppConfig,
      });

      const parsedData = JSON.parse(contents);
      setSettingsData(parsedData);
    } catch (error) {
      console.error("Failed to load settings:", error);
    }
  }

  useEffect(() => {
    async function getAppDirs() {
      setAppDirs({
        appData: await appDataDir(),
        appConfig: await appConfigDir(),
        cache: await appCacheDir(),
        logs: await appLogDir(),
        temp: await tempDir(),
      })
    }

    getAppDirs();
  }, []
  )

  useEffect(() => {
    const unlisten = listen("processing-progress", (event) => {
      setProgress(event.payload);
      setStatus("Processing");
    });

    return () => {
      unlisten.then((fn) => fn());
    };
  }, []);

  async function startProcessing() {
    setProgress(0);
    setStatus("Starting...");

    try {
      await invoke("start_processing");
    } catch (error) {
      setStatus(`Error: ${error}`);
    }
  }

  useEffect(() => {
    const unlisten = listen("processing-completed", () => {
      setStatus("Completed");
      setProgress(100);
    });

    return () => {
      unlisten.then((fn) => fn()); // close the event 
    };
  }, []);

  async function runCommand() {
    const command = Command.create("run-echo", [
      "Hello from Tauri"
    ]);

    const output = await command.execute();

    console.log(output);
  }

  return (
    <>
      <h1>App: {appName}</h1>
      <form onSubmit={handleSubmit}>
        <input value={userName} onChange={(event) => setUserName(event.target.value)} />
        <button>Submit</button>
        <h2>{message}</h2>
      </form>
      <p>Select File</p>
      <button onClick={selectFile}>Select</button>
      <button onClick={saveSettings}>Save</button>
      <button onClick={loadSettings}>Show settings</button>

      {settingsData && (
        <div style={{ marginTop: "20px", border: "1px solid #ccc", padding: "10px" }}>
          <h2>App Settings</h2>
          <p>Name: {settingsData.name}</p>
          <p>Language: {settingsData.language}</p>
          <p>Theme: {settingsData.theme}</p>
        </div>
      )}

      {appDirs && (
        <div>
          <h2>Application Directories</h2>
          <p>App Data: {appDirs.appData}</p>
          <p>App Config: {appDirs.appConfig}</p>
          <p>App Cache: {appDirs.cache}</p>
          <p>App Logs: {appDirs.logs}</p>
          <p>App Temp: {appDirs.temp}</p>
        </div>
      )}
      <h2>Status: {status}</h2>
      <h2>Process: {progress}</h2>
      <button onClick={startProcessing}>
        Start Processing
      </button>
      <p></p>
      <button onClick={runCommand}>Run CMD</button>
      <ProcessManager/>
      <TauriStateTest/>
      <FastApiBackend/>
    </>
  );
}

export default App;
