import { useState, useEffect } from "react";
import { resolveResource } from "@tauri-apps/api/path";
import { exists, writeTextFile, readTextFile, BaseDirectory } from "@tauri-apps/plugin-fs";

// component
import ListModels from "../components/ListModels";

// project context
import { useProjectContext } from "../App";

export default function ModelsManagerPage() {
    const [modelData, setModelData] = useState(null);
    const [needToRefresh, setNeedToRefresh] = useState(0);

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
                    setNeedToRefresh((c) => c + 1);

                } else {
                    console.log("models_manifest.json found in AppData.");

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
    }, [needToRefresh]);

    return (
        <>
            <h1>Manage models</h1>
            {modelData ? (
                <>
                    <ListModels modelsManifest={modelData} setNeedToRefresh={setNeedToRefresh} />
                </>
            ) : (
                <p>Loading your data...</p>
            )}
        </>
    );
}