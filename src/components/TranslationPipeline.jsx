import { useState } from "react"

// project context
import { useProjectContext } from "../App";

export default function Translation({ Input_file }) {

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
                <button onClick={() => handleStartTranslatio({
                    portNumber, Input_file, sourceLang, targetedLang

                })}>Start Translation</button>
            </div>
        )
    }
}


function handleStartTranslatio({ portNumber, Input_file, sourceLang, targetedLang }) {

    // Working
    console.log(`Resiving this values: ${portNumber}, ${Input_file}, ${sourceLang}, ${targetedLang}`)


}