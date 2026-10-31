import { useState, useEffect } from "react";

import { exists, writeTextFile, BaseDirectory } from "@tauri-apps/plugin-fs";

export default function ModelsManagerPage() {
    const [modelData, setModelData] = useState('Loading your data...');
    const [isDataMoved, setIsDataMoved] = useState(false);

    useEffect(() => {
        const loadModelData = async () => {

            try {

                const fileExists = await exists('models_manifest.json', {
                    baseDir: BaseDirectory.AppData
                });

                if (!fileExists) {
                    console.warn("models_manifest.json is missing from AppData! Moving asset...");

                    const response = await fetch('/assets/models_manifest.json');
                    const manifestData = await response.text();

                    await writeTextFile('models_manifest.json', manifestData, {
                        baseDir: BaseDirectory.AppData
                    });

                    console.log("models_manifest.json successfully moved to AppData.");
                    setIsDataMoved(true);

                } else {
                    console.log("models_manifest.json found in AppData.");
                    setModelData("Data loaded"); // Need to implement logic which read data.
                }

            } catch (error) {
                console.error("Failed to process model data:", error);

            }
        }

        loadModelData();
    }, [isDataMoved]);

    return (
        <>
            <h1>Manage models</h1>
            <h2>App data path: {BaseDirectory.AppData}</h2>
            <pre>{modelData}</pre>
        </>
    );
}