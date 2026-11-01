import { useState, useEffect } from "react";
import { resolveResource } from "@tauri-apps/api/path";
import { exists, writeTextFile, readTextFile, BaseDirectory } from "@tauri-apps/plugin-fs";

// project context
import { useProjectContext } from "../App";

export default function ModelsManagerPage() {
    const [modelData, setModelData] = useState(null);
    const [isDataMoved, setIsDataMoved] = useState(false);

    const { setDisplayMessage } = useProjectContext();

    useEffect(() => {
        const loadModelData = async () => {

            try {

                const fileExists = await exists('models_manifest.json', {
                    baseDir: BaseDirectory.AppData
                });

                if (!fileExists) {
                    console.warn("models_manifest.json is missing from AppData! Moving asset...");
                    setDisplayMessage("Model manifest not found. This is normal during the first installation.");

                    const resourcePath = await resolveResource('models_manifest.json');
                    const manifestData = await readTextFile(resourcePath);

                    await writeTextFile('models_manifest.json', manifestData, {
                        baseDir: BaseDirectory.AppData
                    });

                    console.log("models_manifest.json successfully moved to AppData.");
                    setDisplayMessage("New model manifest created successfully!");
                    setIsDataMoved(true);

                } else {
                    console.log("models_manifest.json found in AppData.");
                    setDisplayMessage("Data loaded successfully!");

                    const currentDataText = await readTextFile("models_manifest.json", { baseDir: BaseDirectory.AppData });
                    const currentJsonData = await JSON.parse(currentDataText);

                    setModelData(currentJsonData);
                }

            } catch (error) {
                console.error("Failed to process model data:", error);
                setModelData("Failed to load data.");

            }
        }

        loadModelData();
    }, [isDataMoved]);

    return (
        <>
            <h1>Manage models</h1>
            {modelData ? (
                <>
                    <pre>{JSON.stringify(modelData, null, 2)}</pre>
                </>
            ) : (
                <p>Loading your data...</p>
            )}
        </>
    );
}