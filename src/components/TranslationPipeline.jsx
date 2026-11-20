import { useEffect, useState } from "react"

// project context
import { useProjectContext } from "../App";

function Translation({ Input_file, project_id, setRefTrigger }) {

    if (Input_file) {

        const [sourceLang, setSourceLang] = useState("hindi");
        const [targetedLang, setTargetedLang] = useState("english");

        const { portNumber, setDisplayMessage } = useProjectContext();


        return (
            <div>
                <div>
                    <label>Choose your video language:</label>
                    <select value={sourceLang} onChange={(e) => setSourceLang(e.target.value)}>
                        <option value={"hindi"}>Hindi</option>
                        <option value={"english"}>English</option>
                        <option value={"chinese"}>Chinese</option>
                        <option value={"german"}>German</option>
                        <option value={"spanish"}>Spanish</option>
                        <option value={"russian"}>Russian</option>
                        <option value={"korean"}>Korean</option>
                        <option value={"french"}>French</option>
                        <option value={"japanese"}>Japanese</option>
                    </select>
                </div>
                <div>
                    <label>Choose Targeted Language:</label>
                    <select value={targetedLang} onChange={(e) => setTargetedLang(e.target.value)}>
                        <option value={"english"}>English</option>
                        <option value={"chinese"}>Chinese</option>
                        <option value={"japanese"}>Japanese</option>
                        <option value={"korean"}>Korean</option>
                    </select>
                </div>
                <h4>Please verify your selected languages before starting. Incorrect selections may result in unexpected translation output.</h4>
                <button onClick={() => handleStartTranslatio({
                    portNumber, project_id, Input_file, sourceLang, targetedLang, setDisplayMessage, setRefTrigger

                })}>Start Translation</button>
            </div>
        )
    }
}


async function handleStartTranslatio({ portNumber, project_id, Input_file, sourceLang, targetedLang, setDisplayMessage, setRefTrigger }) {

    const response = await fetch(
        `http://localhost:${portNumber}/translate/project`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(
                {
                    "project_id": project_id,
                    "input_audio_path": Input_file,
                    "source_language": sourceLang,
                    "target_language": targetedLang
                })
        }
    );
    const data = await response.json();

    if (!response.ok) {
        console.error(data.CM);
    }
    setRefTrigger(c => c + 1);
    setDisplayMessage(data.UM);
    console.log(data.CM);

}


function TrackTranslationProcess({ processing_id, portNumber, setDisplayMessage }) {

    const [processData, setProcessData] = useState({});

    useEffect(() => {
        let shouldClose = false;

        const ws = new WebSocket(
            `ws://localhost:${portNumber}/translate/task/get/${processing_id}`
        );

        ws.onopen = () => {
            if (shouldClose) {
                ws.close();
            }
        };

        ws.onmessage = (event) => {
            if (!shouldClose) {
                setProcessData(JSON.parse(event.data));
            }
        };

        ws.onerror = (error) => {
            console.error("WebSocket error:", error);
        };

        return () => {
            shouldClose = true;

            if (ws.readyState === WebSocket.OPEN) {
                ws.close();
            }
        };
    }, [processing_id, portNumber]);

    return (
        <div>
            <p>Working on your video</p>
            <p>Hardware Type: {processData.hardware}</p>
            <p>Inferencing on: {processData.inference_type}</p>
            <p>Stage: {processData.current_working_task}</p>
            <p>Status: {processData.status}</p>
            {processData.error ? (<h3>Error: {processData.error}</h3>) : null}
        </div>
    )

}


export { Translation, TrackTranslationProcess }