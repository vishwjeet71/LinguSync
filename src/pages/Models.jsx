import modelsData from "../assets/models_manifest.json";

import { useState } from "react";

export default function ModelsManagerPage() {
    const [modelData, setModelData] = useState(modelsData);

    return (
        <>
            <h1>Manage models</h1>
            <pre>{JSON.stringify(modelData, null, 2)}</pre>
        </>
    );
}